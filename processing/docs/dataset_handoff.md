# Dataset handoff: processing here, analysis there

**Rule: this repo owns processing. The analysis repo only reads a finished
pickle.** No pipeline in this repo imports the analysis repo at runtime.

## Why

Processing used to be imported live from `synapse-analysis` at run time, which
made every build depend on which branch that checkout happened to be on. That
bit us concretely: a checkout predating `channel_strategy='keep_all'` broke
`pair_video` outright, and the branch also carried a changed `quality_check`
that would silently have altered bad-channel detection. A dataset build should
not depend on a sibling repo's working tree.

## What was vendored

Copied **verbatim** from `synapse-analysis` (branch `main`, commit `e3aa291`,
2026-08-28) so the published mirror still reproduces — not rewritten:

| Module | From | Contains |
|---|---|---|
| `synapse_qc/epoching.py` | `preprocessing/utils.py` | `create_mne`, `read_data`, `create_mappings`, `create_events`, `select_event_ids`, `contralateral_reference`, HED helpers, **and the LEGACY `quality_check`** |
| `synapse_qc/process.py` | `publication_analysis/preprocess.py` | `process_subject`, `process_group`, `load_responses`, `generate_quality_report`, and the clinical loaders in the pkl's nested shape |

Deliberately **not** copied: `create_raw`, `closest_points_vector`, `parse_xdf`
— this repo already has its own in `synapse_qc/qc_core.py` (verified equivalent,
differing only in comments and constant extraction).

One function is **adapted, not verbatim**: `_resolve_path`, because upstream
resolves against the analysis repo root and here it must resolve against this
one (absolute paths pass through untouched).

## The two quality_check implementations — do not unify them

This is the subtlety most likely to be "cleaned up" by mistake:

- **`epoching.quality_check`** — the vendored **LEGACY** metric (mean-correlation
  bounds on the unfiltered signal). Default for `build_dataset`, because the
  published pkl was built with it.
- **`qc_core.quality_check`** — this repo's **ROBUST**, windowed,
  filtering-invariant metric. Used by every QC entry point, and `pair_video`
  rebinds `epoching.quality_check` to it at run time so the multimodal dataset
  gets the corrected metric.

Swapping the legacy one for the robust one in `build_dataset` changes the
bad-channel sets on **23 of 28** published subjects and breaks reproduction.
Measured, not assumed.

## Reproduction check

`pipelines/compare.py` is the regression test. Against the original
`synapse_preprocessed.pkl`, the vendored build gives:

- **matched-stimulus epoch data identical (≤0.01 µV) for every shared epoch**, both groups
- 23/28 bit-identical (same bads, same epoch counts, same data)
- 2/28 identical channels and data, differing only in how many epochs the
  z-score rejection kept
- **3/28 differ in channel QC** — EXP07, EXP13, CTRL10

That 3/28 is the *pre-existing* baseline from before vendoring: upstream's
`quality_check` drifted after the pkl was built. Vendoring introduced no new
divergence.

Re-run after any re-vendor:

```bash
python -m pipelines.build_dataset cohort=published preprocessing=published
python -m pipelines.compare --variant published__published
```

`compare.py` finds the reference pkl automatically if the analysis repo is
present, or takes `--ref /path/to/synapse_preprocessed.pkl`. It is the only
thing here that looks for that repo, and it is optional.

## What the analysis repo consumes

Every `build_dataset` run writes two identical pickles into the variant dir:

```
processed/dataset/eeg_only/<variant>/
  epochs.pkl                          # canonical, for this repo's tooling
  synapse_preprocessed_<YYYY-MM-DD>.pkl   # <- the analysis repo reads this
  manifest.json                       # cohort, params, git SHA, resolved config
```

The date-stamped name is what the analysis side should point at, so provenance
is visible in the filename and successive builds do not overwrite each other.
`manifest.json` records `analysis_pkl` alongside `pkl`.

The schema is unchanged — the same 16 top-level keys the analysis scripts
already read (`exp_epochs`, `ctrl_epochs`, `exp_subjects`, …, `channel_masks`,
`config`). No analysis-side change is needed beyond the path.

## Caveat on `cohort=published`

The **signal** reproduces the paper exactly (above). The `clinical_*` keys will
not: they are built from the current workbook, which has grown since the paper
(EXP20's demographics were only added 2026-08-28). Point
`cohort.clinical_data` at an older workbook copy if you need those to match too.

## Re-vendoring

If upstream's preprocessing changes and you want it:

1. Re-extract the same function lists into `epoching.py` / `process.py`.
2. Keep the two-`quality_check` split and the adapted `_resolve_path`.
3. Re-run the reproduction check above and update the numbers here.
