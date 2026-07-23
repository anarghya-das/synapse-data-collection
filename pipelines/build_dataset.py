"""Build a processed-data variant: cohort (participant IDs) x preprocessing.

Reuses the PUBLISHED preprocessing code from ../synapse (process_subject /
process_group) so a `preprocessing=published` build faithfully mirrors how
synapse_preprocessed.pkl was made -- the comparison step then isolates real
differences rather than reimplementation bugs.

The only thing we change from the published flow is FILE RESOLUTION: we map
participant IDs -> XDF via synapse_qc.inventory (which correctly falls back to
the `-old` folder for CTRL01/02/03, whose folders were renamed to `-old` after
the pkl was built; the published `exclude -old` discovery would now drop them).

    python -m pipelines.build_dataset cohort=published preprocessing=published
    python -m pipelines.build_dataset --multirun preprocessing=published,interpolate,zero_mask
    python -m pipelines.build_dataset cohort.exp='[EXP01,EXP13]' cohort.ctrl='[CTRL10]'
"""
import os
import sys
import json
import pickle
import warnings
from datetime import datetime

import hydra
from omegaconf import OmegaConf, DictConfig

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from synapse_qc import inventory  # noqa: E402

warnings.filterwarnings("ignore")


def _import_published(synapse_repo, montage_abs):
    """Put the analysis repo on the path, import its preprocessing code, and
    inject an absolute montage path into create_mne so it no longer depends on
    the montage being in the current working directory."""
    if synapse_repo not in sys.path:
        sys.path.insert(0, synapse_repo)
    from publication_analysis import preprocess as pp  # noqa: E402
    from preprocessing import utils  # same module object preprocess uses

    _orig = utils.create_mne

    def _create_mne_abs(*a, **k):
        k.setdefault("montage_file", montage_abs)
        return _orig(*a, **k)

    utils.create_mne = _create_mne_abs   # read_data looks this up at call time
    return pp


def _resolve_cohort(cfg, data_root=None):
    """Return ({EXP: {pid: xdf}}, {CTRL: {pid: xdf}}, skipped[]) for the cohort."""
    parts = {p.pid: p for p in inventory.discover(data_root=data_root)}
    want = {
        "EXP": list(cfg.cohort.exp) or [p for p in parts if p.startswith("EXP")],
        "CTRL": list(cfg.cohort.ctrl) or [p for p in parts if p.startswith("CTRL")],
    }
    mapping = {"EXP": {}, "CTRL": {}}
    skipped, resolved = [], {}
    for grp, ids in want.items():
        for pid in ids:
            p = parts.get(pid)
            if p is None or not p.xdf_path:
                skipped.append({"pid": pid, "reason": "no resolvable XDF"})
                continue
            mapping[grp][pid] = p.xdf_path
            resolved[pid] = {"sub_dir": p.sub_dir, "old_only": p.old_only,
                             "neurable": p.is_neurable}
    return mapping, resolved, skipped


@hydra.main(version_base=None, config_path="../conf", config_name="config")
def main(cfg: DictConfig) -> None:
    pre = cfg.preprocessing
    variant = cfg.variant
    print("=" * 70)
    print(f"BUILD DATASET  variant={variant}  cohort={cfg.cohort.name}  "
          f"channel_strategy={pre.channel_strategy}")
    print("=" * 70)

    # Base for the relocatable data/outputs trees (assets stay repo-relative).
    base = cfg.paths.get("root") or os.environ.get("SYNAPSE_DATA_BASE") or REPO
    data_root = (cfg.paths.get("data_root") or os.environ.get("SYNAPSE_DATA_ROOT")
                 or os.path.join(base, "data"))

    montage_abs = os.path.join(REPO, cfg.paths.montage)
    pp = _import_published(cfg.paths.synapse_repo, montage_abs)

    # Load the (published) global event-ID map directly for consistent event codes.
    with open(os.path.join(REPO, cfg.paths.global_event_map), "rb") as f:
        global_event_map = pickle.load(f)

    task_order = list(cfg.tasks.order)
    task_timings = OmegaConf.to_container(cfg.tasks.timings, resolve=True)
    quality_thresholds = OmegaConf.to_container(pre.quality, resolve=True)
    epoch_rejection_config = OmegaConf.to_container(pre.epoch_rejection, resolve=True)
    channel_strategy = pre.channel_strategy

    mapping, resolved, skipped = _resolve_cohort(cfg, data_root)
    print(f"Resolved EXP={len(mapping['EXP'])} CTRL={len(mapping['CTRL'])} "
          f"| skipped={len(skipped)}")

    exp = pp.process_group(mapping["EXP"], global_event_map, "EXP",
                           task_order, task_timings, quality_thresholds,
                           epoch_rejection_config, channel_strategy=channel_strategy)
    ctrl = pp.process_group(mapping["CTRL"], global_event_map, "CTRL",
                            task_order, task_timings, quality_thresholds,
                            epoch_rejection_config, channel_strategy=channel_strategy)

    # Clinical / behavioural / report keys, built with the published builders so the
    # pkl is a drop-in for the CURRENT synapse analysis scripts (which read
    # channel_masks, clinical_scores, etc.). Schema mirrors run_preprocessing's
    # save_preprocessed dict exactly.
    clinical_measures = list(cfg.clinical.measures)
    clinical_data = pp.load_clinical_data(cfg.paths.clinical_data, clinical_measures)
    if not clinical_data:
        print(f"WARNING: clinical_data is EMPTY (could not read {cfg.paths.clinical_data}); "
              f"clinical_scores/demographics will be empty.")
    all_subjects = list(exp["subjects"]) + list(ctrl["subjects"])
    clinical_scores = {s: pp.extract_clinical_scores(clinical_data, s, clinical_measures)
                       for s in all_subjects}
    demographics = {}
    for s in all_subjects:
        demo = pp.extract_demographics(clinical_data.get("demographics"),
                                       clinical_data.get("audio"), s)
        if demo:
            demographics[s] = demo
    responses = {}
    responses.update(pp.load_responses(mapping["EXP"], group_name="EXP"))
    responses.update(pp.load_responses(mapping["CTRL"], group_name="CTRL"))
    quality_report = pp.generate_quality_report(exp, ctrl, task_order)

    # Top-level keys mirror the current synapse save_preprocessed (16 keys with
    # preprocessing_date + config). Provenance (variant/cohort) lives inside `config`
    # and the sidecar manifest.
    data = {
        "exp_epochs": exp["epochs"],
        "ctrl_epochs": ctrl["epochs"],
        "exp_subjects": exp["subjects"],
        "ctrl_subjects": ctrl["subjects"],
        "exp_quality": exp["quality"],
        "ctrl_quality": ctrl["quality"],
        "clinical_data": clinical_data,
        "clinical_scores": clinical_scores,
        "demographics": demographics,
        "responses": responses,
        "quality_report": quality_report,
        "channel_strategy": channel_strategy,
        "epoch_rejection_enabled": epoch_rejection_config.get("enabled", True),
        "channel_masks": {**exp["channel_masks"], **ctrl["channel_masks"]},
        "preprocessing_date": datetime.now().isoformat(),
        "config": OmegaConf.to_container(cfg, resolve=True),
    }

    out_dir = os.path.join(base, cfg.paths.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    pkl_path = os.path.join(out_dir, f"{variant}.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump(data, f)

    manifest = {
        "variant": variant,
        "cohort": cfg.cohort.name,
        "built": data["preprocessing_date"],
        "channel_strategy": channel_strategy,
        "preprocessing": OmegaConf.to_container(pre, resolve=True),
        "tasks": task_timings,
        "exp_subjects": exp["subjects"],
        "ctrl_subjects": ctrl["subjects"],
        "epochs_per_task": {
            "EXP": {t: len(exp["epochs"][t]) for t in task_order},
            "CTRL": {t: len(ctrl["epochs"][t]) for t in task_order},
        },
        "resolved": resolved,
        "skipped": skipped,
        "clinical_scores_nonempty": sum(1 for v in clinical_scores.values() if v),
        "demographics_nonempty": len(demographics),
        "responses_loaded": len(responses),
        "pkl": os.path.relpath(pkl_path, base),
        "pkl_mb": round(os.path.getsize(pkl_path) / 1024 / 1024, 1),
    }
    with open(os.path.join(out_dir, f"{variant}.manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 70)
    print(f"Wrote {pkl_path}  ({manifest['pkl_mb']} MB)")
    print(f"  EXP {len(exp['subjects'])} / CTRL {len(ctrl['subjects'])} subjects")
    print(f"  epochs/task EXP={manifest['epochs_per_task']['EXP']} "
          f"CTRL={manifest['epochs_per_task']['CTRL']}")
    if skipped:
        print(f"  skipped: {[s['pid'] for s in skipped]}")


if __name__ == "__main__":
    main()
