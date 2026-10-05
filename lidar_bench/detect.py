"""Classic non-learned 3D detector (ground removal + Euclidean clustering), GT matching,
and a GT-free sensor health score."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from .sim import GROUND_Z, N_AZ, N_BEAMS

GROUND_MARGIN = 0.25   # m above ground plane counts as obstacle
CLUSTER_RADIUS = 0.8   # m
MIN_PTS = 3
MATCH_DIST = {"car": 2.5, "ped": 1.0}  # m, xy distance cluster center -> GT center
N_SECTORS = 36


def detect(pc):
    """Returns list of clusters as dicts with center (x,y) and point count."""
    xyz = pc["xyz"]
    obst = xyz[(xyz[:, 2] > GROUND_Z + GROUND_MARGIN) & (np.linalg.norm(xyz, axis=1) > 1.0)]
    if len(obst) < MIN_PTS:
        return []
    pairs = cKDTree(obst).query_pairs(CLUSTER_RADIUS, output_type="ndarray")
    g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(obst),) * 2)
    _, lab = connected_components(g, directed=False)
    clusters = []
    for c in np.unique(lab):
        p = obst[lab == c]
        if len(p) < MIN_PTS:
            continue
        ext = p.max(0) - p.min(0)
        if max(ext[0], ext[1]) > 7.0 or ext[2] > 3.0:   # walls / buildings, not objects
            continue
        clusters.append(dict(center=(p[:, :2].max(0) + p[:, :2].min(0)) / 2, n=len(p)))
    return clusters


def match(clusters, objs, gt_ids):
    """Returns (set of detected GT ids, number of false-positive clusters)."""
    centers = np.array([c["center"] for c in clusters]).reshape(-1, 2)
    used = np.zeros(len(centers), bool)
    hit = set()
    for i in gt_ids:
        o = objs[i]
        if not len(centers):
            break
        d = np.hypot(centers[:, 0] - o["cx"], centers[:, 1] - o["cy"])
        d[used] = np.inf
        j = int(np.argmin(d))
        if d[j] < MATCH_DIST[o["cls"]]:
            hit.add(i)
            used[j] = True
    # clusters near a GT (fragments of a detected object) are not counted as FP
    fp = 0
    for j in np.where(~used)[0]:
        if not any(np.hypot(*(centers[j] - (objs[i]["cx"], objs[i]["cy"]))) < MATCH_DIST[objs[i]["cls"]]
                   for i in gt_ids):
            fp += 1
    return hit, fp


# ---------------------------------------------------------------- health score
def health_stats(pc):
    xyz = pc["xyz"]
    r = np.linalg.norm(xyz, axis=1)
    ground = (np.abs(xyz[:, 2] - GROUND_Z) < 0.5) & (r > 5) & (r < 20)
    return dict(
        n=len(xyz),
        beam=np.bincount(pc["ring"], minlength=N_BEAMS),
        sector=np.bincount(pc["az"] * N_SECTORS // N_AZ, minlength=N_SECTORS),
        near=np.mean((r < 3) & (xyz[:, 2] > GROUND_Z + GROUND_MARGIN)) if len(r) else 0.0,
        ground_std=np.std(xyz[ground, 2]) if ground.sum() > 50 else 1.0,
    )


def calibrate(clean_pcs):
    """Baseline from clean scans of the same sensor (what you'd log at commissioning)."""
    s = [health_stats(p) for p in clean_pcs]
    return dict(
        n=np.median([x["n"] for x in s]),
        beam=np.median([x["beam"] for x in s], 0),
        sector=np.median([x["sector"] for x in s], 0),
        ground_std=np.median([x["ground_std"] for x in s]),
    )


def health_score(pc, base):
    """GT-free health in [0,1] = worst of 5 components. Returns (score, components)."""
    s = health_stats(pc)
    beams = base["beam"] > 10
    comp = dict(
        return_rate=min(1.0, s["n"] / base["n"] / 0.9),
        beam_coverage=np.mean(s["beam"][beams] >= 0.3 * base["beam"][beams]),
        sector_coverage=np.mean(s["sector"] >= 0.5 * base["sector"]),
        near_clutter=float(np.clip(1 - s["near"] / 0.02, 0, 1)),
        ground_flatness=float(np.clip(1 - (s["ground_std"] - base["ground_std"]) / 0.1, 0, 1)),
    )
    return min(comp.values()), comp
