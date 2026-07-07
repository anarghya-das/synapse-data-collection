"""Pair per-trial webcam clips with stim-locked EEG epochs (multimodal dataset).

Ports ``../synapse/split_video.py`` into this repo's conventions:
  * file resolution via ``synapse_qc.inventory`` (the XDF *and* the per-participant
    ``.avi``), not ``build_combined_mapping`` / next-to-XDF guessing;
  * EEG parameters come from the Hydra ``preprocessing`` group -- the SAME configs
    ``build_dataset`` uses -- so stream / bandpass / notch / channel_strategy /
    quality / epoch_rejection are all configurable and stay in lock-step with the
    processed-pkl variants;
  * task windows from ``tasks.timings``; video options from the ``video`` group;
  * outputs under ``outputs/paired/<name>/`` (one ``sub-<PID>/`` tree per subject
    + a top-level ``dataset_manifest.csv``).

The published EEG alignment helpers (``create_mne`` and the marker/event
machinery) are reused live from ``../synapse`` exactly like ``build_dataset``,
with the absolute montage path injected into ``create_mne`` so it does not depend
on the current working directory.

    python -m pipelines.pair_video                                   # usable cohort, published EEG params, epoch mode
    python -m pipelines.pair_video preprocessing=drop                # different bad-channel handling
    python -m pipelines.pair_video video.mode=marker                 # legacy marker-to-marker clips
    python -m pipelines.pair_video preprocessing.bandpass.low=2 preprocessing.notch_freq=-1   # tweak filters (notch<0 disables)
    python -m pipelines.pair_video cohort=published
    python -m pipelines.pair_video cohort.exp='[EXP01,EXP13]' cohort.ctrl='[CTRL10]'  # ad-hoc subset
"""
import os
import sys
import csv
import json
import warnings
from datetime import datetime

import hydra
from omegaconf import OmegaConf, DictConfig

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from synapse_qc import inventory  # noqa: E402

warnings.filterwarnings("ignore")


def _import_utils(synapse_repo, montage_abs):
    """Put the analysis repo on the path and inject the absolute montage path into
    ``create_mne`` (so EEG alignment does not depend on the CWD). Mirrors
    ``build_dataset._import_published`` but only needs ``preprocessing.utils``."""
    if synapse_repo not in sys.path:
        sys.path.insert(0, synapse_repo)
    from preprocessing import utils  # same module av_align.align_eeg looks up

    _orig = utils.create_mne

    def _create_mne_abs(*a, **k):
        k.setdefault("montage_file", montage_abs)
        return _orig(*a, **k)

    utils.create_mne = _create_mne_abs   # av_align calls utils.create_mne at run time
    return utils


def _resolve_cohort(cfg):
    """Yield ``(group, pid, Participant|None)`` for the requested cohort.

    Same selection rule as ``build_dataset._resolve_cohort`` (empty list => every
    discovered ID for that group), but we keep the whole Participant because we
    also need its resolved ``.avi`` (``p.video``)."""
    parts = {p.pid: p for p in inventory.discover()}
    want = {
        "EXP": list(cfg.cohort.exp) or [p for p in parts if p.startswith("EXP")],
        "CTRL": list(cfg.cohort.ctrl) or [p for p in parts if p.startswith("CTRL")],
    }
    for grp, ids in want.items():
        for pid in ids:
            yield grp, pid, parts.get(pid)


def _write_dataset_manifest(rows, out_root, cfg, eeg_params):
    """Top-level CSV + JSON capturing per-subject status and the run provenance."""
    csv_path = os.path.join(out_root, "dataset_manifest.csv")
    cols = [
        "group", "subject_id", "status", "mode", "n_bad_channels",
        "video_present", "paired_trials", "pmt", "hlt", "let", "ast",
        "excluded_tasks", "error",
    ]
    flat = []
    for r in rows:
        tc = r.get("task_counts", {}) or {}
        flat.append({
            "group": r.get("group", ""),
            "subject_id": r.get("subject_id", ""),
            "status": r.get("status", ""),
            "mode": r.get("mode", cfg.video.mode),
            "n_bad_channels": r.get("n_bad_channels"),
            "video_present": r.get("video_present"),
            "paired_trials": r.get("paired_trials", 0),
            "pmt": tc.get("pmt", 0), "hlt": tc.get("hlt", 0),
            "let": tc.get("let", 0), "ast": tc.get("ast", 0),
            "excluded_tasks": ",".join(r.get("excluded_tasks", []) or []),
            "error": r.get("error", ""),
        })
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(flat)

    manifest = {
        "name": cfg.name,
        "cohort": cfg.cohort.name,
        "built": datetime.now().isoformat(),
        "mode": cfg.video.mode,
        "eeg_params": eeg_params,
        "tasks": OmegaConf.to_container(cfg.tasks.timings, resolve=True),
        "video": OmegaConf.to_container(cfg.video, resolve=True),
        "n_ok": sum(1 for r in rows if r.get("status") == "ok"),
        "n_failed": sum(1 for r in rows if r.get("status") == "FAILED"),
        "n_skipped": sum(1 for r in rows if r.get("status") == "skipped"),
        "paired_trials_total": sum(r.get("paired_trials", 0) for r in rows),
    }
    with open(os.path.join(out_root, "dataset_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    return csv_path, manifest


@hydra.main(version_base=None, config_path="../conf", config_name="pair_video")
def main(cfg: DictConfig) -> None:
    montage_abs = os.path.join(REPO, cfg.paths.montage)
    _import_utils(cfg.paths.synapse_repo, montage_abs)
    from synapse_qc import av_align  # imported after ../synapse is on sys.path

    pre = cfg.preprocessing
    vid = cfg.video
    out_root = os.path.join(REPO, cfg.paths.paired_dir, cfg.name)
    os.makedirs(out_root, exist_ok=True)

    # All EEG knobs come from the `preprocessing` group -> fully configurable and
    # identical to what build_dataset feeds create_mne / the epoch rejection.
    eeg_kw = dict(
        eeg_stream_name=pre.eeg_stream_name,
        channel_strategy=pre.channel_strategy,
        bandpass=OmegaConf.to_container(pre.bandpass, resolve=True),
        flat_voltage=pre.quality.flat_voltage,
        notch_freq=pre.notch_freq,
        quality_preset=pre.quality.preset,
        bindings=list(vid.bindings),
        task_timings=OmegaConf.to_container(cfg.tasks.timings, resolve=True),
        rejection=OmegaConf.to_container(pre.epoch_rejection, resolve=True),
        mode=vid.mode,
        exclude_phases=list(vid.exclude_phases),
        fps=vid.fps,
        sfreq=vid.sfreq,
        no_eeg=vid.no_eeg,
        no_video=vid.no_video,
    )

    print("=" * 70)
    print(f"PAIR VIDEO  name={cfg.name}  cohort={cfg.cohort.name}  mode={vid.mode}")
    print(f"  EEG: stream={pre.eeg_stream_name}  strategy={pre.channel_strategy}  "
          f"bp={eeg_kw['bandpass']}  notch={pre.notch_freq}  "
          f"reject_enabled={eeg_kw['rejection'].get('enabled')}")
    print(f"  -> {os.path.relpath(out_root, REPO)}")
    print("=" * 70)

    rows = []
    for grp, pid, p in _resolve_cohort(cfg):
        row = {"group": grp, "subject_id": pid, "mode": vid.mode}
        if p is None or not p.xdf_path:
            print(f"[skip] {pid}: no resolvable XDF")
            row.update({"status": "skipped", "error": "no resolvable XDF",
                        "paired_trials": 0})
            rows.append(row)
            continue
        out_dir = os.path.join(out_root, f"sub-{pid}")
        try:
            summary = av_align.pair_recording(
                p.xdf_path, p.video or None, pid, out_dir, **eeg_kw
            )
            row.update({"status": "ok", **summary})
        except Exception as e:  # isolate one subject's failure (e.g. no EEG stream)
            print(f"[error] {grp}/{pid}: {e}")
            row.update({"status": "FAILED", "error": str(e), "paired_trials": 0})
        rows.append(row)

    eeg_params = {k: eeg_kw[k] for k in (
        "eeg_stream_name", "channel_strategy", "bandpass", "flat_voltage",
        "notch_freq", "quality_preset", "rejection")}
    csv_path, manifest = _write_dataset_manifest(rows, out_root, cfg, eeg_params)

    print("\n" + "=" * 70)
    print(f"Wrote {csv_path}")
    print(f"  ok={manifest['n_ok']}  failed={manifest['n_failed']}  "
          f"skipped={manifest['n_skipped']}  "
          f"paired_trials_total={manifest['paired_trials_total']}")


if __name__ == "__main__":
    main()
