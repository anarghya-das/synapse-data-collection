# eeg_quality

Recording-time EEG safety net for the hearing study. Two independent layers that
together stop a session's EEG from being silently lost (no stream, 0 samples,
railed/dead electrodes, or a mid-session drop).

## Layer 1 — pre-flight gate (`recording_checks.py`)

Runs **inside PsychoPy**, automatically, at session start (before LabRecorder is
told to `start`). It is deliberately minimal — **numpy + pylsl only**, no mne —
because it must import inside the PsychoPy app bundle.

It resolves `obci_eeg1`, pulls a few seconds, and fails if the stream is absent,
pushing zero samples, dropping badly, or fully flat/frozen. On failure the
experiment logs the reason (console + `<participant>.log`) and quits before any
XDF is written. No GUI, no prompt.

The Builder file imports it as:

```python
from eeg_quality.recording_checks import preflight_eeg_gate
```

`__init__.py` is intentionally empty so this import never pulls in mne/qc_core.

## Layer 2 — live watchdog (`eeg_watchdog.py`)

A **standalone window you run beside PsychoPy**, in a Python env that has mne
(see `requirements.txt`). It subscribes to `obci_eeg1` on its own inlet and,
every ~1.5 s, scores a rolling window with the project's robust QC
(`qc_core.quality_check`). It shows a green/red banner, the quality score, a
per-channel grid, and **beeps** when it goes bad — catching what the minimal gate
can't: a montage that is connected but railed, and a stream that dies mid-run.

```bash
pip install -r eeg_quality/requirements.txt      # in your conda env, NOT PsychoPy
python eeg_quality/eeg_watchdog.py                # live GUI window
python eeg_quality/eeg_watchdog.py --no-gui       # terminal status line
```

## `qc_core.py`

The robust CEEGrid QC engine, **vendored verbatim** from
`synapse-data/synapse_qc/qc_core.py` so the watchdog scores signal quality with
the exact same algorithm as the analysis pipeline. Re-copy it if the upstream QC
changes; do not edit it here.

## `mock_eeg_stream.py`

Fakes an `obci_eeg1` stream so you can test both layers without the OpenBCI.

```bash
python eeg_quality/mock_eeg_stream.py good        # then run the gate / watchdog
python eeg_quality/mock_eeg_stream.py railed
python eeg_quality/mock_eeg_stream.py good --selftest   # streams + scores, prints verdict
```

## Scope

Offline / post-hoc QC of recorded files lives in the **synapse-data** analysis
repo (where `qc_core` is the source of truth), not here. This folder is only the
*collection-time* safety net.
