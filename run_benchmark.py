"""T2 - LiDAR corruption benchmark.

    python run_benchmark.py [--scenes 8] [--out results]

Synthetic 32-beam LiDAR scans -> 6 corruptions x 5 severities -> classic clustering detector.
Metrics: object recall (overall / by distance), false-positive clusters, points on objects,
and a GT-free health score. Writes CSVs + PNG plots into --out.
"""
import argparse
import csv
import os

import numpy as np
from PIL import Image, ImageDraw

from lidar_bench.corruptions import CORRUPTIONS, FIXES
from lidar_bench.detect import calibrate, detect, health_score, match
from lidar_bench.plots import COLORS, bev_panel, font, line_panel
from lidar_bench.sim import make_scene, simulate

DIST_BINS = [(0, 20), (20, 40), (40, 60)]
MIN_GT_PTS = 5          # GT object must have >= 5 points in the clean scan (KITTI/nuScenes-style filter)
HEALTH_THR = 0.8        # health < thr -> sensor flagged DEGRADED
RECALL_DROP = 0.10      # relative recall drop that counts as a real degradation


def evaluate(pc, objs, gt_ids):
    hit, fp = match(detect(pc), objs, gt_ids)
    row = dict(n_points=len(pc["xyz"]), recall=len(hit) / max(1, len(gt_ids)), fp=fp,
               obj_pts=int(np.isin(pc["label"], list(gt_ids)).sum()))
    for lo, hi in DIST_BINS:
        ids = [i for i in gt_ids if lo <= np.hypot(objs[i]["cx"], objs[i]["cy"]) < hi]
        row[f"recall_{lo}_{hi}"] = len(hit & set(ids)) / len(ids) if ids else np.nan
        row[f"pts_per_obj_{lo}_{hi}"] = (np.isin(pc["label"], ids).sum() / len(ids)) if ids else np.nan
    return row, hit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", type=int, default=8)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    scenes = []
    for s in range(args.scenes):
        rng = np.random.default_rng(s)
        objs, walls = make_scene(rng)
        clean = simulate(objs, walls, rng)
        counts = np.bincount(clean["label"][clean["label"] >= 0], minlength=len(objs))
        gt_ids = {i for i in range(len(objs)) if counts[i] >= MIN_GT_PTS}
        scenes.append((objs, clean, gt_ids))
    base = calibrate([c for _, c, _ in scenes])

    rows, bev = [], {}
    for s, (objs, clean, gt_ids) in enumerate(scenes):
        clean_row, clean_hit = evaluate(clean, objs, gt_ids)
        h, comp = health_score(clean, base)
        rows.append(dict(scene=s, corruption="clean", severity=0, param=0, **{**clean_row, "obj_pts": 1.0}, health=h,
                         worst_component=min(comp, key=comp.get)))
        if s == 0:
            bev["clean"] = (clean, clean_hit)
        for name, (fn, levels, _) in {**CORRUPTIONS, **FIXES}.items():
            for sev, p in enumerate(levels, 1):
                pc = fn(clean, p, np.random.default_rng(1000 * s + sev))
                row, hit = evaluate(pc, objs, gt_ids)
                h, comp = health_score(pc, base)
                row["obj_pts"] /= max(1, clean_row["obj_pts"])
                rows.append(dict(scene=s, corruption=name, severity=sev, param=p, **row, health=h,
                                 worst_component=min(comp, key=comp.get)))
                if s == 0:
                    bev[(name, sev)] = (pc, hit)
        print(f"scene {s}: {len(gt_ids)} visible GT objects, clean recall {clean_row['recall']:.2f}")

    keys = list(rows[0].keys())
    with open(os.path.join(args.out, "metrics_per_scene.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(rows)

    # ---- aggregate over scenes
    num = [k for k in keys if k not in ("scene", "corruption", "worst_component")]
    groups = {}
    for r in rows:
        groups.setdefault((r["corruption"], r["severity"]), []).append(r)
    summary = []
    for (c, sev), rs in groups.items():
        agg = dict(corruption=c, severity=sev)
        for k in num:
            if k not in ("severity",):
                agg[k] = float(np.nanmean([r[k] for r in rs]))
        for k in ("recall", "fp", "health"):
            agg[f"{k}_std"] = float(np.std([r[k] for r in rs]))
        agg["flag_rate"] = float(np.mean([r["health"] < HEALTH_THR for r in rs]))
        wc = [r["worst_component"] for r in rs]
        agg["worst_component"] = max(set(wc), key=wc.count)
        summary.append(agg)
    clean_recall = next(a["recall"] for a in summary if a["corruption"] == "clean")
    for a in summary:
        a["rel_recall_drop"] = 1 - a["recall"] / clean_recall
        real = a["rel_recall_drop"] > RECALL_DROP
        flagged = a["flag_rate"] >= 0.5
        a["verdict"] = ("SILENT FAILURE" if real and not flagged else
                        "caught" if real else "false alarm" if flagged else "ok")
    with open(os.path.join(args.out, "summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, list(summary[0].keys()))
        w.writeheader()
        for a in summary:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in a.items()})

    print(f"\n{'corruption':15s} sev {'param':>6s} {'recall +- std':>13s} {'drop':>6s} {'FP':>5s} "
          f"{'objpts':>6s} {'health':>6s}  worst_component   verdict")
    for a in summary:
        print(f"{a['corruption']:15s} {a['severity']:3d} {a['param']:6.3f} {a['recall']:6.3f}+-{a['recall_std']:.3f} "
              f"{a['rel_recall_drop']:6.1%} {a['fp']:5.1f} {a.get('obj_pts', 1):6.2f} "
              f"{a['health']:6.2f}  {a['worst_component']:17s} {a['verdict']}")

    # ---- plots
    get = lambda c, k: [next(a[k] for a in summary if a["corruption"] == "clean")] + \
                       [next(a[k] for a in summary if a["corruption"] == c and a["severity"] == s)
                        for s in range(1, 6)]
    names = list(CORRUPTIONS)
    img = Image.new("RGB", (2100, 800), "white")
    d = ImageDraw.Draw(img)
    xs = list(range(6))
    fix_col = "#00a0c0"
    line_panel(d, (0, 0, 700, 620), xs, [(n, get(n, "recall"), COLORS[i]) for i, n in enumerate(names)] +
               [(n, get(n, "recall"), fix_col) for n in FIXES],
               "Object recall vs severity (mean of scenes)", "severity (0 = clean)", "recall")
    max_fp = max(max(get(n, "fp")) for n in names)
    line_panel(d, (700, 0, 1400, 620), xs, [(n, get(n, "fp"), COLORS[i]) for i, n in enumerate(names)],
               "False-positive clusters / scan", "severity (0 = clean)", "FP clusters",
               ylim=(0, max(5.0, np.ceil(max_fp / 5) * 5)), legend=False)
    line_panel(d, (1400, 0, 2100, 620), xs, [(n, get(n, "health"), COLORS[i]) for i, n in enumerate(names)],
               "GT-free health score (flag < 0.8)", "severity (0 = clean)", "health", legend=False)
    d.text((20, 640), f"Severity -> actual parameter (sev 1..5). Mean over {args.scenes} synthetic scenes, "
           f"baseline = sev 0 (clean, recall {clean_recall:.2f}).", fill="black", font=font(16))
    for i, (n, (_, levels, unit)) in enumerate({**CORRUPTIONS, **FIXES}.items()):
        col = COLORS[i] if n in CORRUPTIONS else fix_col
        x, y = 20 + (i % 4) * 520, 672 + (i // 4) * 30
        d.rectangle([x, y + 3, x + 12, y + 15], fill=col)
        d.text((x + 18, y), f"{n}: {unit} = " + " / ".join(f"{v:g}" for v in levels), fill="black", font=font(14))
    img.save(os.path.join(args.out, "degradation_curve.png"))

    img = Image.new("RGB", (1400, 620), "white")
    d = ImageDraw.Draw(img)
    bins = [f"{lo}-{hi} m" for lo, hi in DIST_BINS]
    sev = 3
    pick = lambda c, k: [next(a[k] for a in summary if a["corruption"] == c and a["severity"] == (0 if c == "clean" else sev))
                         for k in [f"{k}_{lo}_{hi}" for lo, hi in DIST_BINS]]
    ser = [("clean", pick("clean", "recall"), COLORS[6])] + [(n, pick(n, "recall"), COLORS[i]) for i, n in enumerate(names)]
    line_panel(d, (0, 0, 700, 620), [0, 1, 2], ser, f"Recall by distance (severity {sev})",
               "distance to object", "recall", xticklabels=bins)
    ser = [("clean", pick("clean", "pts_per_obj"), COLORS[6])] + [(n, pick(n, "pts_per_obj"), COLORS[i]) for i, n in enumerate(names)]
    ymax = max(max(v for v in s[1]) for s in ser)
    line_panel(d, (700, 0, 1400, 620), [0, 1, 2], ser, f"Points per object by distance (severity {sev})",
               "distance to object", "points / object", ylim=(0, np.ceil(ymax / 50) * 50),
               xticklabels=bins, legend=False)
    img.save(os.path.join(args.out, "recall_by_distance.png"))

    objs, _, gt_ids = scenes[0]
    img = Image.new("RGB", (1500, 1530), "white")
    panels = [("clean", "Clean"), (("fog", 4), "Fog alpha=0.03, MOR~100 m (sev 4)"),
              (("beam_missing", 4), "Beam missing 75% (sev 4)"), (("motion_smear", 5), "Motion smear 30 m/s (sev 5)")]
    for k, (key, title) in enumerate(panels):
        r, c = divmod(k, 2)
        pc, hit = bev[key]
        bev_panel(img, (c * 750, r * 765, (c + 1) * 750, (r + 1) * 765), pc, objs, gt_ids, hit, title)
    img.save(os.path.join(args.out, "bev_before_after.png"))
    print(f"\nwrote {args.out}/: summary.csv metrics_per_scene.csv degradation_curve.png "
          f"recall_by_distance.png bev_before_after.png")


if __name__ == "__main__":
    main()
