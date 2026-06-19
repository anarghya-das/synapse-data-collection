"""Load the prior hand-graded quality ratings from participant_info.tsv.

This is the human judgement made during collection (Excellent / Good / Average
/ Bad / No Data / Missing) plus clinical condition, severity, and free-text
notes. It is NOT used by the first independent QC pass -- it is kept here for a
later step that compares the automated score against this prior rating.

The default path points at the original file in the analysis repo (it was
deliberately left there, not copied into the data repo).
"""
import os
import csv

DEFAULT_TSV = "/Users/anarghya/Developer/research/synapse/participant_info.tsv"


def load(path=None):
    """Return ``{pid: {quality, condition, severity, notes}}``.

    The bracket markup in the source (e.g. ``[Excellent]``) is stripped.
    """
    path = path or DEFAULT_TSV
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
