"""Validate the QC's bad-channel calls against markers the QC never examines.

Checking the QC's own SD / variance-z / correlation back (as ``spotcheck.py``
prints them) is circular. This script scores every channel on two independent
families of evidence and reports how well each separates the QC's good/bad
calls, per criterion.

1. SPECTRAL SHAPE (passive)
   * ``slope``    - aperiodic exponent: OLS fit of log10(power) on log10(freq)
                    over 2-40 Hz, EXCLUDING 7-14 Hz so an alpha bump does not
                    drag the fit. Real EEG is clearly negative; white noise ~0.
   * ``alpha_db`` - mean 8-12 Hz power ABOVE that aperiodic fit, in dB.
   Caveat: a steep slope means either genuine 1/f activity OR low-frequency
   artifact swamping the fit, so this family cannot adjudicate the ``noisy``
   criterion -- which targets exactly that excess low-frequency power. Alpha is
   also near-useless at the ear (cEEGrid sits far from the alpha generators).

2. TASK-LOCKED RESPONSE (active) -- the decisive test
   ``erp_z`` asks whether the channel carries a response time-locked to the
   auditory stimuli. Stimulus onsets come from the XDF marker stream
   (``<task>_stim...``). Each channel's epochs are baseline-corrected and
   averaged, and the RMS of that evoked average over the post-stimulus window
   is compared against a NULL built by re-running the identical computation on
   randomly placed onsets. ``erp_z`` is how many null SDs the real evoked
   response exceeds the surrogate mean.

   Why this settles what the spectrum cannot: a dead or disconnected electrode
   cannot phase-lock to a stimulus no matter how much variance it carries, and
   the surrogate null is built per channel, so a merely noisy channel widens
   its own null rather than scoring higher. It is causally tied to the
   experiment and independent of every QC criterion.

    python validate_qc.py                 # every scored participant
    python validate_qc.py EXP52 CTRL28    # a subset
"""
import os
import re
import sys
import csv
import warnings

import numpy as np
import pyxdf
from scipy.stats import mannwhitneyu

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synapse_qc import qc_core, inventory, paths as qpaths  # noqa: E402

warnings.filterwarnings("ignore")
import mne  # noqa: E402
mne.set_log_level("ERROR")

FIT_BAND = (2.0, 40.0)      # aperiodic fit range
ALPHA = (8.0, 12.0)
EXCLUDE = (7.0, 14.0)       # kept out of the aperiodic fit

ERP_TMIN, ERP_TMAX = -0.2, 0.6      # epoch window (s) around stimulus onset
ERP_BAND = (1.0, 20.0)              # auditory ERP band
N_SURROGATE = 200
STIM_RE = re.compile(r"^(pmt|hlt|let|ast)_stim\b")

# Recordings where every channel is dead -- kept out of the headline comparison
# because "bad" there is not in question and would inflate the separation.
ALL_DEAD = {"CTRL11", "CTRL13", "CTRL14", "CTRL15", "CTRL16", "EXP12", "EXP14"}


def auc(good_vals, bad_vals):
    """P(a QC-good channel scores MORE brain-like than a QC-bad one).

    Always pass brain-likeness (higher = more brain-like), so AUC reads in the
    intuitive direction: 0.5 = the QC's calls carry no information about it.
    """
    if len(bad_vals) == 0 or len(good_vals) == 0:
        return float("nan")
    u = mannwhitneyu(good_vals, bad_vals, alternative="two-sided").statistic
    return u / (len(good_vals) * len(bad_vals))


def spectral_markers(raw):
    """(slope[], alpha_db[]) from the Welch PSD of the DC-removed signal."""
    r = raw.copy().filter(l_freq=1.0, h_freq=None, picks="eeg", verbose=False)
    psd = r.compute_psd(method="welch", fmin=1.0, fmax=45.0,
                        n_fft=int(4 * r.info["sfreq"]), verbose=False)
    p, f = psd.get_data(), psd.freqs
    logf, logp = np.log10(f), np.log10(np.maximum(p, 1e-30))
    fit_m = ((f >= FIT_BAND[0]) & (f <= FIT_BAND[1])
             & ~((f >= EXCLUDE[0]) & (f <= EXCLUDE[1])))
    a_m = (f >= ALPHA[0]) & (f <= ALPHA[1])
    X = np.vstack([logf[fit_m], np.ones(fit_m.sum())]).T
    slope, alpha_db = [], []
    for i in range(p.shape[0]):
        b, a = np.linalg.lstsq(X, logp[i, fit_m], rcond=None)[0]
        slope.append(b)
        alpha_db.append(10.0 * np.mean(logp[i, a_m] - (b * logf[a_m] + a)))
    return np.array(slope), np.array(alpha_db)


def stim_onset_indices(xdf_path, eeg_stream):
    """Sample indices of every ``<task>_stim`` marker, in EEG-sample space."""
    data, _ = pyxdf.load_xdf(xdf_path)
    mstreams = [s for s in data if s["info"]["type"][0].lower().startswith("marker")]
    if not mstreams:
        return np.array([], dtype=int)
    ms = mstreams[0]
    labels = np.atleast_1d(np.array(ms["time_series"]).squeeze())
    ts = np.asarray(ms["time_stamps"]).squeeze()
    keep = [i for i, lab in enumerate(labels) if STIM_RE.match(str(lab).strip())]
    if not keep:
        return np.array([], dtype=int)
    return qc_core.closest_points_vector(
        np.asarray(eeg_stream["time_stamps"]), ts[np.atleast_1d(keep)]).astype(int)


def _evoked_rms(data, onsets, i0, i1, n_base):
    """RMS of the trial-averaged, baseline-corrected response, per channel."""
    n_ch, n_t = data.shape
    ok = onsets[(onsets + i0 >= 0) & (onsets + i1 < n_t)]
    if len(ok) < 5:
        return None
    idx = ok[:, None] + np.arange(i0, i1)[None, :]        # (n_trials, n_win)
    ep = data[:, idx]                                      # (n_ch, n_trials, n_win)
    ep = ep - ep[:, :, :n_base].mean(axis=2, keepdims=True)
    evoked = ep.mean(axis=1)                               # (n_ch, n_win)
    return np.sqrt((evoked[:, n_base:] ** 2).mean(axis=1))


def task_locked_z(raw, onsets, seed=0):
    """Per-channel z of the evoked response against a shuffled-onset null."""
    r = raw.copy().filter(l_freq=ERP_BAND[0], h_freq=ERP_BAND[1],
                          picks="eeg", verbose=False)
    data = r.get_data()
    sf = r.info["sfreq"]
    i0, i1 = int(round(ERP_TMIN * sf)), int(round(ERP_TMAX * sf))
    n_base = -i0
    real = _evoked_rms(data, onsets, i0, i1, n_base)
    if real is None:
        return None, 0

    rng = np.random.default_rng(seed)
    lo, hi = -i0, data.shape[1] - i1 - 1
    null = np.empty((N_SURROGATE, data.shape[0]))
    for k in range(N_SURROGATE):
        fake = rng.integers(lo, hi, size=len(onsets))
        null[k] = _evoked_rms(data, fake, i0, i1, n_base)
    mu, sd = null.mean(axis=0), null.std(axis=0)
    return (real - mu) / np.maximum(sd, 1e-30), len(onsets)


def main():
    only = set(sys.argv[1:])
    out_dir = os.path.join(qpaths.output_paths()["qc"], "validation")
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    for p in inventory.discover():
        if only and p.pid not in only:
            continue
        if not p.xdf_path:
            continue
        try:
            rs, _, st, _ = qc_core.select_obci_streams(p.xdf_path)
            if st != "ok":
                continue
            raw = qc_core.create_raw(rs, neurable=p.is_neurable)
            qc = qc_core.quality_check(raw, method="robust", verbose=False)
            slope, alpha_db = spectral_markers(raw)
            onsets = stim_onset_indices(p.xdf_path, rs)
            erp_z, n_stim = task_locked_z(raw, onsets) if len(onsets) else (None, 0)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {p.pid}: {e}", flush=True)
            continue

        chs = qc["ch_names"]
        bad = set(qc["bads_combined"])
        frac = np.asarray(qc.get("corr_bad_frac", []), dtype=float)
        for i, ch in enumerate(chs):
            rows.append({
                "participant": p.pid, "channel": ch,
                "qc": "BAD" if ch in bad else "OK",
                "flags": "+".join(k.replace("bads_", "") for k in
                                  ("bads_flat", "bads_variance", "bads_noisy", "bads_corr")
                                  if ch in qc.get(k, [])),
                "slope": round(float(slope[i]), 3),
                "alpha_db": round(float(alpha_db[i]), 2),
                "erp_z": (round(float(erp_z[i]), 2) if erp_z is not None else ""),
                "n_stim": n_stim,
                "sd_uv": round(float(qc["ch_sd_uv"][i]), 3),
                "corr_bad_frac": (round(float(frac[i]), 3) if i < frac.size else ""),
            })
        ez = f"{np.mean(erp_z):+.2f}" if erp_z is not None else "  n/a"
        print(f"{p.pid:8} {len(bad):2d}/{len(chs)} bad | slope {np.mean(slope):+.2f} "
              f"| erp_z {ez} ({n_stim} stim)", flush=True)

    if not rows:
        print("no recordings scored")
        return

    csv_path = os.path.join(out_dir, "channel_validation.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    live = [r for r in rows if r["participant"] not in ALL_DEAD]
    good = [r for r in live if r["qc"] == "OK"]
    has_erp = [r for r in live if r["erp_z"] != ""]

    # ---- POSITIVE CONTROL -------------------------------------------------
    # Before the task-locked test may judge anything, it has to show it can
    # detect a stimulus response AT ALL -- in channels the QC calls good, which
    # are the best candidates for carrying one. If those do not exceed their own
    # shuffled-onset null, the measure is not sensitive enough on this data and
    # any good/bad separation it reports would be noise.
    ctrl = np.array([r["erp_z"] for r in has_erp if r["qc"] == "OK"], dtype=float)
    erp_usable = False
    if len(ctrl) >= 20:
        # one-sample: is mean erp_z of QC-good channels meaningfully above 0?
        t = ctrl.mean() / (ctrl.std(ddof=1) / np.sqrt(len(ctrl)))
        erp_usable = ctrl.mean() > 0.5 and t > 3
        print("\n" + "-" * 74)
        print("POSITIVE CONTROL for the task-locked test")
        print(f"  QC-good channels: mean erp_z = {ctrl.mean():+.2f} "
              f"(SD {ctrl.std():.2f}, n={len(ctrl)}, t={t:+.1f})")
        if erp_usable:
            print("  PASS - good channels show a stimulus-locked response above their"
                  "\n  own shuffled-onset null, so erp_z can be used as evidence below.")
        else:
            print("  FAIL - even QC-good channels do not beat their shuffled-onset null,"
                  "\n  so this dataset has no single-channel stimulus-locked response to"
                  "\n  detect and erp_z CANNOT adjudicate the QC. Its AUC is reported for"
                  "\n  completeness only and must not be read as evidence either way.")
            print("  Likely causes: (a) ~90 trials against ~80 uV single-trial noise puts"
                  "\n  the averaging noise floor near 9 uV, far above the 1-2 uV ear-EEG"
                  "\n  auditory ERP; (b) the psychoacoustic tasks present many stimuli at"
                  "\n  or near hearing threshold, which by design evoke little cortex;"
                  "\n  (c) cEEGrid references within the grid, so a near common-mode"
                  "\n  auditory response largely subtracts out -- the cEEGrid ERP"
                  "\n  literature reads P300/N100 from BIPOLAR derivations, not from"
                  "\n  single referenced channels, which a per-channel test cannot use.")

    print("\n" + "=" * 74)
    print(f"{len(rows)} channels total; headline uses {len(live)} from recordings that "
          f"are not wholly dead ({len(good)} QC-good, {len(live)-len(good)} QC-bad)")
    print(f"task-locked test available for {len(has_erp)} channels")

    markers = [
        ("steepness(-slope)", lambda r: -r["slope"], live),
        ("alpha_db", lambda r: r["alpha_db"], live),
        ("erp_z (task-locked)", lambda r: r["erp_z"], has_erp),
    ]
    print(f"\n{'marker':>20} {'QC-good':>17} {'QC-bad':>17} {'AUC':>7}")
    for name, fn, sub in markers:
        g = np.array([fn(r) for r in sub if r["qc"] == "OK"], dtype=float)
        b = np.array([fn(r) for r in sub if r["qc"] == "BAD"], dtype=float)
        print(f"{name:>20} {g.mean():>8.2f}±{g.std():<8.2f} "
              f"{b.mean():>8.2f}±{b.std():<8.2f} {auc(g, b):>7.3f}")

    print("\nPer-criterion AUC (does each QC rule hold up against each marker?)")
    print(f"{'criterion':>10} {'n':>5} {'slope':>9} {'erp_z':>9}   task-locked verdict")
    gs = np.array([-r["slope"] for r in good])
    ge = np.array([r["erp_z"] for r in has_erp if r["qc"] == "OK"], dtype=float)
    for crit, label in (("flat", "flat"), ("variance", "dead"),
                        ("noisy", "noisy"), ("corr", "corr")):
        sel = [r for r in live if crit in r["flags"]]
        sel_e = [r for r in has_erp if crit in r["flags"]]
        if len(sel) < 5:
            continue
        a_s = auc(gs, np.array([-r["slope"] for r in sel]))
        a_e = (auc(ge, np.array([r["erp_z"] for r in sel_e], dtype=float))
               if len(sel_e) >= 5 else float("nan"))
        if not erp_usable:
            verdict = "uninformative (control failed)"
        else:
            verdict = ("strongly supported" if a_e >= 0.75 else
                       "supported" if a_e >= 0.65 else
                       "weak support" if a_e >= 0.55 else
                       "NOT supported" if a_e == a_e else "n/a")
        print(f"{label:>10} {len(sel):>5} {a_s:>9.3f} {a_e:>9.3f}   {verdict}")

    # Channels worth a human's eyes: the two markers disagree with the QC.
    if has_erp and erp_usable:
        erp_cut = np.percentile(ge, 10)     # weak evoked response, by good-channel std
        fp = [r for r in has_erp if r["qc"] == "BAD" and r["erp_z"] >= np.percentile(ge, 50)]
        miss = [r for r in has_erp if r["qc"] == "OK" and r["erp_z"] < erp_cut]
        print(f"\nFALSE-POSITIVE candidates (QC=BAD but a clear task-locked response): "
              f"{len(fp)}")
        for r in sorted(fp, key=lambda r: -r["erp_z"])[:20]:
            print(f"  {r['participant']:8} {r['channel']:4} flags={r['flags']:20} "
                  f"erp_z={r['erp_z']:+6.2f} slope={r['slope']:+.2f}")
        print(f"\nMISS candidates (QC=OK but no task-locked response): {len(miss)}")
        for r in sorted(miss, key=lambda r: r["erp_z"])[:20]:
            print(f"  {r['participant']:8} {r['channel']:4} "
                  f"erp_z={r['erp_z']:+6.2f} slope={r['slope']:+.2f} sd={r['sd_uv']}uV")
    elif has_erp:
        print("\nDisagreement lists from the task-locked test are SUPPRESSED: the"
              "\npositive control failed, so they would rank noise. Use the spectral"
              "\ncandidates and spotcheck.py instead.")

    print(f"\nwrote {csv_path}")
    print("Visually inspect the listed channels with:  python spotcheck.py <PID>")


if __name__ == "__main__":
    main()
