#!/usr/bin/env python3
"""Sync the study's upstream sources, then score any new recordings.

One command for the recurring "is there new data?" chore. Stages run in order
because each depends on the one before it (numbering matches the table in
``docs/data_sync.md``):

1. **Box -> repo workbook.** The coordinator maintains the clinical workbook on
   Box; ``processing/02_PCData.xlsx`` is the repo's copy and goes stale. Pull it
   first so everything downstream judges against current data. Add
   ``--commit-workbook`` to also git-commit it (that one file, nothing else).
2. **Workbook -> Drive.** Mirror the same file into the Drive ``PC/`` folder so
   recordings and labels live together (the coordinator only ever sees Drive).
3. **Drive -> local recordings.** Diff ``PC/{Control,Experimental}`` against the
   local ``data/`` tree and download whatever is missing.
4. **Demographics gate.** A recording is only scored once its demographics exist
   in the workbook, since a subject with no clinical row cannot enter a dataset
   anyway. ``--skip-demographics-check`` scores it regardless, for when you want
   the QC numbers before the coordinator has caught up on data entry.
5. **QC.** ``run_quality.py`` scores every recording.
6. **Publish the QC workbook** to Drive ``PC/quality_results.xlsx`` -- a single
   always-current file, deliberately not dated.
7. **Refresh built variants' ``labels.csv``.** A workbook pull changes the
   LABELS of an already-built dataset and nothing else, so rewrite just that file
   per variant rather than re-running finalize over ~360 MB of unchanged epochs.
   Runs whenever the workbook moved, independently of whether QC ran.

Step 8 -- actually building a dataset from new recordings (``pair_video`` +
``finalize_dataset``) -- stays MANUAL: it needs a cohort decision first, and
pairing is slow and irreversible.

Stages 1-2 always run. ``--clinical-only`` runs 1, 2 and 7 -- the fast path for
"the coordinator entered new demographics, update the datasets" with no download
and no QC.

Both remotes are pre-configured rclone remotes (``box:`` / ``gdrive:``). Neither
source folder is in the account's own root, so every path MUST be rooted by
folder id -- see ``BOX_FOLDER_ID`` / ``DRIVE_ROOT_ID`` below.

**``docs/data_sync.md`` is the reference for all of this** -- the by-hand
commands, the non-EEG sibling folders, the phone-only subject ids that look like
missing controls, and the workbook's shifting column layout.

    python -m scripts.sync_study_data --dry-run      # report only, change nothing
    python -m scripts.sync_study_data                # full sync + QC + labels
    python -m scripts.sync_study_data --clinical-only        # labels only
    python -m scripts.sync_study_data --clinical-only --variant usable__zero_mask
    python -m scripts.sync_study_data --skip-demographics-check
    python -m scripts.sync_study_data --no-qc        # sync only
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# Box: 'AudioSight Study/01_Participant Data'. Addressed by id, not path, so a
# folder rename upstream does not break the pull.
BOX_FOLDER_ID = "324186906035"
BOX_WORKBOOK = "02_PC Data.xlsx"          # NB: space in the Box filename

# Drive: the coordinator's upload root (owned by lizr89721@gmail.com).
DRIVE_ROOT_ID = "1Eh9SlATsEUzrGEDgNVfWPLeOWE2Cy90l"
DRIVE_PC = "PC"                            # PC/ = EEG; Phone/, DNQ/ are not

# Drive subfolder -> local data subdir. The names deliberately differ.
COHORTS = {"Control": "control", "Experimental": "experimental"}

LOCAL_WORKBOOK = REPO / "02_PCData.xlsx"   # no space locally

# macOS uploads litter every folder with these; they break folder discovery.
JUNK = ["._*", ".DS_Store", ".*/._*"]

# A subject needs these before QC is worth running (see --skip-demographics-check).
REQUIRED_CLINICAL = ("age", "sex")


def sh(args, check=True, quiet=False):
    """Run a command, returning stdout. rclone's shared-client_id notice goes to
    stderr on every call, so stderr is captured and only shown on failure."""
    if not quiet:
        print(f"  $ {' '.join(args)}")
    r = subprocess.run(args, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(args)}\n"
                           f"{r.stderr.strip()}")
    return r.stdout


def rclone(*args, root_flag=None, root_id=None, **kw):
    cmd = ["rclone", *args]
    if root_flag:
        cmd += [root_flag, root_id]
    return sh(cmd, **kw)


def drive(*args, **kw):
    return rclone(*args, root_flag="--drive-root-folder-id",
                  root_id=DRIVE_ROOT_ID, **kw)


def box(*args, **kw):
    return rclone(*args, root_flag="--box-root-folder-id",
                  root_id=BOX_FOLDER_ID, **kw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_STEP = [0]


def header(title):
    """Numbered stage banner. Auto-increments so skipped stages don't leave
    gaps and the summary can't print out of order (it used to)."""
    _STEP[0] += 1
    print(f"\n{'=' * 72}\n{_STEP[0]}. {title}\n{'=' * 72}")


# --------------------------------------------------------------------------- #
# 1. Box -> local workbook
# --------------------------------------------------------------------------- #
def pull_workbook(dry_run, stage_dir):
    """Returns (changed, note, path_to_current_workbook).

    Compares by content hash, not mtime: rclone rewrites mtime on every copy, so
    a hash is the only honest "did it change". The third return value is the
    workbook the LATER STAGES must read -- under --dry-run the local file is
    deliberately left untouched, so the demographics gate has to judge against
    the staged Box copy or it reports stale gaps that upstream already filled.
    """
    header(f"Box -> {LOCAL_WORKBOOK.name}")
    listing = box("lsl", f"box:{BOX_WORKBOOK}", quiet=True).strip()
    if not listing:
        raise RuntimeError(f"{BOX_WORKBOOK!r} not found in Box folder "
                           f"{BOX_FOLDER_ID} -- was it renamed?")
    print(f"  Box:   {listing}")
    before = sha(LOCAL_WORKBOOK) if LOCAL_WORKBOOK.exists() else None
    print(f"  local: {'absent' if before is None else LOCAL_WORKBOOK.stat().st_size} bytes")

    staged = Path(stage_dir) / "workbook.xlsx"
    box("copyto", f"box:{BOX_WORKBOOK}", str(staged))
    if sha(staged) == before:
        print("  -> unchanged")
        return False, "unchanged", LOCAL_WORKBOOK
    if dry_run:
        print("  -> WOULD UPDATE (dry-run; later stages read the staged copy)")
        return True, "would update", staged
    shutil.copy2(staged, LOCAL_WORKBOOK)
    print(f"  -> UPDATED ({LOCAL_WORKBOOK.stat().st_size} bytes)")
    return True, "updated", LOCAL_WORKBOOK


# --------------------------------------------------------------------------- #
# 2. workbook -> Drive PC/
# --------------------------------------------------------------------------- #
def push_workbook(dry_run, workbook):
    header(f"{Path(workbook).name} -> Drive {DRIVE_PC}/{BOX_WORKBOOK}")
    dest = f"gdrive:{DRIVE_PC}/{BOX_WORKBOOK}"
    if dry_run:
        print(f"  -> WOULD UPLOAD to {dest} (dry-run)")
        return
    # copyto compares size+mtime and skips a genuinely identical file.
    drive("copyto", str(workbook), dest)
    print(f"  -> uploaded: {drive('lsl', f'gdrive:{DRIVE_PC}/{BOX_WORKBOOK}', quiet=True).strip()}")


# --------------------------------------------------------------------------- #
# git: commit the refreshed workbook
# --------------------------------------------------------------------------- #
def commit_workbook(dry_run):
    """Commit ONLY the workbook, so a sync never sweeps up unrelated work in
    progress. Opt-in (``--commit-workbook``) because committing is not this
    script's job by default."""
    header(f"git commit {LOCAL_WORKBOOK.name}")
    rel = LOCAL_WORKBOOK.relative_to(REPO.parent)
    status = sh(["git", "-C", str(REPO.parent), "status", "--porcelain", "--",
                 str(rel)], quiet=True).strip()
    if not status:
        print("  -> nothing to commit (workbook unchanged in git)")
        return
    branch = sh(["git", "-C", str(REPO.parent), "rev-parse",
                 "--abbrev-ref", "HEAD"], quiet=True).strip()
    print(f"  branch: {branch}   status: {status}")
    if dry_run:
        print("  -> WOULD COMMIT (dry-run)")
        return
    sh(["git", "-C", str(REPO.parent), "commit", "-m",
        "processing: refresh the clinical workbook from Box", "--", str(rel)])
    print("  -> committed")


# --------------------------------------------------------------------------- #
# Drive PC/ -> local data/
# --------------------------------------------------------------------------- #
def _has_xdf(cohort, pid):
    """A folder without an .xdf is not an EEG session (audiometry-only, or a
    phone-era upload) -- do not pull it into the EEG tree."""
    out = drive("lsf", "--recursive", "--files-only", "--include", "*.xdf",
                f"gdrive:{DRIVE_PC}/{cohort}/{pid}", quiet=True)
    return bool(out.strip())


def sync_recordings(data_root, dry_run):
    header(f"Drive {DRIVE_PC}/ -> {data_root}")
    new = {}
    for cohort, local_name in COHORTS.items():
        local_dir = Path(data_root) / local_name
        remote = sorted(x for x in drive(
            "lsf", "--dirs-only", f"gdrive:{DRIVE_PC}/{cohort}", quiet=True
        ).split() if x.strip("/"))
        remote = [x.rstrip("/") for x in remote]
        local = sorted(p.name for p in local_dir.iterdir() if p.is_dir()) \
            if local_dir.exists() else []
        missing = [p for p in remote if p not in local]
        extra = [p for p in local if p not in remote]
        print(f"  {cohort:12s} drive={len(remote):3d}  local={len(local):3d}  "
              f"missing={missing or '-'}  local-only={extra or '-'}")
        for pid in missing:
            if not _has_xdf(cohort, pid):
                print(f"    {pid}: SKIPPED — no .xdf (not an EEG session)")
                continue
            new[pid] = (cohort, local_dir / pid)
    if not new:
        print("  -> nothing to download")
        return {}
    for pid, (cohort, dest) in new.items():
        size = drive("size", f"gdrive:{DRIVE_PC}/{cohort}/{pid}", quiet=True)
        print(f"  {pid}: {size.strip().splitlines()[-1].strip()}")
        if dry_run:
            print(f"    -> WOULD DOWNLOAD to {dest} (dry-run)")
            continue
        args = ["copy", f"gdrive:{DRIVE_PC}/{cohort}/{pid}", str(dest)]
        for j in JUNK:
            args += ["--exclude", j]
        drive(*args, "-P")
        print(f"    -> {dest}")
    return new


# --------------------------------------------------------------------------- #
# 4. demographics gate
# --------------------------------------------------------------------------- #
def check_demographics(pids, workbook):
    """Returns {pid: [missing fields]} for subjects lacking clinical data."""
    header(f"Demographics gate (vs {workbook})")
    from synapse_qc.clinical import load_clinical_rows
    rows = {r["subject_id"]: r
            for r in load_clinical_rows(str(workbook), sorted(pids))}
    gaps = {}
    for pid in sorted(pids):
        r = rows.get(pid, {})
        missing = [f for f in REQUIRED_CLINICAL if not str(r.get(f, "")).strip()]
        n = sum(1 for k, v in r.items()
                if k not in ("subject_id", "group", "devices_present")
                and str(v).strip())
        flag = "OK " if not missing else "GAP"
        print(f"  {flag} {pid}: {n:3d} clinical fields"
              + (f" | MISSING {missing}" if missing else ""))
        if missing:
            gaps[pid] = missing
    return gaps


# --------------------------------------------------------------------------- #
# 5. QC + upload
# --------------------------------------------------------------------------- #
def run_qc(date, data_root, dry_run):
    header("Quality check")
    cmd = [sys.executable, "run_quality.py"]
    if date:
        cmd += ["--date", date]
    if data_root:
        cmd += ["--data-root", str(data_root)]
    if dry_run:
        print(f"  -> WOULD RUN: {' '.join(cmd)} (dry-run)")
        return None
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=REPO, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"run_quality.py failed ({r.returncode})")
    from synapse_qc import paths as qpaths
    xlsx = Path(qpaths.output_paths()["qc"]) / "quality_results.xlsx"
    if not xlsx.exists():
        raise RuntimeError(f"expected QC workbook not found: {xlsx}")
    return xlsx


def push_qc(xlsx, dry_run):
    header(f"Quality workbook -> Drive {DRIVE_PC}/")
    dest = f"gdrive:{DRIVE_PC}/quality_results.xlsx"
    if dry_run or xlsx is None:
        print(f"  -> WOULD UPLOAD {xlsx} to {dest} (dry-run)")
        return
    drive("copyto", str(xlsx), dest)
    print(f"  -> uploaded: {drive('lsl', dest, quiet=True).strip()}")


# --------------------------------------------------------------------------- #
# Refresh labels.csv in the built dataset variants
# --------------------------------------------------------------------------- #
def refresh_clinical(workbook, dry_run, only_variant=None):
    """Re-derive each built variant's ``labels.csv`` from the current workbook.

    A workbook pull changes the LABELS of an already-built dataset, and nothing
    else -- the epochs and video are untouched -- so this rewrites just that one
    file per variant instead of re-running finalize (which would rebuild ~360 MB
    of .fif per variant for no reason). Mirrors ``finalize_dataset._write_clinical``:
    same column order (first-seen across rows) and the same manifest bookkeeping.
    """
    header("Refresh labels.csv in built variants")
    from omegaconf import OmegaConf
    from synapse_qc import paths as qpaths
    from synapse_qc.clinical import load_clinical_rows

    # Scan every dataset PRODUCT (eeg_only, multimodal, ...), not just the one
    # finalize happens to default to -- a workbook pull relabels all of them.
    base = qpaths.output_paths()["base"]
    fcfg = OmegaConf.load(REPO / "conf" / "finalize.yaml")
    final_dir = Path(base) / Path(fcfg.paths.dataset_dir).parent
    if not final_dir.exists():
        print(f"  -> no built variants at {final_dir}")
        return []
    variants = sorted(d for d in final_dir.glob("*/*")
                      if d.is_dir() and (d / "build_log.csv").exists())
    if only_variant:
        variants = [d for d in variants
                    if only_variant in (d.name, f"{d.parent.name}/{d.name}")]
        if not variants:
            raise RuntimeError(f"variant {only_variant!r} not found in {final_dir}")
    if not variants:
        print(f"  -> no finalized variants under {final_dir}")
        return []

    import csv as _csv
    import json
    import pandas as pd

    touched = []
    for v in variants:
        st = pd.read_csv(v / "build_log.csv")
        subjects = st.loc[st.status == "ok", "subject_id"].tolist()
        measures = None
        mf = v / "manifest.json"
        man = json.loads(mf.read_text()) if mf.exists() else {}
        if isinstance(man.get("clinical"), dict):
            measures = man["clinical"].get("measures")
        rows = load_clinical_rows(str(workbook), subjects, measures)
        cols = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)
        n_quest = sum(1 for r in rows if any(
            str(r.get(m, "")).strip() for m in (measures or [])))
        n_any = sum(1 for r in rows if any(
            str(val).strip() for k, val in r.items()
            if k not in ("subject_id", "group", "devices_present")))
        print(f"  {v.parent.name}/{v.name}: {len(rows)} subjects, {len(cols)} cols, "
              f"{n_any} with clinical data"
              + (f", {n_quest} with questionnaires" if measures else ""))
        if dry_run:
            print("    -> WOULD REWRITE labels.csv (dry-run)")
            continue
        with open(v / "labels.csv", "w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        if man:
            man.setdefault("clinical", {})
            man["clinical"].update({
                "csv": "labels.csv",
                "workbook": str(workbook),
                "subjects_with_entries": n_any,
                "subjects_with_questionnaires": n_quest,
                "refreshed": datetime.date.today().isoformat(),
            })
            mf.write_text(json.dumps(man, indent=2))
        print("    -> rewrote labels.csv" + (" + manifest" if man else ""))
        touched.append(f"{v.parent.name}/{v.name}")
    return touched


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="report every stage's decision, write nothing")
    ap.add_argument("--skip-demographics-check", action="store_true",
                    help="run QC even if new subjects have no clinical data yet")
    ap.add_argument("--no-qc", action="store_true",
                    help="stop after syncing; do not score or upload")
    ap.add_argument("--force-qc", action="store_true",
                    help="run QC even when no new recordings were downloaded")
    ap.add_argument("--data-root", default=None,
                    help="raw recordings dir (default: $SYNAPSE_DATA_ROOT / "
                         "$SYNAPSE_DATA_BASE/raw / <repo>/raw)")
    ap.add_argument("--date", default="", help="run-date label for the QC Legend")
    ap.add_argument("--clinical-only", action="store_true",
                    help="pull the workbook and refresh each built variant's "
                         "labels.csv, nothing else (no download, no QC)")
    ap.add_argument("--variant", default=None,
                    help="restrict the labels.csv refresh to one variant dir")
    ap.add_argument("--no-clinical-refresh", action="store_true",
                    help="leave built variants' labels.csv alone")
    ap.add_argument("--commit-workbook", action="store_true",
                    help="git-commit the refreshed workbook (that file only)")
    args = ap.parse_args()

    data_root = args.data_root
    if data_root is None:
        from synapse_qc import inventory
        data_root = inventory._default_data_root()
    print(f"data root: {data_root}")
    if args.dry_run:
        print("DRY RUN — nothing will be written, uploaded or downloaded.")

    stage = tempfile.mkdtemp(prefix="synapse_sync_")
    try:
        # Stages 1-2 always run: the workbook is the cheapest thing to keep
        # current and everything downstream judges against it.
        wb_changed, wb_note, workbook = pull_workbook(args.dry_run, stage)
        push_workbook(args.dry_run, workbook)
        if args.commit_workbook:
            commit_workbook(args.dry_run)

        if args.clinical_only:
            refreshed = refresh_clinical(workbook, args.dry_run, args.variant)
            header("Summary")
            print(f"  workbook:        {wb_note}")
            print(f"  labels.csv:    {refreshed or 'none'}")
            print("  recordings/QC:   skipped (--clinical-only)")
            print("\nDone.")
            return 0

        new = sync_recordings(data_root, args.dry_run)
        gaps = check_demographics(new, workbook) if new else {}

        header("Summary")
        print(f"  workbook:        {wb_note}")
        print(f"  new recordings:  {sorted(new) or 'none'}")
        print(f"  clinical gaps:   {gaps or 'none'}")

        rc, do_qc = 0, True
        if args.no_qc:
            print("  QC:              skipped (--no-qc)")
            do_qc = False
        elif not new and not args.force_qc:
            print("  QC:              skipped (no new recordings; "
                  "--force-qc to run)")
            do_qc = False
        elif gaps and not args.skip_demographics_check:
            print(f"  QC:              BLOCKED — {sorted(gaps)} lack "
                  f"{REQUIRED_CLINICAL} in the workbook.\n"
                  "                   The coordinator has not entered them yet. "
                  "Re-run later, or pass\n"
                  "                   --skip-demographics-check to score anyway.")
            do_qc, rc = False, 1

        if do_qc:
            xlsx = run_qc(args.date, args.data_root, args.dry_run)
            push_qc(xlsx, args.dry_run)

        # A workbook pull changes the LABELS of already-built datasets, so
        # refresh them even when QC was skipped or blocked -- the two are
        # independent. Only worth doing if the workbook actually moved.
        if wb_changed and not args.no_clinical_refresh:
            refresh_clinical(workbook, args.dry_run, args.variant)
        elif not wb_changed:
            print("\n(labels.csv refresh skipped — workbook unchanged)")
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    print("\nDone." if rc == 0 else "\nStopped.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
