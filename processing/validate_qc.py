"""Validate the QC's bad-channel calls against an INDEPENDENT physiological marker.

The QC decides using amplitude, SD, log-variance robust-z and inter-channel
correlation. Checking those same numbers back (as ``spotcheck.py`` prints them)
is circular. This script instead asks a question the QC never asks:

    does this channel's power spectrum look like brain?

Real EEG has a 1/f-shaped aperiodic background and usually an alpha (8-12 Hz)
bump sitting above it. A disconnected or railed electrode has neither -- its
spectrum is flat/white or line-dominated -- yet it can easily pass an
amplitude or variance test. Spectral SHAPE is independent of every QC
criterion, so agreement between the two is real convergent evidence and
disagreement localises exactly which channels a human should look at.

Per channel it measures:
  * ``slope``       - aperiodic exponent: OLS fit of log10(power) on log10(freq)
                      over 2-40 Hz, EXCLUDING 7-14 Hz so the alpha bump does not
                      drag the fit. Real EEG is clearly negative; white noise ~0.
  * ``alpha_db``    - how far mean 8-12 Hz power sits ABOVE that aperiodic fit,
                      in dB. > 0 means a genuine alpha peak, not just more power.

Then it reports, over every channel of every scored recording, how well those
two separate the QC's good/bad calls (AUC via the Mann-Whitney U statistic;
0.5 = no better than chance, 1.0 = perfect), and lists the disagreements:

  * FALSE-POSITIVE candidates - QC says bad, spectrum looks like real brain
  * MISS candidates           - QC says good, spectrum looks like nothing

    python validate_qc.py                 # every scored participant
    python validate_qc.py EXP52 CTRL28    # a subset
"""
import os
import sys
import csv
import warnings

import numpy as np
from scipy.stats import mannwhitneyu

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synapse_qc import qc_core, inventory, paths as qpaths  # noqa: E402

warnings.filterwarnings("ignore")
import mne  # noqa: E402
mne.set_log_level("ERROR")

FIT_BAND = (2.0, 40.0)      # aperiodic fit range
ALPHA = (8.0, 12.0)         # alpha band
EXCLUDE = (7.0, 14.0)       # kept out of the aperiodic fit


def spectral_markers(raw):
    """Return (ch_names, slope[], alpha_db[]) from the Welch PSD.

    The PSD is computed on the DC-removed signal, NOT the QC's 1-50 Hz copy --
    we want the spectrum's own shape, not one the QC pre-shaped.
    """
    r = raw.copy().filter(l_freq=1.0, h_freq=None, picks="eeg", verbose=False)
    psd = r.compute_psd(method="welch", fmin=1.0, fmax=45.0,
                        n_fft=int(4 * r.info["sfreq"]), verbose=False)
    p, f = psd.get_data(), psd.freqs
    logf, logp = np.log10(f), np.log10(np.maximum(p, 1e-30))

    fit_m = (f >= FIT_BAND[0]) & (f <= FIT_BAND[1]) & ~((f >= EXCLUDE[0]) & (f <= EXCLUDE[1]))
    a_m = (f >= ALPHA[0]) & (f <= ALPHA[1])

    x = logf[fit_m]
    X = np.vstack([x, np.ones_like(x)]).T
    slope, alpha_db = [], []
    for i in range(p.shape[0]):
        b, a = np.linalg.lstsq(X, logp[i, fit_m], rcond=None)[0]
        slope.append(b)
        pred = b * logf[a_m] + a                       # aperiodic baseline at alpha
        alpha_db.append(10.0 * np.mean(logp[i, a_m] - pred))
    return list(r.ch_names), np.array(slope), np.array(alpha_db)


# Recordings where every channel is dead -- kept out of the headline comparison
# because "bad" there is not in question and would inflate the separation.
ALL_DEAD = {"CTRL11", "CTRL13", "CTRL14", "CTRL15", "CTRL16", "EXP12", "EXP14"}


def auc(good_vals, bad_vals):
    """P(a QC-good channel is MORE brain-like than a QC-bad one). 0.5 = chance.

    Always pass brain-likeness, i.e. steepness = -slope, so that higher is more
    brain-like and AUC reads in the intuitive direction.
    """
    if len(bad_vals) == 0 or len(good_vals) == 0:
        return float("nan")
    u = mannwhitneyu(good_vals, bad_vals, alternative="two-sided").statistic
    return u / (len(good_vals) * len(bad_vals))


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
            chs, slope, alpha_db = spectral_markers(raw)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {p.pid}: {e}")
            continue

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
                "sd_uv": round(float(qc["ch_sd_uv"][i]), 3),
                "corr_bad_frac": (round(float(frac[i]), 3) if i < frac.size else ""),
            })
        n_bad = sum(1 for r in rows[-len(chs):] if r["qc"] == "BAD")
        print(f"{p.pid:8} {n_bad:2d}/{len(chs)} bad | "
              f"slope {np.mean(slope):+.2f}  alpha {np.mean(alpha_db):+.1f} dB", flush=True)

    if not rows:
        print("no recordings scored")
        return

    csv_path = os.path.join(out_dir, "channel_validation.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # Headline comparison excludes the all-dead recordings (see ALL_DEAD).
    live = [r for r in rows if r["participant"] not in ALL_DEAD]
    good = [r for r in live if r["qc"] == "OK"]
    bad = [r for r in live if r["qc"] == "BAD"]
    steep = lambda rs: np.array([-r["slope"] for r in rs])      # noqa: E731
    alph = lambda rs: np.array([r["alpha_db"] for r in rs])     # noqa: E731
    gs, bs, ga, ba = steep(good), steep(bad), alph(good), alph(bad)

    print("\n" + "=" * 72)
    print(f"{len(rows)} channels total; headline uses {len(live)} from recordings that "
          f"are not wholly dead\n  ({len(good)} QC-good, {len(bad)} QC-bad)")
    print(f"\n{'marker':>16} {'QC-good':>18} {'QC-bad':>18} {'AUC':>7}")
    print(f"{'steepness(-slope)':>16} {np.mean(gs):>9.2f}±{np.std(gs):<8.2f} "
          f"{np.mean(bs):>9.2f}±{np.std(bs):<8.2f} {auc(gs, bs):>7.3f}")
    print(f"{'alpha_db':>16} {np.mean(ga):>9.2f}±{np.std(ga):<8.2f} "
          f"{np.mean(ba):>9.2f}±{np.std(ba):<8.2f} {auc(ga, ba):>7.3f}")
    print("\n(AUC = P(a QC-good channel is MORE brain-like than a QC-bad one);"
          "\n 0.5 = the QC's calls carry no spectral information at all.)")

    # Per-criterion: which of the four QC rules does the independent marker back?
    print(f"\n{'criterion':>10} {'n':>5} {'steepness':>11} {'AUC':>7}   verdict")
    for crit, label in (("flat", "flat"), ("variance", "dead"),
                        ("noisy", "noisy"), ("corr", "corr")):
        sel = [r for r in live if crit in r["flags"]]
        if len(sel) < 5:
            continue
        a = auc(gs, steep(sel))
        verdict = ("strongly supported" if a >= 0.75 else
                   "supported" if a >= 0.65 else
                   "weak support" if a >= 0.55 else
                   "NOT supported by this marker")
        print(f"{label:>10} {len(sel):>5} {np.mean(steep(sel)):>+11.2f} {a:>7.3f}   {verdict}")
    print("\nCaveat: a steep slope means either genuine 1/f brain activity OR"
          "\nlow-frequency artifact swamping the fit, so this marker cannot"
          "\nadjudicate the `noisy` criterion (which targets exactly that excess"
          "\nlow-frequency power). Use a task-locked test for that one.")

    # Disagreements: where the independent marker contradicts the QC.
    # Thresholds are the good-channel distribution's own 10th percentile, so
    # "looks like brain" is defined by this dataset, not an imported constant.
    steep_cut = np.percentile(gs, 90)      # unusually brain-like
    flat_cut = np.percentile(gs, 10)       # unusually un-brain-like
    fp = [r for r in bad if -r["slope"] >= steep_cut]
    miss = [r for r in good if -r["slope"] <= np.percentile(bs, 10)]

    print(f"\nthresholds from the QC-good distribution: steepness >= {steep_cut:.2f} "
          f"(brain-like), <= {flat_cut:.2f} (not)")
    print(f"\nFALSE-POSITIVE candidates (QC=BAD but spectrum looks like brain): {len(fp)}")
    for r in fp[:25]:
        print(f"  {r['participant']:8} {r['channel']:4} flags={r['flags']:22} "
              f"slope={r['slope']:+.2f} alpha={r['alpha_db']:+.1f}dB")
    print(f"\nMISS candidates (QC=OK but spectrum looks like nothing): {len(miss)}")
    for r in miss[:25]:
        print(f"  {r['participant']:8} {r['channel']:4} "
              f"slope={r['slope']:+.2f} alpha={r['alpha_db']:+.1f}dB sd={r['sd_uv']}uV")
    print(f"\nwrote {csv_path}")
    print("Visually inspect the listed channels with:  python spotcheck.py <PID>")


if __name__ == "__main__":
    main()
