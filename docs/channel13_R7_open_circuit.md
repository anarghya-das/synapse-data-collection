# Channel 13 (R7) open-circuit fault — diagnosis and repair

**Status:** open, not yet repaired. **Affects:** OpenBCI recordings from
2025-02-27 onward. **Owner:** whoever next has the rig on the bench.

The right-ear cEEGrid electrode **R7** — OpenBCI **channel 13**, the Daisy
board's 5th input — is electrically disconnected in most sessions. This is a
mechanical fault in the recording rig, not a data-analysis artefact and not a
problem with the right hemisphere of the montage.

---

## 1. The evidence

Found while auditing per-channel QC failure rates across all 54 participants
(`outputs/qc/quality_results.xlsx`).

**It is not random.** Failure rates differ strongly by electrode position
(chi-square = 95.6, p < 0.0001), and one channel dominates:

| Position | Failure rate (43 live recordings) |
|---|---|
| **R7** | **88.4 %** (38/43) |
| R1 | 34.9 % |
| L7 | 32.6 % |
| … | … |
| L9 | 4.7 % |

**It is a hard rail, not a weak signal.** In the failing sessions channel 13
reads a *single constant value for every sample*: **-187500.0156 uV**. That is
-0.1875 V, exactly the ADS1299 negative full-scale rail at gain 24
(+/- Vref/gain = +/- 4.5/24 = +/- 187.5 mV), matching to the LSB. An ADS1299
input pinned at full scale is the signature of **nothing connected to it** —
input bias current charges the floating pin until the converter saturates.

> Note for anyone re-deriving this: the QC workbook reports channel 13's SD as
> `0.0000` in these sessions. That is the *post-band-pass* SD — a constant DC
> value filters to zero variance. Do not read it as "the channel reads zero";
> the raw value is a rail. This distinction is what separates an **open**
> circuit (rail) from a **short** to reference (true zero), and it inverts the
> diagnosis.

**The amplifier channel itself is fine.** In the periods when it does work,
channel 13 records normally — e.g. EXP47 channel 13 SD 8260 uV versus its
neighbour channel 12 at 7165 uV. So the ADS1299 input and the firmware are
healthy; only the connection to it fails.

**It is intermittent in month-long blocks**, which is why a mechanical cause is
likely rather than a per-session gel/prep mistake:

| Period | Channel 13 behaviour |
|---|---|
| 2025-02 .. 2025-06 | railed (open) |
| 2025-06 .. 2025-09 | live, often very noisy |
| 2025-09 .. 2026-02 | railed (open) |
| 2026-06 .. 2026-08 | mixed |

## 2. What was ruled out, and why

- **Not proximity to the reference.** REF is R4a and GND/BIAS is R4b (both on
  the right grid, per the [openbci-ceegrids](https://github.com/MKnierim/openbci-ceegrids)
  reference design). **R5 is the immediate neighbour of those pads and is
  completely healthy** (median SD 10.9 uV, 21 % bad). R7 sits three positions
  further away. Electrical proximity to REF/GND does not explain it.
- **Not the reference electrode.** All 16 channels reference to R4a; if REF
  were compromised every channel would degrade together. The other 15 do not.
- **Not a solder bridge / short.** A short to REF or a disabled channel yields
  a value at or near *zero*. This channel rails. (An earlier draft of this
  analysis proposed a bridge at the edge-card socket; the raw-sample evidence
  above supersedes it.)
- **Not gel.** A gel-starved electrode gives high impedance and a noisy trace,
  not full-scale saturation for an entire recording.
- **Not a channel-label mix-up.** The pipeline's `CEEGRID_CH_LABELS` matches the
  reference design's mapping exactly — Cyton ch 1-8 = L1,L2,L4,L5,L7,L8,L9,L10
  and Daisy ch 9-16 = R1,R2,R4,R5,R7,R8,R9,R10 — so channel 13 really is R7.

**Conclusion: an open circuit somewhere between the R7 pad and the Daisy's
channel-5 input.**

## 3. Impact on the collected data — the right side is usable

Excluding channel 13, the right grid is statistically indistinguishable from
the left, and carries slightly *more* signal:

| Measure | Left grid | Right grid | p |
|---|---|---|---|
| Bad-channel rate, **including** ch13 | 18.6 % | 30.5 % | 0.002 |
| Bad-channel rate, **excluding** ch13 | 18.6 % | **22.3 %** | **0.86** |
| Median channel SD | 10.9 uV | **13.0 uV** | 0.06 |

The entire apparent "right ear problem" was this one input. **7 of the 8
right-grid electrodes are good and those recordings are usable.** ADS1299
channels are independent, so a railed channel does not contaminate its
neighbours — which the table above confirms empirically.

Two separate incidents, not caused by this fault:

- **CTRL01 (2025-02-27) and CTRL02 (2025-02-28)** — whole right grid dead, the
  first two sessions of the study, consecutive days. Reads as a setup learning
  curve.
- **EXP52 (2026-08-25)** — whole right grid reads literal `0.0` on every right
  channel (not a rail), i.e. the Daisy side not connected at all. Its own
  incident; investigate separately since it is the most recent recording.

## 4. Diagnostic procedure

**Safety:** battery power only, never mains-tethered. Never put a multimeter on
electrodes attached to a person. Do all continuity testing with the grid off the
participant and the board powered down.

The path being bisected:

```
R7 pad -> cEEGrid flex tail -> mini edge card socket -> adapter PCB trace
       -> jumper wire -> Daisy channel-5 pin (OpenBCI channel 13)
```

Verify pin numbering against your board's silkscreen before heating anything;
channel 13 is the Daisy's 5th input, but confirm physically.

### Step 1 — Rule out software (2 min)
In the OpenBCI GUI confirm channel 13 is enabled and gain is 24 (consistent with
the +/-187.5 mV rail measured). A *disabled* channel reads flat zero, not a
rail, so this is expected to come back clean — eliminate it anyway.

### Step 2 — Wiggle test (highest yield for an intermittent open)
Gel the grid on a test surface (or forearm), stream the GUI time-series view,
and gently flex — one at a time — the flex tail where it enters the socket, the
jumper wire, and the socket body, watching channel 13. If the trace pops between
railed and live at a specific point, that is the fault; skip to Step 5.

### Step 3 — Impedance check
Run the GUI impedance measurement. Channel 13 should read open / off-scale while
the others sit in the 10-50 kOhm range the reference design cites. Record the
numbers so they can be compared after repair.

### Step 4 — Swap test (partitions grid vs. rig, no soldering)
Swap the two cEEGrids — right-ear grid into the left socket and vice versa.

| Result | Conclusion |
|---|---|
| Fault **follows the grid** (appears on a Cyton channel) | The cEEGrid is damaged: bad R7 pad or broken flex trace |
| Fault **stays on channel 13** | The adapter, socket, jumper or Daisy pin is at fault |

Given the fault persists across many participants and presumably several grids,
the second outcome is expected — confirm rather than assume.

### Step 5 — Continuity test to localise the open
Multimeter in continuity mode, board powered off. Probe hop by hop:

| From | To | Expect |
|---|---|---|
| R7 pad on the grid | corresponding socket contact | < a few Ohm |
| socket contact | adapter PCB pad/via | < a few Ohm |
| adapter pad | far end of the jumper wire | < a few Ohm |
| jumper end | Daisy channel-5 header pin | < a few Ohm |

Whichever hop reads open is the fault. Also probe R7's pin **against its
neighbours and against SRB/BIAS** — there should be *no* continuity; if there
is, there is a bridge as well as an open.

## 5. Repair

- **Open at the socket or PCB** — reflow the joint. The reference design's
  advice to remove every second pin of the edge-card socket before soldering
  lowers bridging risk but leaves joints mechanically fragile, which is a
  plausible origin here. Add strain relief (hot glue or epoxy) at the socket
  afterwards; this is the point that flexes in use.
- **Open in the jumper** — replace the wire, routing it *below* the Cyton board
  as the reference design specifies.
- **Damaged grid** — retire that cEEGrid. Review the cleaning routine: the
  reference design warns against rubbing the pads or using chemicals on grids
  intended for reuse.

## 6. Verify the fix

Record 2-3 minutes with the grid on, then from `processing/`:

```bash
python run_quality.py --only <TEST_ID> --data-root /data1/anarghya/synapse-data/data
python spotcheck.py <TEST_ID>
```

Channel 13 should be absent from the bad-channel list with an SD in the same
range as its neighbours (roughly 8-17 uV in the healthy recordings) — neither
near zero nor in the hundreds.

## 7. Follow-up code changes (not yet done)

- **Absolute rail check in QC.** EXP10's channel 13 passed QC at 1197 uV SD,
  which is plainly railed. The robust-z `noisy` criterion missed it because z is
  computed against that recording's own median/MAD, and a heterogeneous
  recording widens the MAD enough to hide an extreme outlier. An absolute upper
  amplitude bound alongside the relative one would catch this class of fault.
- **Pre-flight rail check at collection time.** `eeg_quality/recording_checks.py`
  runs before LabRecorder starts and is deliberately numpy-only; a "no channel
  sitting at +/- full scale" test fits it cleanly and would have caught this on
  day one instead of eighteen months later.
- **Consider excluding channel 13 from the quality-score denominator** while the
  fault is live. `quality_score = 100 x (1 - n_bad/16)` currently charges every
  subject 6.25 points for a rig fault; scoring over the 15 working channels
  raises the mean score of affected recordings from 73.8 to 78.7.

## References

- Reference design: <https://github.com/MKnierim/openbci-ceegrids>
- Knierim, M. T., Schemmer, M., & Bauer, N. (2022). A simplified design of a
  cEEGrid ear-electrode adapter for the OpenBCI biosensing platform.
  *HardwareX, 12*, e00357. <https://doi.org/10.1016/j.ohx.2022.e00357>
- Per-channel QC data: `outputs/qc/quality_results.xlsx` (Per-Channel sheet)
- Related: `processing/docs/QC_grade_bands_review.md`
