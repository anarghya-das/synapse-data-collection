"""Finalize the detect-and-defer paired dataset into a training-ready dataset.

``pipelines/pair_video.py`` does the slow, one-time work: temporal EEG<->video
alignment, filtering, epoching, and video encoding, saving EVERY boundary-valid
trial with all 16 channels intact and bad channels *detected but untouched*
(recorded in each ``_epo.fif``'s ``info['bads']`` + a ``*_qc.json`` sidecar).

This step is the fast, swappable half. For each subject it:
  * applies the channel strategy (``interpolate`` | ``zero_mask`` | ``drop`` |
    ``keep_all``) from the ``preprocessing`` group;
  * emits a per-channel validity mask (1 = real signal, 0 = interpolated/masked/
    dropped) so a model can down-weight non-measured channels;
  * applies PTP z-score epoch rejection over the *good* channels only (so a noisy
    bad channel can't corrupt the rejection), excluding a task when too few epochs
    survive or too many are rejected;
  * filters the paired ``*_alignment.csv`` to the surviving epochs, re-indexing
    ``eeg_epoch_index`` into the finalized ``_epo.fif`` and pointing ``video_clip``
    at the existing clips under ``outputs/multimodal/paired`` (video is never
    re-encoded);
  * joins the clinical workbook into ``clinical.csv`` (one row per finalized
    subject: questionnaire scores + demographics) so the dataset ships with its
    labels.

Because channel handling is decoupled from the expensive pairing, you can build
``interpolate`` / ``zero_mask`` / ``drop`` variants side by side from one pair run:

    python -m pipelines.finalize_dataset                          # published: interpolate + z=3
    python -m pipelines.finalize_dataset preprocessing=zero_mask
    python -m pipelines.finalize_dataset preprocessing=drop
    python -m pipelines.finalize_dataset preprocessing.epoch_rejection.enabled=false
"""
import os
import sys
import csv
import json
import warnings
from datetime import datetime

import numpy as np
import hydra
from omegaconf import OmegaConf, DictConfig

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from synapse_qc import paths as qpaths  # noqa: E402

warnings.filterwarnings("ignore")

_ALIGN_COLS_IN = [
    "task", "trial", "eeg_epoch_index", "condition", "label", "t_stim_lsl",
    "tmin", "tmax", "video_clip", "video_frames_csv", "n_frames_written",
    "n_frames_expected", "partial_window",
]


def _load_qc(paired_subj, subject_id):
    """Read the per-subject QC sidecar written by pair_video. Returns
    ``(bads, quality_score)`` (bads = [] if no sidecar)."""
    path = os.path.join(paired_subj, f"sub-{subject_id}_qc.json")
    if not os.path.exists(path):
        return [], None
    with open(path) as fh:
        qc = json.load(fh)
    return list(qc.get("bads_combined", [])), qc.get("quality_score")


def _load_alignment(paired_subj, subject_id):
    """Read the paired alignment rows (empty list if the subject had no video)."""
    path = os.path.join(paired_subj, f"sub-{subject_id}_alignment.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def _apply_channel_strategy(epochs, bads, strategy, montage_file):
    """Apply ``strategy`` to a 16-channel ``Epochs`` and return
    ``(epochs, mask, ch_names)`` where ``mask[i] == 1`` means channel ``i`` carries
    real measured signal (0 = interpolated / masked / dropped).

    * interpolate — spline-interpolate bads from neighbours (fixed 16 ch); mask
      marks the interpolated channels 0.
    * zero_mask   — zero the bad channels (fixed 16 ch); mask marks them 0.
    * drop        — remove bad channels (variable ch count); mask is all-ones.
    * keep_all    — leave the raw bad channels untouched (fixed 16 ch); mask marks
      them 0. This is the honest "give the model the data + a mask" option.
    """
    import mne

    orig_names = list(epochs.ch_names)
    mask = np.array([0 if ch in bads else 1 for ch in orig_names], dtype=np.int8)

    if not bads or strategy == "keep_all":
        return epochs, mask, orig_names

    if strategy == "interpolate":
        # Reloaded epochs keep their dig locations, but set the montage explicitly
        # so interpolation is robust regardless of how the .fif was written.
        md = np.load(montage_file)
        montage = mne.channels.make_dig_montage(
            ch_pos=dict(zip(md["labels"], md["points"])),
            nasion=md["nasion"], lpa=md["lpa"], rpa=md["rpa"], coord_frame="head")
        epochs.set_montage(montage)
        epochs.info["bads"] = list(bads)
        epochs.interpolate_bads(reset_bads=True, verbose=False)
        return epochs, mask, orig_names   # mask still flags the interpolated ch

    if strategy == "zero_mask":
        bad_idx = [orig_names.index(ch) for ch in bads]
        epochs._data[:, bad_idx, :] = 0.0
        epochs.info["bads"] = []
        return epochs, mask, orig_names

    if strategy == "drop":
        epochs.drop_channels(bads)
        kept = list(epochs.ch_names)
        return epochs, np.ones(len(kept), dtype=np.int8), kept

    raise ValueError(f"unknown channel_strategy: {strategy}")


def _reject_epochs(epochs, mask, rej):
    """PTP z-score rejection over the GOOD channels only. Returns
    ``(kept_positions, n_before, n_after, excluded, reason)`` where kept_positions
    are indices into the *input* epochs array."""
    n_before = len(epochs)
    z = rej.get("z_threshold", 3)
    min_epochs = rej.get("min_epochs", 5)
    max_reject_pct = rej.get("max_reject_pct", 50)
    enabled = rej.get("enabled", True)

    kept = list(range(n_before))
    if enabled and n_before >= 3:
        data = epochs.get_data(copy=True)                   # (n_ep, n_ch, n_t)
        good = np.where(mask == 1)[0]
        if len(good) == 0:                                   # degenerate: all bad
            good = np.arange(data.shape[1])
        ptps = np.ptp(data[:, good, :], axis=2).max(axis=1)  # max PTP / good ch
        thresh = ptps.mean() + z * ptps.std()
        bad = np.where(ptps > thresh)[0]
        if len(bad):
            epochs.drop(bad, reason="PTP_ZSCORE", verbose=False)
            drop = set(int(b) for b in bad)
            kept = [i for i in range(n_before) if i not in drop]

    n_after = len(epochs)
    pct = ((n_before - n_after) / n_before * 100) if n_before else 0.0
    excluded, reason = False, ""
    if enabled and n_before >= 3:
        if n_after < min_epochs:
            excluded, reason = True, f"<{min_epochs} epochs survive"
        elif pct > max_reject_pct:
            excluded, reason = True, f">{max_reject_pct}% rejected"
    return kept, n_before, n_after, excluded, reason


def _finalize_subject(pid, paired_subj, out_subj, strategy, rej, montage_file, base=REPO):
    """Finalize one subject; returns a summary row (or None if it has no epochs)."""
    import mne

    eeg_in = os.path.join(paired_subj, "eeg")
    if not os.path.isdir(eeg_in):
        return None

    bads, quality_score = _load_qc(paired_subj, pid)
    align_rows = _load_alignment(paired_subj, pid)
    align_by_task = {}
    for r in align_rows:
        align_by_task.setdefault(r["task"], []).append(r)

    eeg_out = os.path.join(out_subj, "eeg")
    os.makedirs(eeg_out, exist_ok=True)

    task_counts, excluded_tasks, final_align = {}, [], []
    final_ch_names, final_mask = None, None

    for fname in sorted(os.listdir(eeg_in)):
        if not fname.endswith("_epo.fif"):
            continue
        task = fname.split(f"sub-{pid}_")[-1].replace("_epo.fif", "")
        epochs = mne.read_epochs(os.path.join(eeg_in, fname), preload=True, verbose=False)

        epochs, mask, ch_names = _apply_channel_strategy(
            epochs, bads, strategy, montage_file)
        final_ch_names, final_mask = ch_names, mask   # same for every task

        kept, n_before, n_after, excluded, reason = _reject_epochs(epochs, mask, rej)

        if excluded:
            print(f"  [{pid}] {task}: {n_before}->{n_after} — EXCLUDED ({reason})")
            excluded_tasks.append(task)
            task_counts[task] = 0
            continue

        epochs.save(os.path.join(eeg_out, fname), overwrite=True, verbose=False)
        task_counts[task] = n_after
        print(f"  [{pid}] {task}: {n_before}->{n_after} epochs "
              f"(strategy={strategy}, {int(mask.sum())}/{len(mask)} real ch)")

        # Re-index the paired alignment rows for this task onto the finalized
        # epochs: keep rows whose old epoch index survived, renumber to new index.
        new_index = {old: k for k, old in enumerate(kept)}
        for r in align_by_task.get(task, []):
            old = int(r["eeg_epoch_index"])
            if old not in new_index:
                continue
            video_abs = os.path.join(paired_subj, r["video_clip"])
            frames_abs = os.path.join(paired_subj, r["video_frames_csv"])
            row = dict(r)
            row["eeg_epoch_index"] = new_index[old]
            # Rewrite all path columns to a single, consistent base-relative form
            # (the paired frames path was relative to the paired subject dir).
            row["eeg_file"] = os.path.relpath(os.path.join(eeg_out, fname), base)
            row["video_clip"] = os.path.relpath(video_abs, base)
            row["video_frames_csv"] = os.path.relpath(frames_abs, base)
            final_align.append(row)

    if final_ch_names is None:
        return None   # no epoch files at all

    # Per-subject validity mask + channel order (source of truth for the model).
    np.save(os.path.join(out_subj, f"sub-{pid}_channel_mask.npy"), final_mask)
    with open(os.path.join(out_subj, f"sub-{pid}_channels.json"), "w") as fh:
        json.dump({"ch_names": final_ch_names,
                   "mask": [int(m) for m in final_mask],
                   "bads_detected": sorted(bads),
                   "strategy": strategy,
                   "quality_score": quality_score}, fh, indent=2)

    # Filtered alignment: one row per surviving paired (EEG epoch, video clip).
    cols = ["task", "trial", "eeg_epoch_index", "eeg_file", "condition", "label",
            "t_stim_lsl", "tmin", "tmax", "video_clip", "video_frames_csv",
            "n_frames_written", "partial_window"]
    if final_align:
        with open(os.path.join(out_subj, f"sub-{pid}_alignment.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(final_align)

    return {
        "subject_id": pid,
        "quality_score": quality_score,
        "n_bad_detected": len(bads),
        "n_real_channels": int(final_mask.sum()),
        "n_channels": len(final_mask),
        "task_counts": task_counts,
        "excluded_tasks": excluded_tasks,
        "paired_trials": len(final_align),
    }


def _load_paired_manifest(paired_root):
    """Provenance of the paired input (cohort, build date); {} if absent."""
    path = os.path.join(paired_root, "manifest.json")
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return json.load(fh)


def _write_clinical(out_root, subjects, cfg):
    """Join per-subject clinical scores + demographics from the clinical workbook
    into ``clinical.csv`` (one row per finalized subject, keyed by subject_id) so
    the multimodal dataset ships with its labels. Uses the same published loaders
    ``build_dataset`` uses; skipped with a warning if the analysis repo or the
    workbook is unavailable (finalize itself still succeeds)."""
    try:
        synapse_repo = cfg.paths.synapse_repo
        if synapse_repo not in sys.path:
            sys.path.insert(0, synapse_repo)
        from publication_analysis import preprocess as pp
    except Exception as e:  # noqa: BLE001
        print(f"[clinical] SKIPPED — cannot import published loaders "
              f"from {cfg.paths.synapse_repo}: {e}")
        return None

    clinical_path = cfg.paths.clinical_data
    if not os.path.isabs(clinical_path):
        clinical_path = os.path.join(REPO, clinical_path)
    measures = list(cfg.clinical.measures)
    data = pp.load_clinical_data(clinical_path, measures)
    if not data:
        print(f"[clinical] SKIPPED — could not read workbook {clinical_path}")
        return None

    out_rows, cols = [], ["subject_id", "group"]
    for sid in subjects:
        scores = pp.extract_clinical_scores(data, sid, measures) or {}
        demo = pp.extract_demographics(data.get("demographics"),
                                       data.get("audio"), sid) or {}
        row = {"subject_id": sid,
               "group": "EXP" if sid.startswith("EXP") else "CTRL",
               **scores, **demo}
        for k in row:
            if k not in cols:
                cols.append(k)
        out_rows.append(row)

    csv_path = os.path.join(out_root, "clinical.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)
    n_scored = sum(1 for r in out_rows if len(r) > 2)
    print(f"[clinical] wrote clinical.csv ({n_scored}/{len(out_rows)} subjects "
          f"with workbook entries, from {os.path.basename(clinical_path)})")
    return {"csv": "clinical.csv", "workbook": clinical_path,
            "measures": measures, "subjects_with_entries": n_scored}


def _write_manifest(rows, out_root, cfg, strategy, rej, variant, paired_manifest,
                    clinical):
    cols = ["subject_id", "status", "quality_score", "n_bad_detected",
            "n_real_channels", "n_channels", "paired_trials",
            "pmt", "hlt", "let", "ast", "excluded_tasks", "error"]
    with open(os.path.join(out_root, "finalize_status.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            tc = r.get("task_counts", {}) or {}
            w.writerow({
                "subject_id": r.get("subject_id", ""),
                "status": r.get("status", ""),
                "quality_score": r.get("quality_score"),
                "n_bad_detected": r.get("n_bad_detected"),
                "n_real_channels": r.get("n_real_channels"),
                "n_channels": r.get("n_channels"),
                "paired_trials": r.get("paired_trials", 0),
                "pmt": tc.get("pmt", 0), "hlt": tc.get("hlt", 0),
                "let": tc.get("let", 0), "ast": tc.get("ast", 0),
                "excluded_tasks": ",".join(r.get("excluded_tasks", []) or []),
                "error": r.get("error", ""),
            })
    manifest = {
        "product": "multimodal-final",
        "variant": variant,
        "name": cfg.name,
        "cohort": paired_manifest.get("cohort", "unknown"),
        "built": datetime.now().isoformat(),
        "git_sha": qpaths.git_sha(),
        "channel_strategy": strategy,
        "epoch_rejection": rej,
        "inputs": {"paired_dir": cfg.paths.paired_dir,
                   "paired_built": paired_manifest.get("built"),
                   "paired_git_sha": paired_manifest.get("git_sha")},
        "clinical": clinical,
        "n_ok": sum(1 for r in rows if r.get("status") == "ok"),
        "n_failed": sum(1 for r in rows if r.get("status") == "FAILED"),
        "paired_trials_total": sum(r.get("paired_trials", 0) for r in rows),
        "config": OmegaConf.to_container(cfg, resolve=True),
    }
    with open(os.path.join(out_root, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest


@hydra.main(version_base=None, config_path="../conf", config_name="finalize")
def main(cfg: DictConfig) -> None:
    pre = cfg.preprocessing
    strategy = pre.channel_strategy
    rej = OmegaConf.to_container(pre.epoch_rejection, resolve=True)
    # Base for the relocatable outputs trees (montage asset stays repo-relative).
    base = qpaths.resolve_base(cfg.paths.get("root"))
    montage_file = os.path.join(REPO, cfg.paths.montage)
    paired_root = os.path.join(base, cfg.paths.paired_dir)
    # Variant dir is <cohort>__<preprocessing> (cohort from the paired manifest)
    # so both dimensions of the variant are visible in the path.
    paired_manifest = _load_paired_manifest(paired_root)
    variant = cfg.get("variant") or \
        f"{paired_manifest.get('cohort', 'unknown')}__{cfg.name}"
    out_root = os.path.join(base, cfg.paths.dataset_dir, variant)
    os.makedirs(out_root, exist_ok=True)

    print("=" * 70)
    print(f"FINALIZE  variant={variant}  strategy={strategy}  "
          f"reject_enabled={rej.get('enabled')}")
    print(f"  {os.path.relpath(paired_root, base)} -> {os.path.relpath(out_root, base)}")
    print("=" * 70)

    subjects = sorted(
        d for d in os.listdir(paired_root)
        if os.path.isdir(os.path.join(paired_root, d, "eeg"))
    )
    rows = []
    for pid in subjects:
        paired_subj = os.path.join(paired_root, pid)
        out_subj = os.path.join(out_root, pid)
        try:
            summary = _finalize_subject(
                pid, paired_subj, out_subj, strategy, rej, montage_file, base)
            if summary is None:
                continue
            summary["status"] = "ok"
            rows.append(summary)
        except Exception as e:
            print(f"[error] {pid}: {e}")
            rows.append({"subject_id": pid, "status": "FAILED", "error": str(e),
                         "paired_trials": 0})

    finalized = [r["subject_id"] for r in rows if r.get("status") == "ok"]
    clinical = _write_clinical(out_root, finalized, cfg)
    manifest = _write_manifest(rows, out_root, cfg, strategy, rej, variant,
                               paired_manifest, clinical)
    print("\n" + "=" * 70)
    print(f"Wrote {os.path.join(out_root, 'finalize_status.csv')}")
    print(f"  ok={manifest['n_ok']}  failed={manifest['n_failed']}  "
          f"paired_trials_total={manifest['paired_trials_total']}")


if __name__ == "__main__":
    main()
