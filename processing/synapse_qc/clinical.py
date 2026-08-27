"""Per-subject clinical rows straight from the PC workbook (02_PCData.xlsx).

Self-contained replacement for the ``../../synapse`` published clinical loaders,
so ``clinical.csv`` can be built on any machine from the workbook alone. Parses
three sheets:

* ``Demographics``  — one row per subject (ids, age/sex/race, dx history)
* ``Questionnaires`` — one row per subject (THI/GAD/HQ/Iowa/Misophonia scores)
* ``Audio Data``    — one wide row per subject (cohort flags, PTA + UHF
  thresholds, SRT, WRS, LDLs, tinnitus matching, tympanometry)

The workbook uses multi-row decorated headers, so columns are addressed by
position and **validated against the header labels** — if the coordinator
restructures a sheet this fails loudly instead of silently misreading.
Field names mirror the published extractors (age, dx_neuro, pta_right_250, ...)
so downstream consumers see the same schema either way.
"""
import datetime
import math
import re

import pandas as pd

_ID_RE = re.compile(r"^(EXP|CTRL)\d+$")

# Questionnaires sheet: measure -> column index (validated in _check_quest).
MEASURE_COLS = {
    "THI_Total": 3, "GAD_Total": 5,
    "HQ_Functional": 7, "HQ_Social": 8, "HQ_Emotional": 9, "HQ_Total": 10,
    "Iowa_Total": 15,
    "Miso_Section1": 17, "Miso_Section2": 18, "Miso_Section3": 19,
}

_PTA_FREQS = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
_UHF_FREQS = [10000, 12500, 14000, 16000]
_LDL_FREQS = [250, 500, 1000, 2000, 4000, 8000]


def _cell(v):
    """Normalize a raw cell for CSV: NaN -> '', timestamps -> date, else as-is."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if isinstance(v, (pd.Timestamp, datetime.datetime)):
        return v.date().isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    return v


def _header_row(df, label="Group ID"):
    for i in range(min(len(df), 12)):
        if str(df.iat[i, 0]).strip() == label:
            return i
    raise ValueError(f"could not find header row (col0 == {label!r})")


def _expect(df, row, col, want, sheet):
    got = str(df.iat[row, col]).strip()
    ok = (got == want) if not want.endswith("*") else got.startswith(want[:-1])
    if not ok:
        raise ValueError(f"workbook layout changed: {sheet!r} header cell "
                         f"({row},{col}) is {got!r}, expected {want!r}")


def _subject_rows(df, id_col=0):
    """{PID: row_index} for every row whose id column is an EXP/CTRL id.
    First occurrence wins (the sheets can repeat ids in 'Not Sorted' blocks)."""
    out = {}
    for i in range(len(df)):
        pid = str(df.iat[i, id_col]).strip()
        if _ID_RE.match(pid) and pid not in out:
            out[pid] = i
    return out


def _check_quest(df):
    _expect(df, 1, 3, "THI", "Questionnaires")
    _expect(df, 1, 5, "GAD", "Questionnaires")
    _expect(df, 1, 7, "HQ", "Questionnaires")
    _expect(df, 1, 12, "Iowa*", "Questionnaires")
    _expect(df, 1, 17, "Miso*", "Questionnaires")
    _expect(df, 2, 10, "Total Score", "Questionnaires")


def _check_audio(df, hdr):
    for col, want in [(4, "Audio ID"), (15, "Control"), (19, "Misophonia"),
                      (30, "PTA"), (41, "PTA"), (44, "SRT RE"), (47, "WRS RE*"),
                      (68, "Total Score*"), (76, "Total Score*"),
                      (78, "Ear Tested"), (85, "Tymp RE"), (86, "Tymp LE"),
                      (88, "Average LDL*")]:
        _expect(df, hdr, col, want, "Audio Data")
    for col, freq in [(22, 250), (33, 250), (52, 10000), (57, 10000),
                      (62, 250), (70, 250)]:
        if int(float(df.iat[hdr, col])) != freq:
            raise ValueError(f"workbook layout changed: 'Audio Data' header "
                             f"col {col} != {freq}")


def _demographics(df, hdr, i):
    r = df.iloc[i]
    return {
        "age": _cell(r[7]), "sex": _cell(r[8]), "race": _cell(r[9]),
        "date_tested": _cell(r[5]), "dob": _cell(r[6]),
        "dx_neuro": _cell(r[10]), "dx_migraine": _cell(r[11]),
        "dx_mental": _cell(r[12]), "dx_visual": _cell(r[13]),
        "light_sensitivity": _cell(r[14]), "neck_problem": _cell(r[15]),
        "tmj": _cell(r[16]),
        "pc_id": _cell(r[1]), "new_pc_id": _cell(r[2]),
        "neurable_id": _cell(r[3]), "audio_id": _cell(r[4]),
    }


def _audio(df, i):
    r = df.iloc[i]
    row = {
        "is_control": _cell(r[15]), "has_hearing_loss": _cell(r[16]),
        "has_tinnitus": _cell(r[17]), "has_hyperacusis": _cell(r[18]),
        "has_misophonia": _cell(r[19]),
    }
    for base, freqs in [(22, _PTA_FREQS), (52, _UHF_FREQS)]:
        for k, f in enumerate(freqs):
            row[f"pta_right_{f}"] = _cell(r[base + k])
    for base, freqs in [(33, _PTA_FREQS), (57, _UHF_FREQS)]:
        for k, f in enumerate(freqs):
            row[f"pta_left_{f}"] = _cell(r[base + k])
    row.update({
        "pta_right_avg": _cell(r[30]), "hearing_loss_right": _cell(r[31]),
        "pta_left_avg": _cell(r[41]), "hearing_loss_left": _cell(r[42]),
        "srt_right": _cell(r[44]), "srt_left": _cell(r[45]),
        "wrs_right_pct": _cell(r[47]), "wrs_right_db": _cell(r[48]),
        "wrs_left_pct": _cell(r[49]), "wrs_left_db": _cell(r[50]),
    })
    for k, f in enumerate(_LDL_FREQS):
        row[f"ldl_right_{f}"] = _cell(r[62 + k])
    row["ldl_right_avg"] = _cell(r[68])
    for k, f in enumerate(_LDL_FREQS):
        row[f"ldl_left_{f}"] = _cell(r[70 + k])
    row.update({
        "ldl_left_avg": _cell(r[76]), "ldl_overall_avg": _cell(r[88]),
        "tinnitus_ear_tested": _cell(r[78]), "tinnitus_noise_used": _cell(r[79]),
        "tinnitus_pitch_hz": _cell(r[80]), "tinnitus_loudness_db": _cell(r[81]),
        "tympanometry_right": _cell(r[85]), "tympanometry_left": _cell(r[86]),
    })
    return row


def load_clinical_rows(xlsx_path, subjects, measures=None):
    """One flat dict per subject (in the given order): questionnaire scores for
    ``measures`` (default: all of :data:`MEASURE_COLS`) + demographics +
    audiometry. Subjects absent from a sheet just get those fields empty."""
    measures = list(measures) if measures else list(MEASURE_COLS)
    unknown = [m for m in measures if m not in MEASURE_COLS]
    if unknown:
        raise ValueError(f"unknown clinical measures {unknown}; "
                         f"available: {sorted(MEASURE_COLS)}")

    quest = pd.read_excel(xlsx_path, sheet_name="Questionnaires", header=None)
    demo = pd.read_excel(xlsx_path, sheet_name="Demographics", header=None)
    audio = pd.read_excel(xlsx_path, sheet_name="Audio Data", header=None)

    _check_quest(quest)
    demo_hdr = _header_row(demo)
    _expect(demo, demo_hdr, 8, "Biological Sex", "Demographics")
    audio_hdr = _header_row(audio)
    _check_audio(audio, audio_hdr)

    q_rows, d_rows, a_rows = (_subject_rows(x) for x in (quest, demo, audio))

    out = []
    for sid in subjects:
        row = {"subject_id": sid,
               "group": "EXP" if sid.startswith("EXP") else "CTRL"}
        if sid in q_rows:
            for m in measures:
                row[m] = _cell(quest.iat[q_rows[sid], MEASURE_COLS[m]])
        if sid in d_rows:
            row.update(_demographics(demo, demo_hdr, d_rows[sid]))
        if sid in a_rows:
            row.update(_audio(audio, a_rows[sid]))
        out.append(row)
    return out
