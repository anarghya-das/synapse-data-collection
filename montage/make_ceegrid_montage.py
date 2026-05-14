#!/usr/bin/env python3
"""
Create an MNE-friendly montage CSV for cEEGrid from the openbci-ceegrids .loc file.

Output: ceegrid_montage_head.csv with columns:
    ch_name,x,y,z   (in meters, HEAD coordinate frame)

Optional sanity checks (if mne + matplotlib are installed):
    - 2D topomap plot
    - 3D alignment
    - adjacency degree report
"""

import io
import sys
import math
import argparse
from urllib.request import urlopen
from pathlib import Path
import numpy as np
import mne
import matplotlib.pyplot as plt


def load_loc(path_or_url: str):
    """
    Parse the .loc file (label x y per line, comments allowed).
    Returns labels (list[str]) and 2D array (N,2) of floats.
    """
    def _read_text(p):
        return Path(p).read_text(encoding="utf-8")

    txt = _read_text(path_or_url)
    labels, xs, ys = [], [], []
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("%") or line.startswith("//"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue

        # .loc file format: index x y label (4 columns)
        # Use the 4th column as label if available, otherwise use first column
        if len(parts) >= 4:
            lab, x, y = parts[3], parts[1], parts[2]
        else:
            lab, x, y = parts[0], parts[1], parts[2]

        try:
            labels.append(lab)
            xs.append(float(x))
            ys.append(float(y))
        except ValueError:
            # skip any malformed rows
            continue
    if len(labels) == 0:
        raise RuntimeError(
            "No channel rows parsed. Check the .loc path/format.")
    xy = np.column_stack([np.array(xs, float), np.array(ys, float)])
    return labels, xy


def unit(v):
    n = np.linalg.norm(v)
    return v / (n if n else 1.0)


def ear_patch(local_xy: np.ndarray, side: int, r: float, dy: float, dz: float, eps: float):
    """
    Map a local ear grid to the lateral head surface (HEAD coords, meters).
    side: -1 left, +1 right
    """
    if len(local_xy) == 0:
        raise ValueError(
            "Cannot process empty electrode array. Check that channel labels start with 'L' or 'R'.")

    # center the local grid
    x = local_xy[:, 0] - local_xy[:, 0].mean()
    y = local_xy[:, 1] - local_xy[:, 1].mean()

    # scale factors so the local pattern spans ~dy (A/P) and ~dz (S/I)
    x_rng = np.max(np.abs(x)) if len(x) > 0 and np.max(np.abs(x)) > 0 else 1.0
    y_rng = np.max(np.abs(y)) if len(y) > 0 and np.max(np.abs(y)) > 0 else 1.0
    x_scale = dy / x_rng
    y_scale = dz / y_rng

    # base at LPA/RPA on the sphere
    base = np.c_[np.full(len(x), side * r), np.zeros(len(x)), np.zeros(len(x))]

    # tangential directions: +Y anterior, +Z superior
    # mirror anterior direction for symmetry
    tangential = np.c_[np.zeros(len(x)), -side * x * x_scale, y * y_scale]
    pts = base + tangential

    # normalize to radius r - eps (stay inside the head)
    norms = np.linalg.norm(pts, axis=1, keepdims=True)
    pts = pts / norms * (r - eps)
    return pts


def rot_y(theta_rad: float):
    c, s = math.cos(theta_rad), math.sin(theta_rad)
    return np.array([[c, 0,  s],
                     [0, 1,  0],
                     [-s, 0,  c]], float)


def build_3d_from_loc(labels, xy, r=0.095, dy=0.020, dz=0.030, tilt_deg=20.0, eps=0.002):
    """
    Convert 2D loc layout to 3D HEAD coords on sphere radius r (meters).
    Guarantees ||p|| <= r - eps (strictly inside).
    """
    import re

    def ch_num(label):
        m = re.search(r'\d+', str(label))
        return int(m.group()) if m else 0

    # split by L/R prefix (fallback to number: 1-10 left, 11-20 right)
    left_idx = [i for i, lab in enumerate(
        labels) if str(lab).upper().startswith('L')]
    right_idx = [i for i, lab in enumerate(
        labels) if str(lab).upper().startswith('R')]

    L2d = xy[left_idx]
    R2d = xy[right_idx]

    L3d = ear_patch(L2d, side=-1, r=r, dy=dy, dz=dz,
                    eps=eps) if len(L2d) else np.empty((0, 3))
    R3d = ear_patch(R2d, side=+1, r=r, dy=dy, dz=dz,
                    eps=eps) if len(R2d) else np.empty((0, 3))

    pts = np.vstack([L3d, R3d])

    # small anterior tilt (mirror left/right)
    # theta = math.radians(tilt_deg)
    theta = np.deg2rad(tilt_deg)
    pts[left_idx] = pts[left_idx] @ rot_y(+theta).T
    pts[right_idx] = pts[right_idx] @ rot_y(-theta).T

    # --- Adaptive clamp: make sure EVERY point is strictly <= r - eps ---
    norms = np.linalg.norm(pts, axis=1, keepdims=True)
    pts = pts / norms * (r - eps)

    # return to original label order
    return labels, pts


def write_npz(labels, xyz, out_npz: str, radius):
    nas, lpa, rpa = np.array([0, radius, 0]), np.array(
        [-radius, 0, 0]), np.array([radius, 0, 0])
    np.savez(out_npz, labels=labels, points=xyz, nasion=nas, lpa=lpa, rpa=rpa)
    print(f"[OK] Wrote {out_npz} ({len(labels)} channels)")


def quick_checks(labels, xyz, r):
    info = mne.create_info(ch_names=labels, sfreq=1000., ch_types="eeg")
    # fiducials on the same sphere
    nas, lpa, rpa = np.array([0, r, 0]), np.array(
        [-r, 0, 0]), np.array([r, 0, 0])
    ch_pos = dict(zip(labels, xyz))
    montage = mne.channels.make_dig_montage(
        ch_pos=ch_pos, nasion=nas, lpa=lpa, rpa=rpa, coord_frame="head")
    info.set_montage(montage)

    xyz = np.array([montage.get_positions()['ch_pos'][ch]
                   for ch in info.ch_names])
    radii = np.linalg.norm(xyz, axis=1)
    print("min/mean/max radius (m):", radii.min(), radii.mean(), radii.max())

    # adjacency stats used by autoreject
    from mne.channels import find_ch_adjacency
    adj, _ = find_ch_adjacency(info, ch_type="eeg")
    deg = np.array((adj > 0).sum(axis=1)).ravel()
    print(
        f"-- neighbor degree min/median/max: {deg.min()} / {np.median(deg)} / {deg.max()}")

    info.plot_sensors(kind="topomap", show_names=True)
    # mne.viz.plot_alignment(
    #     info, dig=True, eeg="original", surfaces=[], show_axes=True)
    plt.show()


def main():
    ap = argparse.ArgumentParser(
        description="Create cEEGrid montage CSV from .loc file.")
    ap.add_argument("--loc", type=str, default="cEEGrid_locations.loc",
                    help="Path or URL to the .loc file.")
    ap.add_argument("--out", type=str, default="ceegrid_montage_head.npz",
                    help="Output NPZ path.")
    ap.add_argument("--radius", type=float, default=0.095,
                    help="Head radius in meters (default 0.095).")
    ap.add_argument("--dy", type=float, default=0.020,
                    help="Anterior/posterior spread in meters (default 0.020).")
    ap.add_argument("--dz", type=float, default=0.030,
                    help="Superior/inferior spread in meters (default 0.030).")
    ap.add_argument("--tilt", type=float, default=20.0,
                    help="Anterior tilt in degrees (default 20).")
    ap.add_argument("--eps", type=float, default=0.002,
                    help="Inset from sphere surface in meters (default 0.002).")
    ap.add_argument("--no-checks", action="store_true",
                    help="Skip MNE sanity checks/plots.")
    args = ap.parse_args()

    labels, xy = load_loc(args.loc)
    labels3d, xyz = build_3d_from_loc(labels, xy, r=args.radius, dy=args.dy, dz=args.dz,
                                      tilt_deg=args.tilt, eps=args.eps)
    write_npz(labels3d, xyz, args.out, args.radius)

    if not args.no_checks:
        quick_checks(labels3d, xyz, args.radius)


if __name__ == "__main__":
    main()
