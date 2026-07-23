# SYNAPSE — Data & Quality Analysis

Raw data and quality analysis for the SYNAPSE CEEGrid ear-EEG hyperacusis study.
The analysis/paper code lives separately in `../synapse`; this repo holds the
participant recordings and the tooling that reads and quality-checks them.

## Data location (relocatable)

By default the raw `data/` and generated `outputs/` trees live under the repo
root. They can be moved elsewhere (e.g. the lab server
`ub-polar:/data1/anarghya/synapse-data`, or an SSHFS mount of it) without
editing code — point the tooling at the base dir. The published copy of `data/`
+ `outputs/` lives at `/data1/anarghya/synapse-data`.

- **Env var (all entry points, incl. `run_quality.py` / `spotcheck.py`):**
  ```bash
  export SYNAPSE_DATA_BASE=/data1/anarghya/synapse-data   # holds data/ + outputs/
  # or point only the raw dir:  export SYNAPSE_DATA_ROOT=/path/to/data
  ```
- **Hydra pipelines (per-run override):**
  ```bash
  python -m pipelines.build_dataset   paths.root=/data1/anarghya/synapse-data
  python -m pipelines.pair_video      paths.root=/data1/anarghya/synapse-data
  python -m pipelines.finalize_dataset paths.root=/data1/anarghya/synapse-data
  # raw-only override: paths.data_root=/path/to/data
  ```
- **`run_quality.py`:** `--data-root /path/to/data` (else falls back to the env vars).

Precedence for the raw dir: `paths.data_root` / `--data-root` → `$SYNAPSE_DATA_ROOT`
→ `$SYNAPSE_DATA_BASE/data` → `<repo>/data`. Assets (`assets/` montage + event
map) and the sibling `../synapse` code stay repo-relative and are **not** relocated.

## Running the quality analysis

```bash
conda activate brain            # or: pip install -r requirements.txt
python run_quality.py --date $(date +%F)
python run_quality.py --preset strict          # stricter thresholds
python run_quality.py --only EXP13,CTRL09       # spot-check a subset
python -m synapse_qc.inventory                  # audit how each recording resolves
```

## How quality is scored

QC runs on the **raw** OpenBCI stream (`obci_eeg1`) — see "Two EEG streams" below.
The default **`robust`** method (filter-first; grounded in PREP/FASTER — see
`outputs/quality/QC_methodology_review.md`) first band-passes a copy to **1–50 Hz** so the
score does not depend on whether the input was already filtered, then flags a channel
as **bad** if any criterion trips:

| Criterion | Flags a channel when … | Default threshold |
|---|---|---|
| flat | amplitude below `flat_voltage` for > `bad_percent` of the time | 0.5 µV / 30 % |
| dead | SD below a floor | 0.3 µV |
| noisy | robust z (median/MAD) of log-variance is a high outlier | z > 3 |
| corr | **max** correlation with any other channel below `corr_low` (disconnected) | 0.40 |

High correlation (`n_highcorr`, possible electrode bridging ≥ 0.999) is **reported but
not scored**. `quality_score = 100 × (1 − n_bad / n_channels)`. Auto-grade: Excellent
≥95, Good 80–94, Average 60–79, Bad <60.

The original metric is available as `--method legacy` (criteria on the unfiltered
signal); it is kept only for comparison. The methodology review explains why it is not
valid on raw data (it flags common-mode DC drift as bad — e.g. CTRL09 scored 0 under
legacy, 81 under robust).

## Usable subjects / cohort

"Usable" is a threshold choice. Counts of participants with usable EEG:

| Definition | EXP | CTRL | Total |
|---|---|---|---|
| **Published cohort** (legacy QC, as-shipped in `../synapse`) | 18 | 10 | 28 |
| **Corrected, lenient bar** (robust QC, ≥4 good channels = the study's own rule) | **24** | **12** | **36** |
| Corrected, quality bar (robust QC, score ≥ 60 = ≥10 good channels) | 22 | 8–9 | 30–31 |

**Recommended cohort: 24 EXP / 12 CTRL** (robust QC at the study's own inclusion bar).

The published set is **18 EXP + 10 CTRL** (authoritative list in
`../synapse/processed_data/synapse_preprocessed.pkl`, keys `exp_subjects` /
`ctrl_subjects`). Its rule was the **legacy QC + "reject only if ≥12/16 channels bad"** —
`run_quality.py --method legacy` reproduces those 10 controls exactly. Differences under
the corrected metric:

- **CTRL 10 → 12:** CTRL09 and CTRL12 are recovered — legacy scored them 0 via the
  common-mode-drift artifact; they are actually usable (robust 81 and 75). They should
  arguably be added to the control group in any reanalysis.
- **EXP 18 → 24:** EXP08 and EXP10 are likewise rescued from the artifact; EXP20/31/45/46
  passed QC but were originally dropped for **non-QC reasons** (recruitment-batch/roster
  cutoff — the manual roster stops at EXP29), not signal quality.

**Hard-excluded either way (11):** EXP12, EXP14, CTRL11, CTRL13, CTRL14, CTRL15, CTRL16
(all 16 channels dead); EXP26, CTRL03 (no EEG stream); EXP44 (empty stream); EXP32
(Neurable — not OpenBCI-scorable).

> These are **whole-recording** counts. Per-task usability (PMT/LET/HLT/AST) will be lower
> for subjects missing a specific task and is a separate check (not yet implemented).

## Processed-data variants (model ingestion)

`pipelines/build_dataset.py` builds processed `Epochs` datasets as **cohort × preprocessing**
variants, using Hydra config groups. It reuses the *published* preprocessing code from
`../synapse` (event mapping → `create_mne` → per-task epochs → z-score PTP epoch rejection),
so a `preprocessing=published` build faithfully mirrors `synapse_preprocessed.pkl`.

```bash
python -m pipelines.build_dataset cohort=published preprocessing=published     # mirror
python -m pipelines.build_dataset --multirun preprocessing=drop,interpolate,zero_mask,keep_all
python -m pipelines.build_dataset cohort=usable preprocessing=interpolate
python -m pipelines.build_dataset cohort.exp='[EXP01,EXP13]' cohort.ctrl='[CTRL10]'  # ad-hoc
```
- `conf/cohort/` — participant-ID sets (`published` 18+10, `usable` 24+12, `all`); override with `cohort.exp=[...] cohort.ctrl=[...]`.
- `conf/preprocessing/` — variants for comparing channel handling: **`drop` / `interpolate` / `zero_mask` / `keep_all`** (the published mirror uses **`interpolate`** — verified against the pkl).
- Output: `outputs/processed/<variant>.pkl` (+ `<variant>.manifest.json` with cohort, params, file resolution, epoch counts, channel masks — the provenance record). **`outputs/processed/` files are large (~450 MB each)** — treat as build artifacts.

**Pkl schema** — the built pkl mirrors the **current `../synapse` `save_preprocessed` schema** so it is a **drop-in for the current analysis scripts** (`python -m publication_analysis input=outputs/processed/<variant>.pkl …`). The 16 top-level keys: `exp_epochs, ctrl_epochs, exp_subjects, ctrl_subjects, exp_quality, ctrl_quality, clinical_data, clinical_scores, demographics, responses, quality_report, channel_strategy, epoch_rejection_enabled, channel_masks, preprocessing_date, config`. Clinical/behavioural/report keys are built with the published builders (`load_clinical_data` / `extract_clinical_scores` / `extract_demographics` / `load_responses` / `generate_quality_report`) from `02_PC Data.xlsx` + the per-subject `*_responses.csv`. Provenance (`variant`, `cohort`) lives inside `config` and the `<variant>.manifest.json` sidecar. (This is a superset of the older `synapse_preprocessed.pkl`, which had only 11 of these keys — it predates `channel_masks`/`demographics`/`responses`/`channel_strategy`/`epoch_rejection_enabled`.) Nested notes: each `*_quality` dict is a superset of the published one (adds `ch_sd_uv`/`channel_mask`/`epoch_rejection` — harmless, only `quality_score` is read downstream); `clinical_scores` uses `HQ_Functional`/`HQ_Social` where the older pkl used `HQ_Fear`/`HQ_Sensitivity` (a relabel of the same two columns).

### Reproduction check vs the published pkl

`python -m pipelines.compare --variant published` diffs a build against
`../synapse/.../synapse_preprocessed.pkl` (aligning by `subject_id`; published order is
processing order, not sorted). Current result for the `published` mirror:

- **Cohort identical** (18 EXP / 10 CTRL).
- **24/28 subjects:** same bad channels and **bit-identical epoch data on every matched
  stimulus** — only the z-score rejection kept 1–2 fewer epochs/task (it's sensitive to
  tiny numerical differences). The signal pipeline reproduces exactly.
- **3/28 subjects** (EXP07, EXP13, CTRL10) differ in **channel QC**: the current `../synapse`
  `quality_check` flags slightly different bad channels than when the pkl was built (Jan 2026),
  changing interpolation on one channel (a few µV RMS).

So the rebuild is faithful; differences are small and fully explained (epoch-rejection
sensitivity + minor QC drift). Note CTRL01/02/03 are resolved from their `-old` folders
(renamed after the pkl was built; the published `exclude -old` discovery would now drop them).

## Multimodal pairing (video + EEG) — two stages

The DL dataset is built in **two Hydra pipelines**, deliberately split so the slow,
one-time alignment + video encoding is separated from the fast, swappable channel-handling
experiments. The alignment library lives in `synapse_qc/av_align.py`; files resolve through
`inventory` (XDF + the per-participant `.avi`).

### 1. `pipelines/pair_video.py` → `outputs/paired/` (slow, one-time)

Filters, epochs, and pairs **every** boundary-valid trial with **all 16 channels intact**.
QC runs for **detection only** — bad channels are recorded (in each `_epo.fif`'s
`info['bads']` + per-subject `*_channels.tsv` / `*_qc.json` sidecar) but **not**
interpolated/dropped/zeroed, and **no epoch rejection** happens. Nothing is dropped on
channel quality here (that is deferred to finalize), so a recording that would fail QC still
produces paired data.

```bash
python -m pipelines.pair_video                                   # usable cohort, epoch mode
python -m pipelines.pair_video video.mode=marker                 # legacy marker-to-marker clips
python -m pipelines.pair_video preprocessing.bandpass.low=2 preprocessing.notch_freq=-1   # notch<0 disables
python -m pipelines.pair_video cohort=published video.no_video=true   # EEG epochs only
```
- **`epoch` mode** (default): one stim-locked clip + one EEG epoch per trial, both windowed
  to `tasks.timings`, with a per-frame `*_frames.csv` sidecar (`t_rel_stim_s`, `t_lsl_s`) —
  the alignment key. Use `av_align.resample_frames_to_eeg` / `nearest_frame_for_eeg` to map
  frames onto the 125 Hz EEG grid; **never** use a nominal fps (the webcam rate is
  sub-nominal and dejittered). Applies stream/bandpass/notch/quality; **`channel_strategy`
  and `epoch_rejection` are ignored** (finalize's job).
- **`marker` mode**: legacy marker-to-marker segments + a single filtered `Raw.fif` (still
  honours `channel_strategy`).
- Output: `outputs/paired/<PID>/{eeg,video}/` + per-subject `*_alignment.csv` + a top-level
  `dataset_manifest.csv`. **Clips are large build artifacts** (`outputs/paired/` gitignored).
  A recording without `obci_eeg1` (e.g. Neurable-only) is a per-subject FAILED row, not a crash.

### 2. `pipelines/finalize_dataset.py` → `outputs/dataset/<name>/` (fast, swappable)

Applies `channel_strategy` + PTP `epoch_rejection` from the **same `conf/preprocessing/`
group** `build_dataset` uses, so finalized variants stay in lock-step. It emits a per-channel
**validity mask** (`*_channel_mask.npy`, `1`=real / `0`=interpolated/masked/dropped +
`*_channels.json`) and re-filters each `*_alignment.csv` to the surviving pairs — **video is
never re-encoded**, clips are referenced in place under `outputs/paired/`.

```bash
python -m pipelines.finalize_dataset                          # interpolate + z=3 (= old baked-in behaviour)
python -m pipelines.finalize_dataset preprocessing=zero_mask  # zero bad channels, keep 16 + mask
python -m pipelines.finalize_dataset preprocessing=drop       # drop bad channels (variable ch count)
python -m pipelines.finalize_dataset preprocessing=keep_all   # raw bad channels + mask
python -m pipelines.finalize_dataset preprocessing.epoch_rejection.enabled=false
```
- **Why two stages:** rejection PTP is computed over the **good channels only** (a noisy bad
  channel can't corrupt it — only possible because channel handling is decoupled);
  interpolation is irreversible, so pairing keeps raw channels + a mask and you can try
  masking vs interpolation without re-running the slow pair step. Build interpolate/zero_mask/
  drop side by side from a single pair run.
- An empty `cohort.exp` / `cohort.ctrl` list means **none** for that group unless
  `cohort.name=all` (then both groups auto-discover).

## Two EEG streams (important)

Most recordings contain **two** OpenBCI LSL streams:

- `obci_eeg1` — **RAW** (carries the electrode DC offset; always present). **Canonical QC input**, matching `../synapse`'s `parse_xdf`.
- `obci_eeg2` — **FILTERED** by the OpenBCI GUI: empirically a **~5–50 Hz band-pass + 60 Hz notch** (recovered from the stream spectra). Present in 37/47 recordings.

Because the `robust` method band-passes internally, the QC of the raw stream and of
the filtered stream **converge** (mean |Δ| ≈ 4 pts; was up to 100 under the legacy
metric). `score_filtered` is therefore a **convergence check**, not a separate verdict,
and `stream_note` flags any residual difference. (Under the old metric the two diverged
wildly — CTRL09 raw 0 vs filtered 100 — which is what motivated the redesign.)

## Devices (OpenBCI vs Neurable)

Two devices were used: **OpenBCI** (16-ch CEEGrid; the QC target) and **Neurable
MW75** (14-ch). The `device` column is the device of the *scored* recording;
`devices_present` lists every device a participant has data for. Neurable recordings
are **not scored** (the OpenBCI-tuned QC does not apply to a 14-ch headset). EXP10 has
both devices in *separate sessions* (we score its OpenBCI one; `devices_present` shows
both); EXP32 is Neurable-only. Device is detected from the **EEG stream name**, not the
folder name (EXP32's folder does not say "neurable").

## Per-participant resolution quirks

Handled in `synapse_qc/inventory.py`:
`-old`/`_old` folders are skipped unless they are the only session (CTRL01/02/03);
EXP10's `(Neurable)` folder is skipped in favour of its OpenBCI recording;
EXP44's EEG stream is empty; EXP26/CTRL03 have no EEG stream.
