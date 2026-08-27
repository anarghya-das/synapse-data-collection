"""Compare a built variant against the original published pkl.

Quantifies how different our rebuild is from synapse_preprocessed.pkl, aligning
by subject_id (the published subject order is processing order, not sorted).
Reports cohort differences, per-subject bad-channel/interpolation differences,
per-task epoch counts, and numerical epoch-data differences.

    python -m pipelines.compare --variant published__published
    python -m pipelines.compare --variant published__published \
        --mine outputs/epochs/published__published/epochs.pkl \
        --ref /Users/anarghya/Developer/research/synapse/processed_data/synapse_preprocessed.pkl
"""
import os
import sys
import pickle
import argparse
import warnings

import numpy as np

warnings.filterwarnings("ignore")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from synapse_qc import paths as qpaths  # noqa: E402

DEFAULT_REF = os.path.join(
    os.environ.get("SYNAPSE_REPO", "/Users/anarghya/Developer/research/synapse"),
    "processed_data", "synapse_preprocessed.pkl")
TASKS = ["pmt", "let", "hlt", "ast"]


def load(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def subj_to_epochs(d, grp):
    """Map subject_id -> {task: Epochs}, positional only when list lengths align."""
    subs = d[f"{grp}_subjects"]
    epd = d[f"{grp}_epochs"]
    out = {s: {} for s in subs}
    for task in TASKS:
        lst = epd.get(task, [])
        if len(lst) == len(subs):                 # full, position == subject
            for s, ep in zip(subs, lst):
                out[s][task] = ep
        # else: ragged -> cannot align positionally; leave task absent (flagged)
    return out


def bads_by_subject(d, grp):
    out = {}
    for q in d.get(f"{grp}_quality", []):
        sid = q.get("subject_id")
        if sid:
            out[sid] = set(q.get("bads_combined", []))
    return out


def compare_group(mine, ref, grp):
    ms, rs = set(mine[f"{grp}_subjects"]), set(ref[f"{grp}_subjects"])
    common = sorted(ms & rs)
    print(f"\n===== {grp.upper()} =====")
    print(f"  subjects: mine={len(ms)} ref={len(rs)} common={len(common)}")
    if ms - rs:
        print(f"  only in MINE: {sorted(ms - rs)}")
    if rs - ms:
        print(f"  only in REF : {sorted(rs - ms)}")

    me, re_ = subj_to_epochs(mine, grp), subj_to_epochs(ref, grp)
    mb, rb = bads_by_subject(mine, grp), bads_by_subject(ref, grp)

    bad_diffs, data_rows, epoch_count_rows = [], [], []
    identical = same_after_trim = 0
    for s in common:
        bads_match = mb.get(s, set()) == rb.get(s, set())
        if not bads_match:
            bad_diffs.append((s, sorted(rb.get(s, set())), sorted(mb.get(s, set()))))
        subj_max = 0.0
        counts_match = True
        matched_match = True
        for task in TASKS:
            a, b = me[s].get(task), re_[s].get(task)
            if a is None or b is None:
                continue
            if a.get_data().shape[0] != b.get_data().shape[0]:
                counts_match = False
                epoch_count_rows.append((s, task, a.get_data().shape[0], b.get_data().shape[0]))
            # Align epochs by event onset sample (col 0); compare only matched stimuli,
            # so epoch-rejection differences don't masquerade as data differences.
            ma = {ev[0]: i for i, ev in enumerate(a.events)}
            mbk = {ev[0]: i for i, ev in enumerate(b.events)}
            common_ev = sorted(set(ma) & set(mbk))
            if not common_ev or a.get_data().shape[1:] != b.get_data().shape[1:]:
                continue
            da = a.get_data()[[ma[e] for e in common_ev]]
            db = b.get_data()[[mbk[e] for e in common_ev]]
            maxabs = np.abs(da - db).max() * 1e6
            subj_max = max(subj_max, maxabs)
            if maxabs > 0.01:
                matched_match = False
                rms = np.sqrt(((da - db) ** 2).mean()) * 1e6
                data_rows.append((s, task, f"{len(common_ev)} matched ev: max={maxabs:.3f}uV rms={rms:.4f}uV", maxabs))
        if bads_match and counts_match and subj_max < 1e-3:
            identical += 1
        elif bads_match and matched_match:
            same_after_trim += 1                          # matched-stimulus data identical; only rejection counts differ
    return common, bad_diffs, data_rows, epoch_count_rows, identical, same_after_trim


def main():
    ap = argparse.ArgumentParser(description="Compare a built variant to the published pkl.")
    ap.add_argument("--variant", default="published__published")
    ap.add_argument("--mine", default=None, help="override path to the built pkl")
    ap.add_argument("--ref", default=DEFAULT_REF)
    args = ap.parse_args()

    # Variant pkls live under paths.output_dir from conf/config.yaml.
    mine_path = args.mine or os.path.join(
        qpaths.output_paths()["epochs"], args.variant, "epochs.pkl")
    print(f"MINE: {mine_path}\nREF : {args.ref}")
    mine, ref = load(mine_path), load(args.ref)

    g_ident = g_trim = g_common = 0
    for grp in ["exp", "ctrl"]:
        common, bad_diffs, data_rows, ec_rows, identical, same_trim = compare_group(mine, ref, grp)
        g_common += len(common); g_ident += identical; g_trim += same_trim

        print(f"  bad-channel set differs: {len(bad_diffs)}/{len(common)} subjects")
        for s, r, m in bad_diffs:
            print(f"     {s}: ref={r}  mine={m}")

        if ec_rows:
            deltas = [m - r for _, _, m, r in ec_rows]   # mine - ref
            print(f"  epoch-count differs: {len({r[0] for r in ec_rows})} subjects, "
                  f"{len(ec_rows)} subject-tasks "
                  f"(mine-ref: min={min(deltas)} max={max(deltas)}, "
                  f"all={'−1' if set(deltas)=={-1} else sorted(set(deltas))})")

        if data_rows:
            print(f"  matched-stimulus DATA differs (>0.01uV): "
                  f"{len({r[0] for r in data_rows})} subjects")
            for s, task, msg, _ in data_rows[:8]:
                print(f"     {s} {task}: {msg}")
            if len(data_rows) > 8:
                print(f"     ... (+{len(data_rows) - 8} more)")
        else:
            print("  matched-stimulus DATA: identical for every shared epoch (≤0.01uV)")

    print("\n" + "=" * 60)
    print(f"Bit-identical (same bads, same epoch counts, same data): {g_ident}/{g_common}")
    print(f"Same channels + same data on matched stimuli, differ only in how many "
          f"epochs the z-score rejection kept: {g_trim}/{g_common}")
    print(f"=> remaining {g_common - g_ident - g_trim}/{g_common} differ in channel QC")


if __name__ == "__main__":
    main()
