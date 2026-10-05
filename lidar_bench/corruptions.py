"""LiDAR corruptions, 5 severity levels each (in the spirit of Robo3D / KITTI-C / nuScenes-C)."""
import numpy as np

from .sim import N_AZ, N_BEAMS, subset


def dropout(pc, p, rng):
    """Random point dropout (dirty window, low reflectance, weak returns)."""
    return subset(pc, rng.random(len(pc["xyz"])) >= p)


def gaussian_noise(pc, sigma, rng):
    """Per-point xyz jitter (sensor aging, vibration, interference)."""
    out = dict(pc)
    out["xyz"] = pc["xyz"] + rng.normal(0, sigma, pc["xyz"].shape)
    return out


def beam_missing(pc, frac, rng):
    """Whole laser channels dead (hardware fault)."""
    dead = rng.choice(N_BEAMS, int(round(frac * N_BEAMS)), replace=False)
    return subset(pc, ~np.isin(pc["ring"], dead))


def packet_loss(pc, frac, rng, packet_cols=12):
    """UDP packets lost: contiguous azimuth blocks (~4.8 deg each) disappear."""
    n_packets = N_AZ // packet_cols
    lost = rng.choice(n_packets, int(round(frac * n_packets)), replace=False)
    return subset(pc, ~np.isin(pc["az"] // packet_cols, lost))


def fog(pc, alpha, rng):
    """Fog: two-way attenuation exp(-2*alpha*r) drops far returns, backscatter adds near ghosts.
    alpha in 1/m (meteorological visibility ~ 3/alpha)."""
    out = {k: v.copy() for k, v in pc.items()}
    r = np.linalg.norm(out["xyz"], axis=1)
    bs = rng.random(len(r)) < min(0.25, 4 * alpha)
    r_bs = rng.uniform(1.0, np.minimum(8.0, r[bs]))
    out["xyz"][bs] *= (r_bs / r[bs])[:, None]
    out["label"][bs] = -3
    r[bs] = r_bs
    keep = rng.random(len(r)) < np.exp(-2 * alpha * r)
    return subset(out, keep)


def motion_smear(pc, v, rng):
    """Ego moving +x at v m/s, no motion compensation: each point is expressed in the
    sensor frame at its own capture time, so it lags by v*t (up to v*0.1 m)."""
    out = dict(pc)
    xyz = pc["xyz"].copy()
    xyz[:, 0] -= v * pc["t"]
    out["xyz"] = xyz
    return out


def motion_deskewed(pc, v, rng, speed_err=0.05):
    """Proposed fix: motion_smear, then deskew each point by v_est*t using odometry speed
    with 5% (1-sigma) error. Not a corruption - the improvement tested for the failure case."""
    out = motion_smear(pc, v, rng)
    v_est = v * (1 + rng.normal(0, speed_err))
    out["xyz"] = out["xyz"].copy()
    out["xyz"][:, 0] += v_est * pc["t"]
    return out


# name -> (function, severity levels 1..5, unit)
CORRUPTIONS = {
    "dropout":        (dropout,        [0.2, 0.4, 0.6, 0.8, 0.9],     "drop prob"),
    "gaussian_noise": (gaussian_noise, [0.02, 0.05, 0.1, 0.15, 0.25], "sigma m"),
    "beam_missing":   (beam_missing,   [0.2, 0.4, 0.6, 0.75, 0.875],  "dead beam frac"),
    "packet_loss":    (packet_loss,    [0.05, 0.1, 0.2, 0.3, 0.5],    "lost packet frac"),
    "fog":            (fog,            [0.005, 0.01, 0.02, 0.03, 0.06], "alpha 1/m"),
    "motion_smear":   (motion_smear,   [5, 10, 15, 20, 30],           "ego speed m/s"),
}

FIXES = {
    "motion+deskew":  (motion_deskewed, [5, 10, 15, 20, 30],          "ego speed m/s"),
}
