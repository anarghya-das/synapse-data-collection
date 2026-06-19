# SYNAPSE data repo — notes for Claude

This repo holds raw SYNAPSE CEEGrid ear-EEG recordings + quality tooling. The
analysis/paper code is the sibling repo `../synapse` (see its CLAUDE.md). Use the
`brain` conda env (`/Users/anarghya/miniconda3/envs/brain/bin/python`).

These are the things that are NOT obvious from reading the code:

## Two EEG streams per recording — pick deliberately
Most XDFs contain **two** OpenBCI streams. `obci_eeg1` is RAW; `obci_eeg2` is the
OpenBCI GUI's FILTERED stream (empirically ~5–50 Hz band-pass + 60 Hz notch,
recovered from the PSD ratio — the GUI config was never written down). QC must run
on the RAW stream because the preset's correlation bounds (0.15–0.85) are
calibrated for raw ear-EEG's shared DC drift; that is also what `../synapse`'s
`parse_xdf` uses. `obci_eeg2` is scored only as a cross-check (`score_filtered`) —
running the raw-tuned presets on filtered data over-flags it. Which stream is
"good" flips per participant, so never auto-pick best-of-two as the headline.

## Scoring method: `robust` (default) vs `legacy`
`quality_check(method=...)`. **robust** filters a copy to 1–50 Hz before computing
ALL criteria (flat, dead, noisy via robust-z, low-correlation via *max* off-diagonal
corr; high-corr is reported, not scored). This makes the score filtering-invariant, so
raw and filtered streams converge (mean |Δ|≈4). **legacy** is the original metric that
computes criteria on the UNFILTERED signal — kept only for comparison. The legacy
correlation bound (high=0.85) flags common-mode DC drift as bad, scoring whole
recordings 0 even when every channel is healthy (CTRL09: legacy 0, robust 81). The
redesign rationale + citations (PREP, FASTER) are in `outputs/quality/QC_methodology_review.md`.
Use *max* inter-channel correlation, not mean: ear-EEG channels are weakly correlated
with the contralateral ear, so a healthy channel's MEAN correlation is naturally low.

## quality_score is "% channels surviving QC", not signal fidelity
It is `100·(1 − n_bad/16)`. A clean recording with one dead electrode is 94, not a
statement about SNR. Don't over-read small differences.

## Two devices; detect by STREAM, not folder name
The study used OpenBCI (16ch CEEGrid; streams obci_eeg1/2) and Neurable MW75 (14ch;
stream "MW75 Neuro Neurable Stream"). Only OpenBCI is scored — the QC montage/thresholds
are OpenBCI-specific. EXP10 has BOTH devices in SEPARATE sessions (folders sub-364837
OpenBCI + "sub-212394 (Neurable)"); we score the OpenBCI one and surface both in the
`device` / `devices_present` columns. EXP32 is Neurable-only. Crucially, EXP32's folder
name does NOT contain "neurable" — device must be detected from the EEG stream name
(`qc_core.detect_devices`), not the folder. No single XDF mixes devices. Verified by
scanning every XDF in every sub-folder (incl. -old).

## Resolution quirks live in inventory.py, not scattered
`-old`/`_old` = abandoned sessions, skipped UNLESS the only session (CTRL01/02/03; all
-old folders are plain OpenBCI). EXP44's obci_eeg1 is empty (0 samples). EXP26/CTRL03
have no EEG stream at all. Add new layout exceptions there, in one place.

## qc_core.py is vendored, not original
It is a faithful copy of the QC functions in
`../synapse/preprocessing/utils.py`. If the upstream QC algorithm changes,
re-sync this file; the canonical implementation lives in the analysis repo.

## The prior hand ratings are intentionally NOT in this repo
`../synapse/participant_info.tsv` has manual Excellent/Good/Average/Bad ratings.
They were deliberately left there (not copied in) so the first QC pass is
independent. `synapse_qc/manual.py` can load them for a later comparison step.

## Project layout / conventions
- All generated artifacts go under `outputs/` (`quality/`, `processed/`, `runs/`); source/
  config/data stay at the root. `outputs/processed/*.pkl` (~450 MB) and `outputs/runs/` are
  gitignored. Don't write generated files to the repo root.
- `assets/` holds the canonical `ceegrid_montage_head.npz` + `global_event_id_map.pkl`.
  The published `create_mne` loads the montage by a RELATIVE path; `build_dataset.py` works
  around this by monkeypatching `utils.create_mne` to inject the absolute `assets/` path
  (so there is NO montage file required in CWD — don't re-add one).

## Dataset pipelines (built)
- `pipelines/build_dataset.py` (Hydra: `conf/cohort/` × `conf/preprocessing/`) builds
  processed variants; `pipelines/compare.py` diffs against the published pkl. It REUSES
  `../synapse` preprocessing code (faithful mirror). See README "Processed-data variants".
  `inventory.discover()` is the shared ID→file layer.

## Tooling
- Use `bun` (not npm/npx) for any JS tooling; use Context7 MCP for library docs.
