#!/usr/bin/env python3
"""Materialise a dataset variant into a self-contained, shareable bundle.

Variants are stored as VIEWS (decisions only, ~2 MB) over the shared EEG tree —
see ``synapse_qc/dataset.py``. That is right for working locally, where the whole
tree is present, and wrong for handing data to someone else: a view is useless
without ``processed/eeg/``; and a variant's video clips (when it has
any) live in ``processed/video/`` rather than beside the epochs.

This writes a directory that stands on its own:

    <out>/
      labels.csv  build_log.csv  manifest.json  README.md
      <PID>/eeg/sub-<PID>_<task>_epo.fif    finalized epochs, transforms applied
            sub-<PID>_channel_mask.npy      1 = real signal
            sub-<PID>_channels.json
            sub-<PID>_alignment.csv         paths rewritten to be bundle-relative
            video/<task>/*.avi + *_frames.csv   only with --video

    python -m scripts.export_dataset --variant usable_20260904__zero_mask \\
        --out /tmp/synapse_eeg                       # EEG + labels
    python -m scripts.export_dataset --variant ... --out ... --video      # + clips
    python -m scripts.export_dataset --variant ... --out ... --deidentify # strip PII

**Check before you share.** ``labels.csv`` carries date of birth, test dates,
race, sex and the coordinator's internal ids; ``--deidentify`` drops those and
bins age. The video is participants' faces, which is identifiable data governed
by your consent/IRB terms, not by this script.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from synapse_qc import dataset as ds  # noqa: E402

# Direct identifiers dropped by --deidentify. `age` is kept but binned: it is
# stored to ~7 decimal places, which re-derives a date of birth on its own.
PII_COLUMNS = ("dob", "date_tested", "date_tested_openbci", "date_tested_neurable",
               "pc_id", "new_pc_id", "neurable_id", "audio_id")
AGE_BIN = 5


def _deidentify(rows):
    out = []
    for r in rows:
        r = {k: v for k, v in r.items() if k not in PII_COLUMNS}
        try:
            a = float(r.get("age", ""))
            lo = int(a // AGE_BIN) * AGE_BIN
            r["age"] = f"{lo}-{lo + AGE_BIN - 1}"
        except (TypeError, ValueError):
            r["age"] = ""
        out.append(r)
    return out


def _copy_table(src, dst, deidentify=False):
    if not os.path.exists(src):
        return
    with open(src) as fh:
        rows = list(csv.DictReader(fh))
    if deidentify and os.path.basename(src) == "labels.csv":
        rows = _deidentify(rows)
    if not rows:
        shutil.copy2(src, dst)
        return
    with open(dst, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variant", required=True, help="variant directory name")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--base", default=os.environ.get("SYNAPSE_DATA_BASE"),
                    help="data base holding raw/ + processed/")
    ap.add_argument("--dataset-dir", default="processed/dataset/eeg_only")
    ap.add_argument("--video", action="store_true", help="include the clips (large)")
    ap.add_argument("--deidentify", action="store_true",
                    help="drop direct identifiers from labels.csv and bin age")
    ap.add_argument("--subjects", default="", help="comma list; default all")
    args = ap.parse_args()

    if not args.base:
        ap.error("--base or $SYNAPSE_DATA_BASE required")
    vdir = os.path.join(args.base, args.dataset_dir, args.variant)
    if not os.path.isdir(vdir):
        ap.error(f"no such variant: {vdir}")
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    only = {s.strip() for s in args.subjects.split(",") if s.strip()}
    pids = [p for p in ds.subjects(vdir) if not only or p in only]
    print(f"exporting {len(pids)} subjects from {args.variant} -> {out}")

    n_ep = n_clip = 0
    for pid in pids:
        sub_out = out / pid
        (sub_out / "eeg").mkdir(parents=True, exist_ok=True)
        spec = ds._spec(vdir, pid)
        for task, entry in spec["tasks"].items():
            if entry.get("excluded"):
                continue
            ep = ds.load_epochs(vdir, pid, task, base=args.base)
            ep.save(sub_out / "eeg" / f"sub-{pid}_{task}_epo.fif",
                    overwrite=True, verbose=False)
            n_ep += 1
        for name in (f"sub-{pid}_channel_mask.npy", f"sub-{pid}_channels.json"):
            src = os.path.join(vdir, pid, name)
            if os.path.exists(src):
                shutil.copy2(src, sub_out / name)

        rows = ds.load_alignment(vdir, pid)
        if not rows:
            continue
        for r in rows:
            task = r["task"]
            r["eeg_file"] = f"{pid}/eeg/sub-{pid}_{task}_epo.fif"
            if args.video and r.get("video_clip"):
                for col, sub in (("video_clip", "video"),
                                 ("video_frames_csv", "video")):
                    src = os.path.join(args.base, r[col])
                    rel = os.path.join(sub, task, os.path.basename(src))
                    dst = sub_out / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if os.path.exists(src) and not dst.exists():
                        shutil.copy2(src, dst)
                        if col == "video_clip":
                            n_clip += 1
                    r[col] = f"{pid}/{rel}"
            else:
                r.pop("video_clip", None)
                r.pop("video_frames_csv", None)
        with open(sub_out / f"sub-{pid}_alignment.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    for name in ("labels.csv", "build_log.csv"):
        _copy_table(os.path.join(vdir, name), out / name, args.deidentify)

    man = ds.read_manifest(vdir)
    man.update({"layout": ds.LAYOUT_MATERIALIZED, "exported_from": args.variant,
                "includes_video": bool(args.video),
                "deidentified": bool(args.deidentify)})
    (out / "manifest.json").write_text(json.dumps(man, indent=2))

    (out / "README.md").write_text(f"""# SYNAPSE dataset export — `{args.variant}`

Self-contained: epochs have the channel strategy and epoch rejection already
applied, so `mne.read_epochs()` gives training-ready data with no extra code.

```
<PID>/eeg/sub-<PID>_<task>_epo.fif   finalized epochs
      sub-<PID>_channel_mask.npy     int8[n_ch], 1 = real signal, 0 = masked
      sub-<PID>_channels.json        channel order, detected bads, strategy
      sub-<PID>_alignment.csv        one row per trial; paths are bundle-relative
{"      video/<task>/*.avi + *_frames.csv" if args.video else "(video not included)"}
labels.csv      one row per subject
build_log.csv   how each subject was built
```

**Read the channel mask.** Real channels per subject range from 5 to 16; a model
that ignores the mask treats masked channels as real zeros.

**Never assume a nominal fps** for video: the webcam runs sub-nominal and the
stream is dejittered. Use `t_rel_stim_s` in `*_frames.csv`.

{"Labels are de-identified: date of birth, test dates and internal ids removed, age binned to " + str(AGE_BIN) + "-year ranges." if args.deidentify else "**Labels include date of birth, test dates, race and sex.** Treat as identifiable."}
""")

    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"  {n_ep} epoch files, {n_clip} clips, {total/1e6:.0f} MB -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
