"""Synthetic spinning-LiDAR simulator (32 beams, 360 deg) for a straight road scene.

A point cloud is a dict of aligned numpy arrays:
    xyz   (N,3) float  sensor frame, z up, sensor at height SENSOR_H above ground
    ring  (N,)  int    beam index 0..N_BEAMS-1
    az    (N,)  int    azimuth column index 0..N_AZ-1
    t     (N,)  float  capture time within the sweep [0, SWEEP_T)
    label (N,)  int    object id >= 0, -1 ground, -2 wall, -3 fog/noise
"""
import numpy as np

SENSOR_H = 1.8
GROUND_Z = -SENSOR_H
N_BEAMS = 32
V_FOV = (-25.0, 15.0)        # deg, similar to a VLP-32 / HDL-32 class sensor
AZ_RES = 0.4                 # deg
N_AZ = int(360 / AZ_RES)
MAX_RANGE = 80.0
SWEEP_T = 0.1                # 10 Hz
RANGE_NOISE = 0.01           # m, clean sensor noise

SIZES = {"car": (4.5, 1.9, 1.6), "ped": (0.7, 0.7, 1.8)}


def make_scene(rng, n_cars=15, n_peds=10):
    """Objects placed on a road corridor |y| < 12 m between two walls."""
    objs = []
    want = ["car"] * n_cars + ["ped"] * n_peds
    while want:
        cls = want[-1]
        r, th = rng.uniform(5, 60), rng.uniform(-np.pi, np.pi)
        cx, cy = r * np.cos(th), r * np.sin(th)
        if abs(cy) > 12:
            continue
        if any(np.hypot(cx - o["cx"], cy - o["cy"]) < 4.0 for o in objs):
            continue
        l, w, h = SIZES[cls]
        yaw = rng.normal(0, 0.15) if cls == "car" else rng.uniform(-np.pi, np.pi)
        objs.append(dict(cls=cls, cx=cx, cy=cy, yaw=yaw, l=l, w=w, h=h))
        want.pop()
    walls = [dict(cls="wall", cx=0.0, cy=s * 16.0, yaw=0.0, l=160.0, w=0.5, h=3.0) for s in (-1, 1)]
    return objs, walls


def _ray_box(d, box):
    """Ray (origin 0) vs yawed box. Returns hit distance per ray (inf = miss)."""
    c, s = np.cos(box["yaw"]), np.sin(box["yaw"])
    center = np.array([box["cx"], box["cy"], GROUND_Z + box["h"] / 2])
    half = np.array([box["l"], box["w"], box["h"]]) / 2
    rot_t = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])  # world -> box
    o = rot_t @ (-center)
    db = d @ rot_t.T
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (-half - o) / db
        t2 = (half - o) / db
    tmin = np.nanmax(np.minimum(t1, t2), axis=1)
    tmax = np.nanmin(np.maximum(t1, t2), axis=1)
    hit = (tmax >= np.maximum(tmin, 0)) & (tmin > 0)
    return np.where(hit, tmin, np.inf)


def simulate(objs, walls, rng):
    elev = np.deg2rad(np.linspace(V_FOV[0], V_FOV[1], N_BEAMS))
    azim = np.deg2rad(np.arange(N_AZ) * AZ_RES)
    E, A = np.meshgrid(elev, azim, indexing="ij")
    ring, az = np.meshgrid(np.arange(N_BEAMS), np.arange(N_AZ), indexing="ij")
    d = np.stack([np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E)], -1).reshape(-1, 3)

    t_best = np.full(len(d), np.inf)
    label = np.full(len(d), -9)
    down = d[:, 2] < 0
    t_best[down] = SENSOR_H / -d[down, 2]
    label[down] = -1
    for i, b in enumerate(objs + walls):
        tb = _ray_box(d, b)
        closer = tb < t_best
        t_best[closer] = tb[closer]
        label[closer] = i if i < len(objs) else -2

    valid = t_best < MAX_RANGE
    rng_m = t_best[valid] + rng.normal(0, RANGE_NOISE, valid.sum())
    return dict(
        xyz=d[valid] * rng_m[:, None],
        ring=ring.ravel()[valid],
        az=az.ravel()[valid],
        t=az.ravel()[valid] / N_AZ * SWEEP_T,
        label=label[valid],
    )


def subset(pc, mask):
    return {k: v[mask] for k, v in pc.items()}
