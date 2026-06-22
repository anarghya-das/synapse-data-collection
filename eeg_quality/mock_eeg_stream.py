#!/usr/bin/env python3
"""Fake ``obci_eeg1`` LSL stream for testing the recording quality gate.

Lets you exercise ``recording_checks.assert_eeg_quality`` / the PsychoPy
pre-flight gate WITHOUT the OpenBCI hardware, by broadcasting a synthetic
16-channel EEG stream with a chosen signal quality:

    good       correlated, physiological-amplitude signal  -> gate PASSES
    flat       near-zero (dead/disconnected electrodes)     -> gate FAILS
    railed     pinned at the ADC rail                        -> gate FAILS
    saturated  huge independent noise on every channel       -> gate FAILS

The "good" mode mimics real EEG: a shared brain/reference component (so channels
correlate, which the QC's correlation criterion requires) plus per-channel noise
at ~15 uV, on top of a large DC offset like the raw obci_eeg1 stream carries.

Usage
-----
    # Terminal 1: broadcast a stream of the chosen quality
    python mock_eeg_stream.py good
    python mock_eeg_stream.py flat

    # Terminal 2: run the gate against it
    python -c "import recording_checks as r; print(r.assert_eeg_quality())"

    # Or do both in one process (start stream, score it, print verdict, exit):
    python mock_eeg_stream.py good --selftest
    python mock_eeg_stream.py railed --selftest
"""

import argparse
import sys
import threading
import time

import numpy as np
from pylsl import StreamInfo, StreamOutlet, local_clock

N_CH = 16
SRATE = 125.0
MODES = ("good", "flat", "railed", "saturated")
RAIL_UV = 187500.0


def _make_block(mode, n, rng, dc, n0=0):
    """Generate ``n`` samples x ``N_CH`` of synthetic EEG (microvolts).

    ``n0`` is the absolute sample index of the first sample, so the shared
    oscillation stays phase-continuous across successive blocks (otherwise the
    block boundaries inject artificial high-frequency content that the QC reads
    as noise).
    """
    if mode == "flat":
        return rng.normal(0, 0.05, (n, N_CH)) + dc * 0  # essentially dead
    if mode == "railed":
        return np.full((n, N_CH), RAIL_UV) + rng.normal(0, 0.05, (n, N_CH))
    if mode == "saturated":
        return rng.normal(0, 80000.0, (n, N_CH))  # independent huge swings
    # "good": shared component (-> inter-channel correlation) + per-channel noise
    t = ((n0 + np.arange(n)) / SRATE)[:, None]
    common = (8 * np.sin(2 * np.pi * 10 * t) +          # ~alpha
              4 * np.sin(2 * np.pi * 3 * t) +
              rng.normal(0, 4, (n, 1)))                  # shared broadband
    indep = rng.normal(0, 6, (n, N_CH))
    return 0.7 * common + indep + dc                     # ~15 uV signal + DC offset


def stream(mode, stop_event, duration=None):
    info = StreamInfo("obci_eeg1", "EEG", N_CH, SRATE, "float32", "mock_obci_eeg1")
    outlet = StreamOutlet(info, chunk_size=8)
    rng = np.random.default_rng(0)
    dc = rng.uniform(-120000, 120000, (1, N_CH))         # large DC like raw obci_eeg1
    print(f"[mock] streaming obci_eeg1 ({mode}) @ {SRATE:.0f} Hz, {N_CH} ch. Ctrl-C to stop.")
    next_t = local_clock()
    t_end = None if duration is None else time.time() + duration
    block = max(1, int(SRATE / 20))                      # ~20 pushes/sec
    n0 = 0
    while not stop_event.is_set():
        data = _make_block(mode, block, rng, dc, n0).astype(np.float32)
        outlet.push_chunk(data.tolist())
        n0 += block
        next_t += block / SRATE
        sleep = next_t - local_clock()
        if sleep > 0:
            time.sleep(sleep)
        if t_end is not None and time.time() > t_end:
            break
    print("[mock] stopped.")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=MODES, help="Signal quality to broadcast.")
    p.add_argument("--selftest", action="store_true",
                   help="Stream in a thread, run the gate against it, print the verdict, exit.")
    args = p.parse_args(argv)

    if not args.selftest:
        stop = threading.Event()
        try:
            stream(args.mode, stop)
        except KeyboardInterrupt:
            stop.set()
        return 0

    # Self-test: broadcast in the background, then run BOTH layers against it:
    #   * the minimal in-bundle gate (recording_checks, numpy+pylsl only)
    #   * the watchdog's robust QC (eeg_watchdog -> qc_core, needs mne)
    # so you can see the division of labour: the gate catches frozen/empty
    # streams; only the watchdog catches a railed-but-flowing or saturated one.
    from pylsl import StreamInlet, resolve_byprop

    import recording_checks as rc

    stop = threading.Event()
    th = threading.Thread(target=stream, args=(args.mode, stop, 30), daemon=True)
    th.start()
    time.sleep(2)  # let the outlet resolve and buffer a little

    # Minimal gate (mne-free).
    gate_ok, gate_detail = rc.assert_eeg_flowing(probe_s=3.0)

    # Watchdog QC (pull ~6 s directly so the test needs no running watchdog).
    infos = resolve_byprop("name", "obci_eeg1", timeout=10)
    buf = []
    if infos:
        inlet = StreamInlet(infos[0], recover=False)
        inlet.flush()
        t_end = time.time() + 6
        while time.time() < t_end:
            chunk, tss = inlet.pull_chunk(timeout=0.5, max_samples=4096)
            if tss:
                buf.extend(chunk)
    stop.set()

    score = None
    if buf:
        try:
            import eeg_watchdog as wd
            score, _bads, _chn = wd.score_live(np.asarray(buf, dtype=float), 125.0)
            wd_ok = score is not None and score >= wd.MIN_QUALITY_SCORE
        except Exception as e:
            wd_ok = None
            print(f"[selftest] watchdog QC unavailable ({e})")
    else:
        wd_ok = None

    sc = f"{score:.0f}" if score is not None else "--"
    print(f"\n[selftest] mode={args.mode}")
    print(f"           minimal gate : {'PASS' if gate_ok else 'FAIL'}  ({gate_detail})")
    print(f"           watchdog QC  : {'PASS' if wd_ok else 'FAIL'}  score={sc}")
    # 'good' should pass both; every bad mode should fail the watchdog QC.
    return 0 if (wd_ok == (args.mode == "good")) else 1


if __name__ == "__main__":
    sys.exit(main())
