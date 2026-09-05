#!/usr/bin/env python3
"""One-shot migration: product-shaped `outputs/` -> step-shaped `processed/`.

The old tree was organised by product (`qc`, `epochs`, `multimodal`), which hid
the fact that each stage feeds the next and hardcoded "EEG + video" into the
directory names. The new tree is organised by STEP, numbered, with gaps left for
the stages that do not exist yet:

    raw/                        (was data/)
      control/                  (was 01_Control/)
      experimental/             (was 02_Experimental/)
    processed/                  (was outputs/)
      qc/                     (was outputs/qc/)
      eeg/                    RESERVED -- filtered/epoched EEG, once pair_video is split
      video/                  RESERVED -- clips + pupillometry signal
      paired/<variant>/       (was outputs/multimodal/paired_<date>/)
      dataset/
        multimodal/<variant>/   (was outputs/multimodal/final/<variant>/)
        eeg_only/<variant>/     (was outputs/epochs/<variant>/)
      logs/

`eeg/` and `video/` are created empty on purpose: when `pair_video` is later
split into "process EEG" + "process video" + "align", those stages land there and
**nothing renumbers**. `paired/` then sheds its per-subject eeg/ and video/
subdirs and keeps only the alignment index.

THE PART THAT IS NOT A RENAME: every `*_alignment.csv` stores `eeg_file`,
`video_clip` and `video_frames_csv` as paths relative to the outputs base. Moving
directories invalidates all of them, so this script rewrites those columns. That
is the whole reason this is a script and not four `mv` commands.

    python -m scripts.migrate_layout --base /data1/anarghya/synapse-data --dry-run
    python -m scripts.migrate_layout --base /data1/anarghya/synapse-data
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

# old prefix -> new prefix, applied to the path columns of every alignment CSV.
# Longest first: 'multimodal/paired_20260828' must win over 'multimodal/paired'.
PATH_REWRITES = [
    ("outputs/multimodal/paired_20260828", "processed/paired/usable_20260904"),
    ("outputs/multimodal/final",           "processed/dataset/multimodal"),
    ("outputs/epochs",                     "processed/dataset/eeg_only"),
    ("outputs/qc",                         "processed/qc"),
    ("data/01_Control",                    "raw/control"),
    ("data/02_Experimental",               "raw/experimental"),
]

PATH_COLUMNS = ("eeg_file", "video_clip", "video_frames_csv")


def moves(base: Path):
    """(src, dst) pairs, in dependency order. Only ones whose src exists run."""
    return [
        (base / "data",                                base / "raw"),
        (base / "raw" / "01_Control",                  base / "raw" / "control"),
        (base / "raw" / "02_Experimental",             base / "raw" / "experimental"),
        (base / "outputs" / "qc",                      base / "processed" / "qc"),
        (base / "outputs" / "multimodal" / "paired_20260828",
         base / "processed" / "paired" / "usable_20260904"),
        (base / "outputs" / "epochs",
         base / "processed" / "dataset" / "eeg_only"),
        (base / "outputs" / "multimodal" / "final",
         base / "processed" / "dataset" / "multimodal"),
        (base / "outputs" / "logs",                    base / "processed" / "logs"),
    ]


def _scan_roots(base: Path):
    """Where the files to rewrite currently live. After a real move they are
    under processed/; during --dry-run they are still under outputs/, and the
    dry run is worthless if it reports 0 because it looked in the wrong place."""
    return [d for d in (base / "processed", base / "outputs") if d.exists()]


def rewrite_alignment(base: Path, dry: bool):
    """Repoint every alignment CSV's path columns at the new tree."""
    csvs = sorted(f for root in _scan_roots(base)
                  for f in root.rglob("*_alignment.csv"))
    n_files = n_cells = 0
    for f in csvs:
        rows = list(csv.DictReader(f.open()))
        if not rows:
            continue
        cols = [c for c in PATH_COLUMNS if c in rows[0]]
        hits = 0
        for r in rows:
            for c in cols:
                v = r.get(c) or ""
                for old, new in PATH_REWRITES:
                    if v.startswith(old):
                        r[c] = new + v[len(old):]
                        hits += 1
                        break
        if not hits:
            continue
        n_files += 1
        n_cells += hits
        if not dry:
            with f.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    print(f"  alignment CSVs rewritten: {n_files} files, {n_cells} paths"
          + (" (dry-run)" if dry else ""))
    return n_files


def rewrite_manifests(base: Path, dry: bool):
    """Manifests record the tree they were built from; keep them honest."""
    n = 0
    for f in sorted(f for root in _scan_roots(base)
                    for f in root.rglob("manifest.json")):
        raw = f.read_text()
        out = raw
        for old, new in PATH_REWRITES:
            out = out.replace(old, new)
        if out == raw:
            continue
        n += 1
        if not dry:
            f.write_text(out)
    print(f"  manifests rewritten: {n}" + (" (dry-run)" if dry else ""))
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--drop-stale-paired", action="store_true",
                    help="delete outputs/multimodal/paired (the superseded run)")
    args = ap.parse_args()
    base, dry = args.base, args.dry_run
    if dry:
        print("DRY RUN — nothing is moved or written.\n")

    print("1. Move directories")
    for src, dst in moves(base):
        if not src.exists():
            print(f"  skip (absent): {src.relative_to(base)}")
            continue
        if dst.exists():
            print(f"  SKIP (dst exists): {dst.relative_to(base)}")
            continue
        print(f"  {src.relative_to(base)}  ->  {dst.relative_to(base)}")
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

    print("\n2. Reserve the future stages")
    for d in ("processed/eeg", "processed/video"):
        print(f"  {d}/  (empty, reserved)")
        if not dry:
            p = base / d
            p.mkdir(parents=True, exist_ok=True)
            (p / ".gitkeep").touch()

    print("\n3. Repoint stored paths")
    rewrite_alignment(base, dry)
    rewrite_manifests(base, dry)

    if args.drop_stale_paired:
        stale = base / "outputs" / "multimodal" / "paired"
        print("\n4. Drop the superseded paired tree")
        if stale.exists():
            sz = sum(f.stat().st_size for f in stale.rglob("*") if f.is_file())
            print(f"  {stale.relative_to(base)}  ({sz/1e9:.1f} GB)")
            if not dry:
                shutil.rmtree(stale)
        else:
            print("  already gone")

    # Variants built from the deleted tree keep valid EEG (.fif are
    # self-contained) but their video_clip paths now dangle. Say so in the
    # manifest rather than leaving a silent trap.
    if args.drop_stale_paired:
        print("\n5. Flag variants orphaned by that deletion")
        vroot = base / "processed" / "dataset" / "multimodal"
        for v in sorted(d for d in vroot.glob("*") if d.is_dir()) if vroot.exists() else []:
            hit = any("outputs/multimodal/paired" in f.read_text()
                      for f in v.rglob("*_alignment.csv"))
            if not hit:
                continue
            print(f"  {v.name}: video refs dangle (EEG epochs still valid)")
            mf = v / "manifest.json"
            if mf.exists() and not dry:
                m = json.loads(mf.read_text())
                m["video_refs"] = ("DANGLING -- built from outputs/multimodal/"
                                   "paired, which was deleted as superseded. "
                                   "The .fif epochs and labels.csv are still "
                                   "valid; only video_clip paths are dead. "
                                   "Rebuild from paired/ if video is needed.")
                mf.write_text(json.dumps(m, indent=2))

    left = base / "outputs"
    if left.exists() and not dry:
        rest = [p.name for p in left.rglob("*") if p.is_file()]
        if not rest:
            shutil.rmtree(left)
            print("\n  removed the now-empty outputs/")
        else:
            print(f"\n  NOTE: outputs/ still holds {len(rest)} file(s): "
                  f"{rest[:5]}")
    print("\nDone." if not dry else "\nDry run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
