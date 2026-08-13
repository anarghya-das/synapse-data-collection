"""Core CEEGrid EEG quality-check routines — re-export, not a copy.

The canonical implementation lives in ``processing/synapse_qc/qc_core.py`` in
this repo. This module used to be a VENDORED copy that had to be re-synced by
hand whenever the QC changed; now that the processing pipelines live in the
same repo it simply loads the canonical file, so the live watchdog and the
offline pipelines can never drift.

The file is loaded by path (not ``import synapse_qc.qc_core``) on purpose:
``synapse_qc/__init__.py`` eagerly imports ``excel``/``av_align``, which need
pandas — not installed in the watchdog env (``requirements.txt`` here). The
canonical ``qc_core.py`` itself only needs numpy/scipy/mne/pyxdf, all of which
this env has.

The PsychoPy pre-flight gate (``recording_checks.py``) does NOT import this —
it stays numpy+pylsl-only so it can run inside the PsychoPy app bundle.
"""
import importlib.util
import os
import sys

_CANONICAL = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        os.pardir,
        "processing",
        "synapse_qc",
        "qc_core.py",
    )
)

_spec = importlib.util.spec_from_file_location("_synapse_qc_core", _CANONICAL)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_synapse_qc_core"] = _mod
_spec.loader.exec_module(_mod)

# Make `import qc_core; qc_core.<anything>` resolve on the canonical module.
sys.modules[__name__] = _mod
