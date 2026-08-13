"""Spot-check the robust QC flags against the actual signal.

For each participant: band-pass the raw obci_eeg1 to 1-50 Hz (exactly what the
robust QC scores), print a per-channel numeric audit (SD, max off-diagonal
correlation, robust-z of log-variance, and the flag each criterion would set),
and save a 16-channel time-series grid (common y-scale so flat channels look
flat) with each panel titled by its QC verdict.

    python spotcheck.py EXP05 CTRL09 EXP13 CTRL21
"""
import os
import sys
import warnings

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synapse_qc import qc_core, inventory  # noqa: E402
import mne  # noqa: E402

warnings.filterwarnings("ignore")
mne.set_log_level("ERROR")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "quality", "spotcheck")
WIN = (300.0, 315.0)   # 15 s window in the middle of the recording


def audit(pid):
    p = next((x for x in inventory.discover() if x.pid == pid), None)
    if p is None or not p.xdf_path:
        print(f"{pid}: no recording"); return
    raw_stream, _, status, _ = qc_core.select_obci_streams(p.xdf_path)
    if status != "ok":
        print(f"{pid}: {status}"); return

    raw = qc_core.create_raw(raw_stream, neurable=p.is_neurable)
    qc = qc_core.quality_check(raw, method="robust", verbose=False)
    cfg = qc["config"]
    bp = cfg["qc_bandpass"]

    # Reproduce the exact normalized signal the QC scored.
    norm = raw.copy().filter(l_freq=bp[0], h_freq=bp[1], picks="eeg", verbose=False)
    data = norm.get_data()                     # (16, n) in volts
    chs = norm.ch_names
    sd_uv = data.std(axis=1) * 1e6
    cm = np.corrcoef(data); np.fill_diagonal(cm, np.nan)
    with np.errstate(invalid="ignore"):
        maxoff = np.nanmax(cm, axis=1)
    logv = np.log10(np.maximum(data.var(axis=1), 1e-30))
    med, mad = np.median(logv), __import__("scipy.stats", fromlist=["median_abs_deviation"]).median_abs_deviation(logv)
    rz = (logv - med) / (1.4826 * mad) if mad > 0 else np.zeros_like(logv)

    flat, dead, noisy = set(qc["bads_flat"]), set(qc["bads_variance"]), set(qc["bads_noisy"])
    lowc, hic = set(qc["bads_corr"]), set(qc["bads_highcorr"])

    print(f"\n===== {pid}  score={qc['quality_score']:.0f}  "
          f"(corr_low={cfg['corr_low']}, sd_floor={cfg['sd_floor_uv']}uV, z_thresh={cfg['z_thresh']}) =====")
    print(f"{'ch':5}{'sd_uV':>8}{'maxcorr':>9}{'z(var)':>8}   flags")
    for i, ch in enumerate(chs):
        fl = []
        if ch in flat: fl.append("flat")
        if ch in dead: fl.append("dead")
        if ch in noisy: fl.append("noisy")
        if ch in lowc: fl.append("lowcorr")
        if ch in hic: fl.append("bridge?")
        print(f"{ch:5}{sd_uv[i]:>8.2f}{maxoff[i]:>9.3f}{rz[i]:>8.2f}   {'+'.join(fl)}")
    return p, norm, data, chs, sd_uv, maxoff, qc


def plot(pid, norm, data, chs, sd_uv, maxoff, qc):
    fs = norm.info["sfreq"]
    a, b = int(WIN[0] * fs), int(WIN[1] * fs)
    b = min(b, data.shape[1]); a = min(a, max(0, b - int(15 * fs)))
    t = np.arange(a, b) / fs
    bad = set(qc["bads_combined"])
    # common y-scale: robust, so flat channels read as flat and normals as normal
    ylim = 4 * np.median(sd_uv[sd_uv > 0]) if np.any(sd_uv > 0) else 50

    fig, axes = plt.subplots(4, 4, figsize=(18, 11), sharex=True)
    for i, ch in enumerate(chs):
        ax = axes.flat[i]
        ax.plot(t, data[i, a:b] * 1e6, lw=0.4,
                color="firebrick" if ch in bad else "steelblue")
        ax.set_ylim(-ylim, ylim)
        status = "BAD" if ch in bad else "OK"
        fl = qc_core_flags(ch, qc)
        ax.set_title(f"{ch}  {status}  sd={sd_uv[i]:.1f}uV r={maxoff[i]:.2f}"
                     + (f"  [{fl}]" if fl else ""),
                     fontsize=9, color="firebrick" if ch in bad else "black")
        ax.axhline(0, color="gray", lw=0.3)
    fig.suptitle(f"{pid}  —  robust QC score {qc['quality_score']:.0f}/100  "
                 f"(1-50 Hz, common y=±{ylim:.0f}uV)", fontsize=13)
    fig.supxlabel("time (s)"); fig.supylabel("uV")
    fig.tight_layout(rect=[0, 0.02, 1, 0.98])
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{pid}.png")
    fig.savefig(path, dpi=110); plt.close(fig)
    print(f"  -> {path}")


def qc_core_flags(ch, qc):
    fl = []
    for key, lab in [("bads_flat", "flat"), ("bads_variance", "dead"),
                     ("bads_noisy", "noisy"), ("bads_corr", "lowcorr"),
                     ("bads_highcorr", "bridge?")]:
        if ch in qc.get(key, []):
            fl.append(lab)
    return "+".join(fl)


if __name__ == "__main__":
    pids = sys.argv[1:] or ["EXP05", "CTRL09", "EXP13", "CTRL21"]
    for pid in pids:
        r = audit(pid)
        if r:
            p, norm, data, chs, sd_uv, maxoff, qc = r
            plot(pid, norm, data, chs, sd_uv, maxoff, qc)
