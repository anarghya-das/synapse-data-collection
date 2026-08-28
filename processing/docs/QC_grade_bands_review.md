# Are the QC grade bands defensible? (literature check)

Companion to `QC_methodology_review.md`, which validated the *criteria*
(flat/dead/noisy/corr). This one checks the **score** and the
**Excellent/Good/Average/Bad bands** against published practice.

## What the grades actually mean

`quality_score = 100 × (1 − n_bad / 16)`, so with 16 channels the score is
quantized in steps of 6.25. The bands in `synapse_qc/excel.py` therefore reduce
to a bad-channel count:

| Grade | Band | = bad channels | = % bad |
|---|---|---|---|
| Excellent | ≥ 95 | 0 | 0 % |
| Good | 80–94 | 1–3 | 6–19 % |
| Average | 60–79 | 4–6 | 25–38 % |
| Bad | < 60 | ≥ 7 | ≥ 44 % |

Observed distribution (n=47 scored): Excellent 3, Good 15, Average 15, Bad 14
(7 of the 14 are all-16-dead recordings scoring 0). Median 75, mean 63.8.

## Verdict

**The metric is well-precedented; the band cutoffs are a local convention.**

1. **"Percent good channels" is a recognised standardised metric.** HAPPE
   (Gabard-Durnam et al., 2018) reports it as a core data-quality output,
   explicitly so that "users wishing to limit the amount of interpolated data in
   further analyses can easily identify files for removal". So scoring a
   recording by surviving-channel fraction is legitimate.

2. **But HAPPE publishes a reference *distribution*, not fixed grade bands.**
   There is no literature standard for Excellent/Good/Average/Bad EEG grading.
   The 95/80/60 cutoffs here mirror the study's own pre-existing manual ratings
   in `../../synapse/participant_info.tsv` (so auto and hand grades stay
   comparable) — that is their real provenance, not a published rubric. They
   happen to land on clean channel counts (0 / 1–3 / 4–6 / ≥7), which is tidier
   than the round numbers suggest.

3. **The bands are lenient relative to scalp-EEG interpolation practice.**
   Auger et al. (2022), independently evaluating HAPPE, treat interpolating
   >5 % of channels as biasing ("our data contains 33 channels so interpolation
   of more than one electrode would be over 5 % of the data and interpolation
   would bias the data"). Hardmeier et al. (2014) report a median of 1
   interpolated channel out of 214. Kayser & Tenke interpolate only when
   <25 % of channels are artifactual, rejecting otherwise. Against that,
   SYNAPSE "Good" already spans 6–19 % bad and "Average" 25–38 % — an
   "Average" recording sits at or past the point where scalp studies stop
   interpolating and start rejecting.

   Two caveats pull in opposite directions, and neither is resolved in the
   literature for cEEGrid:
   - **Stricter is arguable:** with 16 channels each one carries far more unique
     information than 1 of 128, and cEEGrid electrodes sit in two tight
     clusters, so spherical-spline interpolation across ears rests on much
     weaker spatial sampling than the dense-array case those limits assume.
   - **More lenient is arguable:** ear-EEG is intrinsically lower-yield, and
     holding it to scalp channel-yield standards would reject most of the
     dataset. The pipeline's `zero_mask`/`keep_all` + validity-mask options are
     the honest alternative to interpolating a quarter of the montage.

4. **The study's inclusion rule is much more lenient than the grades.** Cohort
   membership uses "≥4 good channels" (i.e. up to 75 % bad), which is far
   beyond any published practice found. This needs explicit justification in
   the paper — it is a defensible choice for a low-yield wearable modality, but
   it is not a convention anyone else follows.

## Two implementation gaps vs the cited standards

- **Correlation is not windowed.** PREP flags a channel when its correlation is
  below ~0.4 **in >1 % of 1-second windows**; `qc_core.quality_check` computes a
  single max off-diagonal correlation over the *whole* recording. An electrode
  that detaches partway through can keep a whole-recording correlation above
  0.4 and pass. `QC_methodology_review.md` recommended a "windowed-max" but the
  implementation is unwindowed. **This is the one substantive fix.**
- **The noisy criterion is one-sided** (`rz > 3`) where FASTER uses `|z| > 3`.
  Defensible — the low tail is already covered by the SD floor.

## What the score does not measure

HAPPE reports a *panel* (percent good channels, percent ICs rejected, percent
variance retained, segments retained). `quality_score` is one axis: channel
count. It says nothing about how clean the *surviving* channels are — a
recording whose 16 channels are all marginal-but-unflagged scores 100. The
repo already warns about this (`CLAUDE.md`: "quality_score is '% channels
surviving QC', not signal fidelity"); the literature supports that caution.
Pairing the grade with a second axis (epoch-rejection rate from
`finalize_dataset`, or SNR of retained channels) would make it much more
informative.

## References

- Gabard-Durnam, L. J., Mendez Leal, A. S., Wilkinson, C. L., & Levin, A. R. (2018).
  The Harvard Automated Processing Pipeline for Electroencephalography (HAPPE).
  *Frontiers in Neuroscience, 12*, 97. https://doi.org/10.3389/fnins.2018.00097
- Auger, E., et al. (2022). Independent evaluation of the Harvard Automated
  Processing Pipeline for Electroencephalography 1.0 using multi-site EEG data
  from children with Fragile X Syndrome. *Journal of Neuroscience Methods, 371*,
  109501. https://doi.org/10.1016/j.jneumeth.2022.109501
- Hardmeier, M., et al. (2014). Reproducibility of functional connectivity and
  graph measures based on the phase lag index (PLI) and weighted phase lag index
  (wPLI) derived from high resolution EEG. *PLOS ONE, 9*(10), e108648.
  https://doi.org/10.1371/journal.pone.0108648
- Kayser, J., & Tenke, C. E. (2015). Issues and considerations for using the scalp
  surface Laplacian in EEG/ERP research: A tutorial review. *International Journal
  of Psychophysiology, 97*(3), 189–209. https://doi.org/10.1016/j.ijpsycho.2015.04.012
- Bigdely-Shamlo, N., et al. (2015). The PREP pipeline. *Frontiers in
  Neuroinformatics, 9*, 16. https://doi.org/10.3389/fninf.2015.00016
- Nolan, H., Whelan, R., & Reilly, R. B. (2010). FASTER. *Journal of Neuroscience
  Methods, 192*(1), 152–162. https://doi.org/10.1016/j.jneumeth.2010.07.015

Sources located via PubMed and scite.
