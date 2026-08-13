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

## Data lives on the server; paths are relocatable
The canonical `data/` (17 GB raw) + `outputs/` (~9 GB generated) were MOVED off
this repo to `ub-polar:/data1/anarghya/synapse-data/{data,outputs}` (local copies
deleted). Nothing is hardcoded to the repo anymore: `inventory._default_data_root()`
honors `$SYNAPSE_DATA_ROOT` / `$SYNAPSE_DATA_BASE`, and the Hydra pipelines take
`paths.root` (base holding data/+outputs) + `paths.data_root` (raw only), both
also reading those env vars, defaulting to the repo root so old behaviour is
unchanged when nothing is set. Precedence + examples are in the README "Data
location" section. WHY split base vs data_root: outputs and raw data can sit in
different places. WHY assets stay repo-relative: montage/event-map/`../synapse`
are code+config, not data — they were deliberately NOT relocated, so only `data/`
and the `outputs/*` trees follow the base. To actually run the pipelines you must
either mount the server path (SSHFS) or run on the server; assets still resolve
from the repo checkout.

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

## The multimodal (video+EEG) pipeline is two stages — detect-and-defer
The DL dataset is built in two Hydra pipelines, deliberately split so the SLOW,
one-time work (temporal EEG↔video alignment + video re-encoding) is separated from
the FAST, swappable channel-handling experiments:
- `pipelines/pair_video.py` → `outputs/paired/`. Filters, epochs, and pairs EVERY
  boundary-valid trial with ALL 16 channels intact. QC runs for DETECTION ONLY: bad
  channels are recorded (in each `_epo.fif`'s `info['bads']` + a per-subject
  `*_channels.tsv`/`*_qc.json` sidecar) but NOT interpolated/dropped/zeroed, and NO
  epoch rejection happens. So no subject is dropped here on channel quality — that
  decision is deferred. `preprocessing.channel_strategy`/`epoch_rejection` are IGNORED
  by epoch mode (they still apply to legacy `marker` mode).
- `pipelines/finalize_dataset.py` (`conf/finalize.yaml`) → `outputs/dataset/<name>/`.
  Applies `channel_strategy` (interpolate|zero_mask|drop|keep_all) + PTP `epoch_rejection`
  from the `preprocessing` group, emits a per-channel validity mask (`*_channel_mask.npy`,
  1=real / 0=interpolated/masked/dropped), and re-filters the alignment CSV to surviving
  pairs (video is never re-encoded — clips are referenced in place under `outputs/paired`).
  Run it once per strategy to get interpolate/zero_mask/drop variants side by side.
- WHY this matters: (1) rejection PTP is computed over GOOD channels only, so a noisy
  bad channel can't corrupt it — this only works because channel handling is decoupled;
  (2) interpolation is irreversible, so pairing keeps raw channels + a mask, letting you
  try masking vs interpolation without re-running the slow pair step; (3) `interpolate`+z=3
  in finalize reproduces the old baked-in behaviour.
- `pair_video` patches `utils.quality_check` → `synapse_qc.qc_core.quality_check` (robust,
  filtering-invariant, max off-diag corr). The analysis-repo `quality_check` is the LEGACY
  mean-corr metric that flags common-mode DC drift as bad and fails whole healthy recordings
  (EXP08/EXP10/CTRL09/CTRL12 score 0 legacy / 75–100 robust). `build_dataset` does NOT patch
  it — its legacy QC is intentional there (faithful mirror of the published pkl).

## Tooling
- Use `bun` (not npm/npx) for any JS tooling; use Context7 MCP for library docs.
