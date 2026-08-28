"""Per-subject / per-group processing: XDF -> task Epochs + quality + responses.

**Vendored** from the analysis repo's ``publication_analysis/preprocess.py``
(branch `main`, commit e3aa291, 2026-08-28). Copied rather than rewritten so
``build_dataset cohort=published`` still reproduces the published
``synapse_preprocessed.pkl``; ``pipelines/compare.py`` is the regression test.

See :mod:`synapse_qc.epoching` for why processing lives in this repo rather than
being imported from the analysis repo at runtime.

Only the functions ``build_dataset`` calls are vendored. The clinical loaders
(``load_clinical_data`` / ``extract_clinical_scores`` / ``extract_demographics``)
are deliberately NOT copied -- this repo already has a self-contained
reimplementation in :mod:`synapse_qc.clinical`, which parses the workbook
directly and needs no analysis repo at all.
"""
import glob
import os
import traceback

import numpy as np
import pandas as pd
import mne
from tqdm import tqdm

from . import epoching

__all__ = [
    "standardize_response", "load_responses",
    "process_subject", "process_group", "generate_quality_report",
    "load_clinical_data", "extract_clinical_scores", "extract_demographics",
]

# --- module constants, vendored verbatim ---
_HLT_NUMERIC = {0: "cant_hear", 1: "audible", 2: "too_loud"}

_HLT_TEXT = {"cant_hear": "cant_hear", "cannot_hear": "cant_hear",
             "can_not_hear": "cant_hear", "audible": "audible",
             "too_loud": "too_loud"}

_LET_UNCLEAR_TEXT = {"unclear"}

_AUDIO_COLS = {
    "group_id":       0,
    "pc_id":          1,
    "new_pc_id":      2,
    "audio_id":       3,
    "is_control":     9,
    "hearing_loss":  10,
    "tinnitus":      11,
    "hyperacusis":   12,
    "misophonia":    13,
    # Pure-tone audiometry, right ear (cols 15–22): 250, 500, 1k, 2k, 3k, 4k, 6k, 8k Hz
    "pta_re_start":  15, "pta_re_end": 22,
    "pta_re_avg":    23,
    "hl_re":         24,
    # PTA left ear (cols 26–33)
    "pta_le_start":  26, "pta_le_end": 33,
    "pta_le_avg":    34,
    "hl_le":         35,
    # Speech
    "srt_re":        37,
    "srt_le":        38,
    "wrs_re_pct":    40,
    "wrs_re_db":     41,
    "wrs_le_pct":    42,
    "wrs_le_db":     43,
    # HF PTA (cols 45–48 RE, 50–53 LE): 10k, 12.5k, 14k, 16k Hz
    "pta_re_hf_start": 45, "pta_re_hf_end": 48,
    "pta_le_hf_start": 50, "pta_le_hf_end": 53,
    # LDL RE (cols 55–60): 250, 500, 1k, 2k, 4k, 8k Hz
    "ldl_re_start":  55, "ldl_re_end": 60,
    "ldl_re_avg":    61,
    # LDL LE (cols 63–68)
    "ldl_le_start":  63, "ldl_le_end": 68,
    "ldl_le_avg":    69,
    # Tinnitus profile
    "tinn_ear":      71,
    "tinn_noise":    72,
    "tinn_pitch":    73,
    "tinn_loud":     74,
    "tinn_desc":     75,
    "tinn_hx":       76,
    # Tympanometry
    "tymp_re":       78,
    "tymp_le":       79,
    # Overall LDL
    "ldl_avg":       81,
}

_PTA_FREQS = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]

_PTA_HF_FREQS = [10000, 12500, 14000, 16000]

_LDL_FREQS = [250, 500, 1000, 2000, 4000, 8000]


# ADAPTED, not vendored verbatim: upstream resolves relative paths against the
# ANALYSIS repo root. Here they resolve against THIS repo (processing/), and an
# absolute path -- which is what the pipelines pass -- is returned untouched.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_path(rel_path: str) -> str:
    """Resolve a path relative to this repo's root; absolute paths pass through."""
    return rel_path if os.path.isabs(rel_path) else os.path.join(_REPO_ROOT, rel_path)



def _norm_text(value) -> str:
    """Lowercase, strip, and collapse whitespace/underscores/apostrophes."""
    s = str(value).strip().lower().replace("'", "").replace("’", "")
    return "_".join(s.split())


def standardize_response(stim_type, user_value):
    """Map raw `User Value` to (canonical category, numeric digit).

    Returns
    -------
    (response, response_number) : (str or None, int or None)
        ``response`` is one of ``{"cant_hear", "audible", "too_loud"}``
        for HLT rows, ``"unclear"`` or ``"digit"`` for LET rows, or None
        if unrecognized. ``response_number`` is the LET digit (1–20) or
        None.
    """
    if pd.isna(user_value):
        return None, None

    task = str(stim_type).strip().lower()
    norm = _norm_text(user_value)

    # Try to parse as int (covers "1", "1.0", 1, 1.0)
    as_int = None
    try:
        f = float(norm)
        if f.is_integer():
            as_int = int(f)
    except (ValueError, TypeError):
        pass

    if task == "hlt":
        if as_int is not None and as_int in _HLT_NUMERIC:
            return _HLT_NUMERIC[as_int], None
        if norm in _HLT_TEXT:
            return _HLT_TEXT[norm], None
        return None, None

    if task == "let":
        if as_int is not None:
            if as_int == 0:
                return "unclear", None
            if 1 <= as_int <= 20:
                return "digit", as_int
            return None, None
        if norm in _LET_UNCLEAR_TEXT:
            return "unclear", None
        return None, None

    return None, None


def load_responses(subject_mapping, group_name=""):
    """Load behavioral response CSVs for every subject in a group.

    Looks for ``*_responses.csv`` in the same folder as each subject's
    XDF file (``os.path.dirname(xdf_path)``). Returns a dict keyed by
    SYNAPSE subject ID; subjects without a CSV are simply absent.
    """
    import glob

    responses = {}
    missing = []

    for subject_id, file_path in subject_mapping.items():
        if file_path is None:
            continue
        folder = os.path.dirname(file_path)
        matches = glob.glob(os.path.join(folder, "*_responses.csv"))
        if len(matches) == 0:
            missing.append(subject_id)
            continue
        if len(matches) > 1:
            print(f"  [responses] {subject_id}: multiple CSVs found, "
                  f"using {os.path.basename(matches[0])}")

        try:
            df = pd.read_csv(matches[0])
        except Exception as e:
            print(f"  [responses] {subject_id}: read error — {e}")
            continue

        df.insert(0, "subject_id", subject_id)

        standardized = df.apply(
            lambda row: standardize_response(row.get("Stim Type"),
                                             row.get("User Value")),
            axis=1, result_type="expand",
        )
        df["response"] = standardized[0]
        df["response_number"] = pd.array(standardized[1], dtype="Int64")

        responses[subject_id] = df

    if missing:
        print(f"  [responses] {group_name}: no CSV for "
              f"{len(missing)} subject(s): {missing}")

    return responses


def process_subject(file_path, global_event_map, subject_id,
                    task_order, task_timings, quality_thresholds,
                    epoch_rejection_config, channel_strategy="drop"):
    """Load and preprocess a single subject's XDF file."""
    print(f"  Processing {subject_id}...")

    try:
        raw, events, task_mapping = epoching.read_data(
            file_path,
            channel_strategy=channel_strategy,
            use_hed=True,
            global_event_id_map=global_event_map,
            flat_voltage=quality_thresholds["flat_voltage"],
            quality_preset=quality_thresholds.get("preset", "default"),
        )
    except Exception as e:
        print(f"    Error loading {subject_id}: {e}")
        return None, {"error": str(e)}

    quality_info = raw.info.get("temp", {}).get("quality_check", {})
    quality_info["subject_id"] = subject_id
    quality_info["n_channels"] = len(raw.ch_names)
    quality_info["channel_mask"] = raw.info.get("temp", {}).get("channel_mask", None)
    quality_info["ch_names_after"] = list(raw.ch_names)

    # Epoch rejection settings
    rej_enabled = epoch_rejection_config.get("enabled", True)
    z_threshold = epoch_rejection_config.get("z_threshold", 3)
    min_epochs = epoch_rejection_config.get("min_epochs", 5)
    max_reject_pct = epoch_rejection_config.get("max_reject_pct", 50)

    epochs = {}
    for task in task_order:
        try:
            timings = task_timings[task]
            stim_ids = epoching.select_event_ids(task_mapping, task,
                                              phases=["stim"])
            if not stim_ids:
                print(f"    No events for {task}")
                epochs[task] = None
                continue

            task_epochs = mne.Epochs(
                raw, events, event_id=stim_ids,
                tmin=timings["tmin"],
                tmax=timings["tmax"],
                baseline=None,
                preload=True,
                verbose=False,
            )

            n_epochs = len(task_epochs)
            if n_epochs == 0:
                print(f"    {task}: 0 epochs")
                epochs[task] = None
                continue

            if rej_enabled and n_epochs >= 3:
                # Z-score rejection: compute max-channel PTP per epoch,
                # reject epochs where PTP > mean + z_threshold * SD
                data = task_epochs.get_data()  # (n_epochs, n_ch, n_times)
                ptps = np.ptp(data, axis=2).max(axis=1)  # max PTP across ch
                ptp_mean = ptps.mean()
                ptp_std = ptps.std()
                thresh = ptp_mean + z_threshold * ptp_std
                bad_mask = ptps > thresh

                # Drop flagged epochs
                bad_indices = np.where(bad_mask)[0]
                if len(bad_indices) > 0:
                    task_epochs.drop(bad_indices, reason="PTP_ZSCORE",
                                     verbose=False)

                n_after = len(task_epochs)
                n_rejected = n_epochs - n_after
                pct = (n_rejected / n_epochs * 100) if n_epochs else 0

                # Store per-task rejection stats
                quality_info.setdefault("epoch_rejection", {})[task] = {
                    "n_before": n_epochs,
                    "n_after": n_after,
                    "n_rejected": n_rejected,
                    "pct_rejected": round(pct, 1),
                    "threshold_uv": round(thresh * 1e6, 1),
                    "z_threshold": z_threshold,
                    "ptp_mean_uv": round(ptp_mean * 1e6, 1),
                    "ptp_std_uv": round(ptp_std * 1e6, 1),
                }

                # Exclude task if too few epochs or too many rejected
                if n_after < min_epochs:
                    print(f"    WARNING: {task}: {n_epochs} -> {n_after} "
                          f"epochs (< {min_epochs}) — EXCLUDED")
                    task_epochs = None
                elif pct > max_reject_pct:
                    print(f"    WARNING: {task}: {n_epochs} -> {n_after} "
                          f"epochs ({pct:.0f}% rejected > {max_reject_pct}%)"
                          f" — EXCLUDED")
                    task_epochs = None
                else:
                    print(f"    {task}: {n_epochs} -> {n_after} epochs "
                          f"({n_rejected} rejected, thresh="
                          f"{thresh*1e6:.0f}µV)")
            else:
                print(f"    {task}: {n_epochs} epochs")

            epochs[task] = task_epochs

        except Exception as e:
            print(f"    Error creating {task} epochs: {e}")
            epochs[task] = None

    return epochs, quality_info


def process_group(subject_mapping, global_event_map, group_name,
                  task_order, task_timings, quality_thresholds,
                  epoch_rejection_config, channel_strategy="drop"):
    """Process all subjects in a group (EXP or CTRL)."""
    print(f"\n{'=' * 60}")
    print(f"Processing {group_name} group ({len(subject_mapping)} subjects)")
    print("=" * 60)

    all_epochs = {task: [] for task in task_order}
    all_subjects = []
    all_quality = []

    for subject_id, file_path in tqdm(subject_mapping.items(),
                                      desc=group_name):
        if file_path is None or not os.path.exists(file_path):
            print(f"  Skipping {subject_id}: no file found")
            continue

        epochs, quality_info = process_subject(
            file_path, global_event_map, subject_id,
            task_order, task_timings, quality_thresholds,
            epoch_rejection_config,
            channel_strategy=channel_strategy,
        )

        if epochs is None:
            continue

        all_subjects.append(subject_id)
        all_quality.append(quality_info)

        for task in task_order:
            if epochs.get(task) is not None:
                all_epochs[task].append(epochs[task])

    # Collect per-subject channel masks
    channel_masks = {}
    for q in all_quality:
        sid = q.get("subject_id")
        mask = q.get("channel_mask")
        if sid and mask is not None:
            channel_masks[sid] = mask

    print(f"\n{group_name} Summary:")
    print(f"  Subjects processed: {len(all_subjects)}")
    for task in task_order:
        print(f"  {task.upper()}: {len(all_epochs[task])} subjects with data")

    return {
        "epochs": all_epochs,
        "subjects": all_subjects,
        "quality": all_quality,
        "channel_masks": channel_masks,
    }


def generate_quality_report(exp_data, ctrl_data, task_order):
    """Generate a quality report for both groups."""
    report = {
        "exp": {
            "n_subjects": len(exp_data["subjects"]),
            "subjects": exp_data["subjects"],
            "quality": exp_data["quality"],
        },
        "ctrl": {
            "n_subjects": len(ctrl_data["subjects"]),
            "subjects": ctrl_data["subjects"],
            "quality": ctrl_data["quality"],
        },
    }

    for group_name, data in [("exp", exp_data), ("ctrl", ctrl_data)]:
        epochs_per_task = {}
        for task in task_order:
            total_epochs = sum(
                len(e) for e in data["epochs"][task] if e is not None)
            epochs_per_task[task] = total_epochs
        report[group_name]["epochs_per_task"] = epochs_per_task

        # Aggregate epoch rejection stats per task
        rej_stats = {}
        for task in task_order:
            task_before = 0
            task_after = 0
            task_rejected = 0
            n_subjects = 0
            for q in data["quality"]:
                rej_info = q.get("epoch_rejection", {}).get(task)
                if rej_info:
                    task_before += rej_info["n_before"]
                    task_after += rej_info["n_after"]
                    task_rejected += rej_info["n_rejected"]
                    n_subjects += 1
            if n_subjects > 0:
                pct = (task_rejected / task_before * 100) if task_before else 0
                rej_stats[task] = {
                    "total_before": task_before,
                    "total_after": task_after,
                    "total_rejected": task_rejected,
                    "pct_rejected": round(pct, 1),
                    "n_subjects": n_subjects,
                }
        report[group_name]["epoch_rejection_stats"] = rej_stats

    return report


# ---------------------------------------------------------------------------
# Clinical loaders, in the PKL's nested shape.
#
# These duplicate what :mod:`synapse_qc.clinical` does, on purpose. The pkl
# schema stores per-frequency audiometry as NESTED dicts
# (``demographics[sid]['pta_right'] == {250: 5.0, 500: 0.0, ...}``) and keeps
# the raw sheet DataFrames under ``clinical_data``; reproducing the published
# pkl requires exactly that shape. ``synapse_qc.clinical`` instead flattens to
# ``pta_right_250`` columns for the multimodal ``clinical.csv``, and parses the
# workbook without any analysis-repo code. Two consumers, two shapes -- do not
# collapse them.
# ---------------------------------------------------------------------------

def load_clinical_data(clinical_path, clinical_measures):
    """Load clinical questionnaire data from the Excel file.

    Returns only experimental (EXP) subjects.
    """
    full_path = _resolve_path(clinical_path)

    if not os.path.exists(full_path):
        print(f"Warning: Clinical data file not found: {full_path}")
        return {}

    print(f"Loading clinical data from {full_path}")

    try:
        quest_df_raw = pd.read_excel(full_path, sheet_name="Questionnaires",
                                     header=None)

        # Find where EXP group starts
        exp_group_row = None
        for idx in range(len(quest_df_raw)):
            val = quest_df_raw.iloc[idx, 0]
            if pd.notna(val) and "EXP" in str(val).upper() and "Group" in str(val):
                exp_group_row = idx
                break

        exp_header_row = exp_group_row + 1 if exp_group_row else None
        exp_data_start = exp_header_row + 1 if exp_header_row else None

        if exp_data_start:
            exp_data = quest_df_raw.iloc[exp_data_start:].copy().reset_index(
                drop=True)
            exp_data = exp_data[exp_data.iloc[:, 0].notna()]
        else:
            raise ValueError("Could not find EXP group in questionnaire data")

        col_mapping = {
            0: "Subject",
            2: "Condition",
            3: "THI_Total",
            4: "THI_Severity",
            5: "GAD_Total",
            6: "GAD_Severity",
            7: "HQ_Functional",
            8: "HQ_Social",
            9: "HQ_Emotional",
            10: "HQ_Total",
            11: "HQ_Significant",
            12: "Iowa_Factor1",
            13: "Iowa_Factor2",
            14: "Iowa_Factor3",
            15: "Iowa_Total",
            17: "Miso_Section1",
            18: "Miso_Section2",
            19: "Miso_Section3",
        }

        new_cols = []
        for i in range(len(exp_data.columns)):
            new_cols.append(col_mapping.get(i, f"col_{i}"))
        exp_data.columns = new_cols

        exp_data = exp_data[exp_data["Subject"].notna()]
        exp_data = exp_data[
            exp_data["Subject"].astype(str).str.startswith("EXP")]

        keep_cols = list(col_mapping.values())
        exp_data = exp_data[[c for c in keep_cols if c in exp_data.columns]]

        print(f"  Loaded questionnaire data for {len(exp_data)} EXP subjects")

        severity_df = pd.read_excel(full_path,
                                    sheet_name="Severity Data Sum", header=3)
        severity_df = severity_df.loc[
            :, ~severity_df.columns.str.contains("^Unnamed")]

        audio_df = pd.read_excel(full_path, sheet_name="Audio Data", header=6)
        demo_df = pd.read_excel(full_path, sheet_name="Demographics", header=2)

        return {
            "questionnaires": exp_data,
            "severity": severity_df,
            "audio": audio_df,
            "demographics": demo_df,
        }

    except Exception as e:
        print(f"  Error loading clinical data: {e}")
        import traceback
        traceback.print_exc()
        return {}


def extract_clinical_scores(clinical_data, subject_id, clinical_measures):
    """Extract clinical scores for a single subject."""
    scores = {}

    q_df = clinical_data.get("questionnaires")
    if q_df is None or not isinstance(q_df, pd.DataFrame):
        return scores

    subj_row = q_df[q_df["Subject"] == subject_id]
    if len(subj_row) == 0:
        return scores

    subj_row = subj_row.iloc[0]

    for col in clinical_measures:
        if col in subj_row.index:
            val = subj_row[col]
            if pd.notna(val):
                try:
                    scores[col] = float(val)
                except (ValueError, TypeError):
                    pass

    return scores


def _safe(val):
    """Return val if it's a real value, else None."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _audio_freq_dict(audio_row, start_idx, end_idx, freqs):
    """Pull a frequency-indexed slice from an Audio Data row."""
    vals = audio_row.iloc[start_idx:end_idx + 1].tolist()
    out = {}
    for f, v in zip(freqs, vals):
        v_ok = _safe(v)
        if v_ok is not None:
            try:
                out[f] = float(v_ok)
            except (ValueError, TypeError):
                pass
    return out


def extract_demographics(dem_df, audio_df, subject_id):
    """Build a flat demographics dict for a single subject.

    Pulls age / sex / race / medical-dx flags from the Demographics
    sheet and condition flags + audiometry from the Audio Data sheet.
    Returns an empty dict if the subject isn't in either sheet.
    """
    out = {}

    # Demographics sheet
    if dem_df is not None and isinstance(dem_df, pd.DataFrame) and \
            "Group ID" in dem_df.columns:
        dem_match = dem_df[
            dem_df["Group ID"].astype(str).str.strip() == subject_id]
        if len(dem_match) > 0:
            row = dem_match.iloc[0]
            field_map = {
                "age": "Age",
                "sex": "Biological Sex",
                "race": "Race",
                "date_tested": "Date tested",
                "dob": "DOB",
                "dx_neuro": "Neuro dx",
                "dx_migraine": "Migraine dx",
                "dx_mental": "Mental dx",
                "dx_visual": "Visual dx",
                "light_sensitivity": "Light sensitivity",
                "neck_problem": "Neck problem",
                "tmj": "TMJ",
                "pc_id": "PC ID",
                "new_pc_id": "New PC ID",
                "audio_id": "Audio ID",
            }
            for key, col in field_map.items():
                if col in row.index:
                    v = _safe(row[col])
                    if v is not None:
                        if key == "age":
                            try:
                                out[key] = float(v)
                            except (ValueError, TypeError):
                                pass
                        else:
                            out[key] = v

    # Audio Data sheet — positional slicing
    if audio_df is not None and isinstance(audio_df, pd.DataFrame) and \
            len(audio_df.columns) > _AUDIO_COLS["ldl_avg"]:
        group_col = audio_df.iloc[:, _AUDIO_COLS["group_id"]]
        audio_match = audio_df[
            group_col.astype(str).str.strip() == subject_id]
        if len(audio_match) > 0:
            row = audio_match.iloc[0]

            # Condition flags
            flag_map = {
                "is_control": "is_control",
                "has_hearing_loss": "hearing_loss",
                "has_tinnitus": "tinnitus",
                "has_hyperacusis": "hyperacusis",
                "has_misophonia": "misophonia",
            }
            for out_key, col_key in flag_map.items():
                v = _safe(row.iloc[_AUDIO_COLS[col_key]])
                if v is not None:
                    try:
                        out[out_key] = int(float(v))
                    except (ValueError, TypeError):
                        out[out_key] = v

            # PTA + HF PTA per ear
            pta_re = _audio_freq_dict(row, _AUDIO_COLS["pta_re_start"],
                                      _AUDIO_COLS["pta_re_end"], _PTA_FREQS)
            pta_re.update(_audio_freq_dict(row,
                                           _AUDIO_COLS["pta_re_hf_start"],
                                           _AUDIO_COLS["pta_re_hf_end"],
                                           _PTA_HF_FREQS))
            pta_le = _audio_freq_dict(row, _AUDIO_COLS["pta_le_start"],
                                      _AUDIO_COLS["pta_le_end"], _PTA_FREQS)
            pta_le.update(_audio_freq_dict(row,
                                           _AUDIO_COLS["pta_le_hf_start"],
                                           _AUDIO_COLS["pta_le_hf_end"],
                                           _PTA_HF_FREQS))
            if pta_re:
                out["pta_right"] = pta_re
            if pta_le:
                out["pta_left"] = pta_le

            for out_key, col_key, caster in [
                ("pta_right_avg", "pta_re_avg", float),
                ("pta_left_avg", "pta_le_avg", float),
                ("hearing_loss_right", "hl_re", str),
                ("hearing_loss_left", "hl_le", str),
                ("srt_right", "srt_re", float),
                ("srt_left", "srt_le", float),
                ("wrs_right_pct", "wrs_re_pct", float),
                ("wrs_right_db", "wrs_re_db", float),
                ("wrs_left_pct", "wrs_le_pct", float),
                ("wrs_left_db", "wrs_le_db", float),
                ("ldl_right_avg", "ldl_re_avg", float),
                ("ldl_left_avg", "ldl_le_avg", float),
                ("ldl_overall_avg", "ldl_avg", float),
                ("tinnitus_ear_tested", "tinn_ear", str),
                ("tinnitus_noise_used", "tinn_noise", str),
                ("tinnitus_pitch_hz", "tinn_pitch", float),
                ("tinnitus_loudness_db", "tinn_loud", float),
                ("tinnitus_description", "tinn_desc", str),
                ("tinnitus_case_hx", "tinn_hx", str),
                ("tympanometry_right", "tymp_re", str),
                ("tympanometry_left", "tymp_le", str),
            ]:
                v = _safe(row.iloc[_AUDIO_COLS[col_key]])
                if v is not None:
                    try:
                        out[out_key] = caster(v)
                    except (ValueError, TypeError):
                        pass

            # LDL per ear
            ldl_re = _audio_freq_dict(row, _AUDIO_COLS["ldl_re_start"],
                                      _AUDIO_COLS["ldl_re_end"], _LDL_FREQS)
            ldl_le = _audio_freq_dict(row, _AUDIO_COLS["ldl_le_start"],
                                      _AUDIO_COLS["ldl_le_end"], _LDL_FREQS)
            if ldl_re:
                out["ldl_right"] = ldl_re
            if ldl_le:
                out["ldl_left"] = ldl_le

    return out
