# QC metric review: does the scoring work on raw *and* filtered EEG?

*Focused literature brief (deep-research, lit-review mode). AI-assisted research; all
citations verified against Semantic Scholar / source docs (DOIs below).*

## Bottom line

**No — the current metric is not valid on raw data, and is only partly valid on
filtered data, because two of its three criteria are computed on the unfiltered
signal.** Every established automated pipeline computes amplitude- and
correlation-based criteria on **high-pass-filtered, line-noise-removed** data, *for
the explicit reason* that thresholds are otherwise uncalibrated. The fix is to make
the metric **filtering-invariant**: apply a fixed internal pre-filter (≈1 Hz
high-pass + 60 Hz notch) inside `quality_check` before computing *all* criteria, and
replace the fixed correlation bounds with the standard *low-correlation* /
robust-z formulation. Then raw (`obci_eeg1`) and filtered (`obci_eeg2`) inputs
converge to nearly the same score, and the CTRL09-type false-negative disappears.

## What the established pipelines actually do

**PREP** (the de-facto standard for automated bad-channel detection) **detrends or
high-pass filters at 1 Hz and removes line noise *before* detecting bad channels or
referencing, "in order to properly calibrate the thresholds"** (Bigdely-Shamlo et
al., 2015; PREP/EEG-Clean-Tools docs). Its criteria are all **data-driven robust
z-scores**, not fixed µV:
- extreme amplitude: robust channel-deviation **z > 5**
- high-frequency noise: noise-to-signal **z > 5**
- **correlation: a channel is bad if it correlates *too little* with the others**
  (corr < **0.4** in > 1% of 1-s windows). PREP has **no "correlation too high = bad"
  rule.** RANSAC predictability is a further criterion (needs electrode positions).

**FASTER** (Nolan et al., 2010) flags channels by **|z| > 3** on three per-channel
parameters — mean inter-channel **correlation**, variance, and Hurst exponent —
computed on **filtered** data; again data-driven, and again *low* mean correlation is
the bad-channel signal.

**autoreject** (Jas et al., 2017) operates on **filtered, epoched** data and learns
peak-to-peak thresholds by cross-validation rather than fixing them a priori.

**Three consistent lessons:** (1) filter first, score second; (2) thresholds are
data-driven/robust, not hard-coded µV; (3) the correlation criterion detects
**under-correlated** (disconnected/noisy) channels — bridged or common-mode-dominated
channels are *over*-correlated, a different problem (electrode bridging), not what a
single high bound should police.

## Mapping this onto the current `quality_check`

| Criterion | Computed on | Verdict |
|---|---|---|
| dead/variance (SD floor on a **1 Hz high-passed copy**) | filtered copy ✓ | **Sound** — already matches PREP's "filter-then-threshold". Roughly filtering-invariant. |
| flat (`annotate_amplitude`, µV) on the raw stream | raw ✗ | Fixed µV on DC-coupled data; a large DC offset is *not* flat. Should run on the high-passed copy and/or use a robust scale. |
| correlation, bounds **(0.15, 0.85)** on **unfiltered** data | raw ✗ | **The core problem.** On raw ear-EEG, common-mode DC drift drives mean inter-channel corr → ~0.97, tripping the 0.85 bound for *every* channel (CTRL09: raw 0, filtered 100). The "high = bad" bound and fixed values are both non-standard. |

The code comment that the (0.15, 0.85) bounds are "calibrated for the shared DC drift
of unfiltered ear-EEG" is exactly the move the literature warns against: PREP removes
the drift so thresholds *can* be calibrated, rather than calibrating around it. So the
metric does not transfer between streams — on raw it false-flags drift as bad
channels; on filtered the 0.15 *low* bound can false-flag genuinely independent
ear-EEG channels.

## Sub-questions, answered

1. **Raw or filtered for correlation?** Always filtered (≥1 Hz HP) + line-noise
   removed. Running a correlation criterion on DC-coupled raw data is not appropriate
   by any of the standard pipelines.
2. **Do µV amplitude/SD thresholds scale between raw and filtered?** No — they are
   only meaningful after high-pass. Best practice replaces absolute µV with robust
   z-scores (FASTER |z|>3; PREP deviation z>5), with a small absolute floor as a
   dead-channel safety net.
3. **Fixed vs data-driven correlation bound?** Prefer data-driven: PREP's
   low-correlation-in-windows (<0.4) or a robust-z on each channel's mean correlation.
   A single fixed (low, high) pair is not defensible across both stream types.
4. **Ear-EEG / cEEGrid specifics.** cEEGrid signals have **lower amplitude and
   different characteristics than scalp EEG** (Debener et al., 2015; Sterr et al.,
   2018), so absolute scalp thresholds must be re-scaled — another argument for
   robust/relative thresholds. There is **no published, validated automated
   bad-channel threshold set specific to cEEGrid**; ear-EEG QC in the literature is
   mostly manual/visual or task-performance-based. (Limitation: the recommendation
   adapts scalp-EEG standards; it is not a cEEGrid-validated recipe.)
5. **Recommendation: (c) redesign to be filtering-invariant, built on (a).**

## Recommended redesign (engineering)

Inside `quality_check`, before computing any criterion:

1. **Normalise the input:** copy the raw, apply **1 Hz high-pass + 60 Hz notch**
   (skip the notch if already filtered — detect via residual 60 Hz power, or just
   re-applying is harmless). Compute *all* criteria on this normalised copy. This
   single step makes raw vs filtered inputs converge.
2. **Dead/flat:** keep the SD-floor-on-HP-copy logic (already correct); compute the
   flat check on the same normalised copy.
3. **Correlation → low-correlation, data-driven:** flag a channel whose mean (or
   windowed-max) correlation with the others is **low** — either PREP-style (< ~0.4 in
   >1% of 1-s windows) or robust-z (median ± k·MAD). **Drop the high bound** as a
   bad-channel rule; if bridging detection is wanted, treat it as a separate,
   explicitly-labelled flag, not part of the score.
4. **Amplitude/variance → robust z** (|z|>3 on log-variance across channels) plus the
   absolute dead floor.
5. **Keep presets as scale parameters only**, not as per-stream regimes — there should
   be one metric, applied to one normalised signal.

Expected effect: CTRL09 raw and filtered both score ~clean; EXP13 raw stays clean and
its corrupted filtered stream is still caught (by low-correlation, correctly). The
`score_filtered` cross-check column becomes redundant once the metric is
filtering-invariant, though it is worth keeping for one validation run to confirm
convergence.


## Referencing: QC must run on the RECORDED montage, never after re-referencing

The pipeline does not re-reference anywhere — `grep set_eeg_reference` over the
whole tree returns nothing — so QC, epoching and dataset building all operate on
the recorded referential montage (REF = L6, a single electrode on the left
grid). That is deliberate, and it matters more than it looks.

**Re-referencing to a common average (CAR) systematically HIDES bad channels.**
Measured directly, referential vs CAR on the same recordings:

| Recording | referential | after CAR | channels CAR hides |
|---|---|---|---|
| CTRL12 | 66.7 (6 bad) | **100.0 (1 bad)** | L01, L02, L08, R02, R04 |
| CTRL06 | 40.0 (10 bad) | 60.0 (6 bad) | L08, L09, R04, R07 |
| EXP43 | 93.3 (2 bad) | 86.7 | R07 (the railed channel) |
| EXP01 | 86.7 (3 bad) | 86.7 | L07, R07 |
| EXP52 | 46.7 (9 bad) | 46.7 | L01 |

CTRL12 is the clearest case: under CAR it scores a **perfect 100**, yet the five
channels CAR masks are railing at the ADC limit for **44-49 % of the recording**
(L01 43.7 %, L02 49.1 %, R02 48.2 %, R04 49.3 %). That is a false pass on a
recording that is genuinely half-broken.

The mechanism is the standard average-reference contamination problem, in both
directions at once:

1. The average is computed *including* the bad channels, so their railed or dead
   content is injected into every good channel.
2. Each bad channel then has that average subtracted, so a dead or constant
   channel becomes `constant - mean(others)` = the negated average — which looks
   like plausible EEG and no longer trips the flat/dead criteria.

EXP52 shows (2) starkly: its 8 zero-valued right channels all become the *same*
negated average, so they end up perfectly correlated with each other and sail
through the correlation criterion (mean `corr_bad_frac` 0.558 -> 0.030).

This is exactly why **PREP detects bad channels first and only then estimates a
*robust* average reference** with those channels excluded, iterating. Referencing
before detection inverts the logic.

**Separately, CAR is questionable for cEEGrid at all.** The average-reference
approximation assumes electrodes sample a closed surface so their mean
approximates a neutral potential. Sixteen electrodes in two tight clusters
around the ears do not. The ear-EEG literature accordingly reads responses from
**bipolar derivations** (contralateral, or within-grid pairs such as R2-R7),
not from CAR.

**Practical rule:** keep QC on the recorded montage. If a downstream *analysis*
wants a different reference, apply it after bad channels have been dropped,
interpolated or masked — which is what `finalize_dataset`'s channel strategies
already produce.

## References

- Bigdely-Shamlo, N., Mullen, T., Kothe, C., Su, K.-M., & Robbins, K. (2015). The PREP
  pipeline: standardized preprocessing for large-scale EEG analysis. *Frontiers in
  Neuroinformatics, 9*, 16. https://doi.org/10.3389/fninf.2015.00016
- Nolan, H., Whelan, R., & Reilly, R. B. (2010). FASTER: Fully Automated Statistical
  Thresholding for EEG artifact Rejection. *Journal of Neuroscience Methods, 192*(1),
  152–162. https://doi.org/10.1016/j.jneumeth.2010.07.015
- Jas, M., Engemann, D. A., Bekhti, Y., Raimondo, F., & Gramfort, A. (2017).
  Autoreject: Automated artifact rejection for MEG and EEG data. *NeuroImage, 159*,
  417–429. https://doi.org/10.1016/j.neuroimage.2017.06.030
- Debener, S., Emkes, R., De Vos, M., & Bleichner, M. (2015). Unobtrusive ambulatory
  EEG using a smartphone and flexible printed electrodes around the ear. *Scientific
  Reports, 5*, 16743. https://doi.org/10.1038/srep16743
- Sterr, A., Ebajemito, J. K., Mikkelsen, K. B., et al. (2018). Sleep EEG derived from
  behind-the-ear electrodes (cEEGrid) compared to standard PSG: A proof of concept
  study. *Frontiers in Human Neuroscience, 12*, 452. https://doi.org/10.3389/fnhum.2018.00452
- PREP / EEG-Clean-Tools documentation: http://vislab.github.io/EEG-Clean-Tools/ ·
  pyprep `NoisyChannels`: https://pyprep.readthedocs.io/
