"""Load the prior hand-graded quality ratings from participant_info.tsv.

This is the human judgement made during collection (Excellent / Good / Average
/ Bad / No Data / Missing) plus clinical condition, severity, and free-text
notes. It is NOT used by the first independent QC pass -- it is kept here for a
later step that compares the automated score against this prior rating.

The path is auto-detected inside the analysis repo (the file was
deliberately left there, not copied into the data repo); $SYNAPSE_REPO overrides.
"""
import os
import csv

from . import paths as _paths


def load(path=None):
    """Return ``{pid: {quality, condition, severity, notes}}``.

    The bracket markup in the source (e.g. ``[Excellent]``) is stripped.
    """
    path = path or _paths.participant_info_tsv()
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            pid = (row.get("SubjectID") or "").strip()
            if not pid:
                continue
            quality = (row.get("Quality") or "").strip().strip("[]").strip()
            out[pid] = {
                "quality": quality,
                "condition": (row.get("Condition") or "").strip(),
                "severity": (row.get("Severity") or "").strip(),
                "notes": (row.get("Notes") or "").strip(),
            }
    return out
