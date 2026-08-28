# SYNAPSE processing — notes for Claude

This directory (formerly the standalone `synapse-data` repo, merged into the
collection repo via git subtree) holds the quality tooling + dataset pipelines
for the SYNAPSE CEEGrid ear-EEG recordings. The analysis/paper code is the separate `synapse-analysis` repo; it is NOT a
runtime dependency any more (see "THIS repo owns processing" below). Run
everything from inside this directory.

These are the things that are NOT obvious from reading the code:

## Two EEG streams per recording — pick deliberately
Most XDFs contain **two** OpenBCI streams. `obci_eeg1` is RAW; `obci_eeg2` is the
OpenBCI GUI's FILTERED stream (empirically ~5–50 Hz band-pass + 60 Hz notch,
recovered from the PSD ratio — the GUI config was never written down). QC must run
on the RAW stream because the preset's correlation bounds (0.15–0.85) are
calibrated for raw ear-EEG's shared DC drift; that is also what `../../synapse`'s
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
redesign rationale + citations (PREP, FASTER) are in `docs/QC_methodology_review.md`.
The correlation criterion is WINDOWED (PREP-style): max |off-diag| corr per 1-s
window, channel bad when it fails in > `corr_bad_time_frac` of windows. WHY the
default is 10% and not PREP's 1%: PREP is calibrated on artifact-free scalp EEG.
cEEGrid sits over jaw/facial muscle, so healthy channels briefly decorrelate
during clenching/chewing; at 1% this flags 233/800 channels (29%), drops the
median score 75 -> 53, and pushes CTRL02+EXP02 out of the cohort. At 10% the
cohort and median score are UNCHANGED vs the old whole-recording criterion while
still catching the 19 intermittent-dropout channels it missed (e.g. EXP52, whose
entire right grid reads corr_bad_frac = 1.0). Empirics in
docs/QC_grade_bands_review.md. Presets scale: strict 5%, default 10%, lenient 20%.

Use *max* inter-channel correlation, not mean: ear-EEG channels are weakly correlated
with the contralateral ear, so a healthy channel's MEAN correlation is naturally low.

## Duplicate-channel detection runs on RAW, never on the filtered copy
`find_duplicate_channels` flags pairs at |r| >= 0.9999 as the SAME signal (one
is not real data) and scores the later one bad. It MUST use the unfiltered
signal: band-passing strips the shared DC/drift and relatively amplifies each
ADC's own noise, which collapses the separation. Measured here: duplicated
recordings sit at exactly 1.000000 raw vs <=0.997 healthy, but after 1-50 Hz
CTRL27 (duplicated) falls to 0.984 -- BELOW CTRL10 (healthy, 0.9996). Caught 7
recordings; EXP47/CTRL27/CTRL06 lose whole blocks. See docs/recording_rig_faults.md.

## R07 is excluded from the quality_score denominator (not from bads_combined)
`exclude_from_score: ['R07']` in every preset. R07 is a RIG fault (open circuit,
88% of recordings), so charging every participant 6.25 points for it is wrong.
It is still detected, still in `bad_channels`, and still dropped/masked
downstream -- only the SCORE ignores it, over `n_scored`=15. REMOVE this once
the hardware is repaired, else a regression stays hidden.

## Never re-reference before QC (and the pipeline never re-references at all)
`grep set_eeg_reference` over the tree returns nothing: QC, epoching and dataset
building all run on the RECORDED montage (REF = L6, single electrode, left
grid). Keep it that way. Measured: a common-average reference HIDES bad channels
because the average is contaminated by them and each bad channel then receives
the negated average, which looks like EEG. CTRL12 goes 66.7 -> a PERFECT 100
under CAR while the 5 channels it masks are railing for 44-49% of the recording.
EXP52's 8 zero channels all become the same negated average, so they correlate
perfectly with each other and pass. This is why PREP detects bad channels FIRST,
then estimates a robust average reference excluding them. BIPOLAR montages are no better, for the OPPOSITE reasons: contralateral
(L_i-R_i) HIDES a dead grid -- in EXP52 the right side is zeros so L-0=L
bit-identically, and 9/16 bad collapses to 1/8; within-grid (adjacent pairs)
OVER-flags -- perfect CTRL10 shows 8/14 bad because adjacent pads are 1-2cm
apart so their difference is ~5uV against 50-68uV referential SDs, and the
absolute thresholds misfire. Both also propagate faults (a pair is bad if
EITHER member is), whereas referential costs exactly one channel per bad
electrode. Re-referencing clean data is fine; re-referencing to DECIDE what is
clean is not. Details: docs/QC_methodology_review.md.

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

## docs/variants.md is GENERATED from conf/ -- never hand-edit it
`python -m synapse_qc.variants --write` regenerates it; `--check` exits 1 if it
has drifted from `conf/cohort/` + `conf/preprocessing/`. Run --check after
touching either config group. The "Built" table is scanned from the outputs
tree and is deliberately NOT part of the staleness comparison.

## THIS repo owns processing; the analysis repo only reads a finished pkl
No pipeline imports the analysis repo at run time any more. The published
preprocessing code is VENDORED verbatim into `synapse_qc/epoching.py`
(create_mne / read_data / events, from preprocessing/utils.py) and
`synapse_qc/process.py` (process_group / responses / clinical loaders, from
publication_analysis/preprocess.py), both from analysis-repo main @ e3aa291.
Full rationale, the reproduction numbers, and the re-vendoring procedure:
`docs/dataset_handoff.md`.

## TWO quality_check implementations, on purpose -- do not unify them
`epoching.quality_check` is the vendored LEGACY metric (mean-correlation on the
unfiltered signal). It is the default because `build_dataset cohort=published`
must mirror the published pkl, which was built with it. `qc_core.quality_check`
is this repo's ROBUST windowed metric, used by every QC entry point, and
`pair_video` REBINDS `epoching.quality_check` to it at run time so the
multimodal dataset gets the corrected metric. MEASURED: putting the robust
metric in build_dataset changes bad channels on 23/28 published subjects and
breaks reproduction. `build_dataset` deliberately does NOT rebind.

## build_dataset writes a DATED pkl for the analysis repo
Each run writes `epochs.pkl` (canonical) AND
`synapse_preprocessed_<YYYY-MM-DD>.pkl` (identical content) into the variant
dir. The analysis side points at the dated one, so provenance is in the
filename and successive builds do not overwrite each other. Schema unchanged --
same 16 top-level keys.

## The prior hand ratings are intentionally NOT in this repo
`../../synapse/participant_info.tsv` has manual Excellent/Good/Average/Bad ratings.
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
different places. WHY assets stay repo-relative: montage/event-map/`../../synapse`
are code+config, not data — they were deliberately NOT relocated, so only `data/`
and the `outputs/*` trees follow the base. To actually run the pipelines you must
either mount the server path (SSHFS) or run on the server; assets still resolve
from the repo checkout.

## Project layout / conventions
- ALL generated artifacts go under `<base>/outputs/` in the data tree
  (`$SYNAPSE_DATA_BASE`, e.g. `ub-polar:/data1/anarghya/synapse-data`) — the whole
  `outputs/` dir is gitignored, nothing generated lives in the repo. Layout:
  `qc/` (quality workbook + reports), `epochs/<cohort>__<preprocessing>/`
  (processed pkls, ~450 MB each), `multimodal/paired/` (stage-1 intermediate),
  `multimodal/final/<cohort>__<preprocessing>/` (training-ready variants),
  `logs/` (Hydra). Every location is defined ONCE in the `paths:` section of the
  relevant `conf/*.yaml` (`run_quality.py`/`spotcheck.py` read the same YAML via
  `synapse_qc.paths`) — relocate outputs by editing config, never code. Variant
  dirs are always `<cohort>__<preprocessing>` so both dimensions show in the
  path; each carries a `manifest.json` with git SHA + resolved config. The
  entry points warn loudly when `$SYNAPSE_DATA_BASE` is unset and they fall
  back to writing under the repo. See `outputs/README.md` in the data tree.
- `assets/` holds the canonical `ceegrid_montage_head.npz` + `global_event_id_map.pkl`.
  The published `create_mne` loads the montage by a RELATIVE path; `build_dataset.py` works
  around this by monkeypatching `utils.create_mne` to inject the absolute `assets/` path
  (so there is NO montage file required in CWD — don't re-add one).

## The clinical workbook comes from Box — re-pull it, do not hand-edit
`processing/02_PCData.xlsx` is a copy of
`box:AudioSight Study/01_Participant Data/02_PC Data .xlsx` (note the space in
the Box filename). The study coordinator updates it there, so refresh with
`rclone copy "box:AudioSight Study/01_Participant Data/02_PC Data .xlsx" .`
and rename. Last pulled 2026-08-28 (Box mtime 10:43): added EXP20's
demographics + audiometry (0 -> 75 fields) and 2 fields for EXP53, no existing
values changed. That closed the last gap -- all 43 cohort subjects now have
clinical data. Re-run finalize (or just `_write_clinical`) after a pull.

## Two clinical workbooks — the choice is per-cohort, on purpose
`02_PCData.xlsx` (here, updated 2026-07 by the study coordinator) is the NEWER
workbook: adds EXP44-47 + CTRL26-28, splits questionnaires per device, and moves
excluded participants to their own sheet. `../../synapse/02_PC Data.xlsx`
(2026-04) is the OLDER state the published pkl was built from. `build_dataset`
resolves `cohort.clinical_data` first (set only in `conf/cohort/published.yaml`,
pinning the old file so the published mirror reproduces exactly), then falls
back to `paths.clinical_data` (the new local file). Don't "fix" the published
cohort to use the new workbook — its whole point is bit-faithful reproduction.

## Dataset pipelines (built)
- `pipelines/build_dataset.py` (Hydra: `conf/cohort/` × `conf/preprocessing/`) builds
  processed variants; `pipelines/compare.py` diffs against the published pkl. It REUSES
  `../../synapse` preprocessing code (faithful mirror). See README "Processed-data variants".
  `inventory.discover()` is the shared ID→file layer.

## The multimodal (video+EEG) pipeline is two stages — detect-and-defer
The DL dataset is built in two Hydra pipelines, deliberately split so the SLOW,
one-time work (temporal EEG↔video alignment + video re-encoding) is separated from
the FAST, swappable channel-handling experiments:
- `pipelines/pair_video.py` → `outputs/multimodal/paired/`. Filters, epochs, and pairs EVERY
  boundary-valid trial with ALL 16 channels intact. QC runs for DETECTION ONLY: bad
  channels are recorded (in each `_epo.fif`'s `info['bads']` + a per-subject
  `*_channels.tsv`/`*_qc.json` sidecar) but NOT interpolated/dropped/zeroed, and NO
  epoch rejection happens. So no subject is dropped here on channel quality — that
  decision is deferred. `preprocessing.channel_strategy`/`epoch_rejection` are IGNORED
  by epoch mode (they still apply to legacy `marker` mode).
- `pipelines/finalize_dataset.py` (`conf/finalize.yaml`) → `outputs/multimodal/final/<cohort>__<preprocessing>/`.
  Applies `channel_strategy` (interpolate|zero_mask|drop|keep_all) + PTP `epoch_rejection`
  from the `preprocessing` group, emits a per-channel validity mask (`*_channel_mask.npy`,
  1=real / 0=interpolated/masked/dropped), and re-filters the alignment CSV to surviving
  pairs (video is never re-encoded — clips are referenced in place under `outputs/multimodal/paired`).
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
