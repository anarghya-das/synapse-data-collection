# SYNAPSE — Data & Quality Analysis

Raw data and quality analysis for the SYNAPSE CEEGrid ear-EEG hyperacusis study.
The analysis/paper code lives separately in `../synapse`; this repo holds the
participant recordings and the tooling that reads and quality-checks them.

## Layout

```
data/                    # raw recordings (gitignored: large)
  01_Control/CTRLnn/sub-XXXXXX/sub-XXXXXX_task-hearing_run-001.xdf  (+ responses.csv, .avi, audiogram PDFs)
  02_Experimental/EXPnn/sub-XXXXXX/...

synapse_qc/              # quality-analysis package
  qc_core.py             # vendored CEEGrid QC routines (from ../synapse/preprocessing/utils.py)
  inventory.py           # participant discovery + recording resolution (shared layout layer)
  excel.py               # workbook writer
  manual.py              # loader for the prior hand ratings (used only by the later comparison step)
run_quality.py           # QC driver: QC every participant -> Excel + per-participant reports
spotcheck.py             # plot/audit a participant's channels against the QC flags

pipelines/               # dataset-builder package (cohort x preprocessing variants)
  build_dataset.py       # build a processed-data variant; compare.py: diff vs the published pkl
conf/                    # Hydra config groups: cohort/ (participant IDs), preprocessing/ (variants)
assets/                  # ceegrid_montage_head.npz + global_event_id_map.pkl (canonical)

outputs/                 # ALL generated artifacts
  quality/               #   quality_results.xlsx (Summary/Per-Channel/Legend), reports/<PID>.txt,
                         #   spotcheck/<PID>.png, QC_methodology_review.md
  processed/             #   <variant>.pkl (gitignored, ~450 MB) + <variant>.manifest.json
  runs/                  #   Hydra per-run logs (gitignored)
```

47 participants (29 EXP, 18 CTRL). The *published* study used a subset
(18 EXP + 10 CTRL); this folder is the full raw collection, and the QC here is
one input to deciding inclusion.

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
