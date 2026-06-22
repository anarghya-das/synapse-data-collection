#!/usr/bin/env python3
"""Live EEG quality watchdog -- a standalone window you run BESIDE PsychoPy.

This is the heavy half of the recording safety net. Unlike the minimal in-bundle
gate (``recording_checks.py``), this script uses the project's real ``qc_core``
robust QC, so it needs mne + scipy -- run it in your analysis/conda env, NOT the
PsychoPy bundle. Open it in its own window (drag to a second monitor) before a
session and watch it for the whole recording.

It continuously:
  * subscribes to the ``obci_eeg1`` LSL stream (its own inlet; LSL allows many
    consumers, so it does not disturb LabRecorder),
  * tracks data FLOW -- flags the moment samples stop (board/Bluetooth drop),
  * scores a rolling window with ``qc_core.quality_check(robust)`` every ~1.5 s
    -- flags a montage that is connected but railed/dead,
  * shows a big GREEN/RED banner, the quality score, per-channel status, and
    BEEPS when it transitions into a bad state.

Usage
-----
    python eeg_watchdog.py                      # live GUI window
    python eeg_watchdog.py --no-gui             # terminal status line (headless)

Test it without hardware using the mock streamer in another terminal:
    python mock_eeg_stream.py good      # watchdog should show EEG OK
    python mock_eeg_stream.py railed    # watchdog should go red
"""

import argparse
import sys
import threading
import time
from collections import deque

import numpy as np

import qc_core

EEG_NAME = "obci_eeg1"
MIN_QUALITY_SCORE = 40.0   # robust quality_score (0-100) below this = problem
QC_PRESET = "default"


# --------------------------------------------------------------------------- #
# Scoring (shared with calibrate_quality.py)
# --------------------------------------------------------------------------- #
def _raw_from_buffer(samples_uv, sfreq):
    """Build an MNE Raw (uV -> V, resampled to 125 Hz) from a live LSL buffer."""
    import mne

    mne.set_log_level("ERROR")
    X = np.asarray(samples_uv, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    n_chan = X.shape[1]
    neurable = n_chan == len(qc_core.NEURABLE_CH_LABELS)
    labels = (qc_core.NEURABLE_CH_LABELS if neurable else qc_core.CEEGRID_CH_LABELS)[:n_chan]
    info = mne.create_info(ch_names=labels, sfreq=sfreq, ch_types="eeg")
    raw = mne.io.RawArray(X.T * 1e-6, info, verbose=False)
    if sfreq != 125:
        raw = raw.resample(125, verbose=False)
    return raw


def score_live(samples_uv, sfreq, preset=QC_PRESET):
    """Return ``(score, bad_channels, ch_names)`` for a live buffer."""
    raw = _raw_from_buffer(samples_uv, sfreq)
    qc = qc_core.quality_check(raw, method="robust", preset=preset, verbose=False)
    return qc["quality_score"], qc["bads_combined"], qc["ch_names"]


# --------------------------------------------------------------------------- #
# Background sampler: pull from LSL, track flow, score a rolling window
# --------------------------------------------------------------------------- #
class WatchdogSampler(threading.Thread):
    def __init__(self, name, window_s, interval_s, stall_s, min_score, preset):
        super().__init__(daemon=True)
        self.name = name
        self.window_s = window_s
        self.interval_s = interval_s
        self.stall_s = stall_s
        self.min_score = min_score
        self.preset = preset
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.s = {"present": False, "rate": 0.0, "age": float("inf"), "score": None,
                  "bads": [], "ch_names": [], "n": 0, "msg": "starting...", "bad": True}

    def snapshot(self):
        with self._lock:
            return dict(self.s)

    def _set(self, **kw):
        with self._lock:
            self.s.update(kw)

    def stop(self):
        self._stop.set()

    def run(self):
        from pylsl import StreamInlet, resolve_byprop

        inlet = None
        nominal = 125.0
        buf = deque()
        recvlog = deque()       # (recv_time, n_samples) over the last ~2 s
        last_recv = 0.0
        last_score = 0.0
        score, bads, chn = None, [], []

        while not self._stop.is_set():
            if inlet is None:
                infos = resolve_byprop("name", self.name, timeout=1.0)
                if not infos:
                    self._set(present=False, bad=True, age=float("inf"),
                              score=None, bads=[], n=0,
                              msg=f"waiting for '{self.name}'...")
                    continue
                info = infos[0]
                nominal = info.nominal_srate() or 125.0
                inlet = StreamInlet(info, max_buflen=int(self.window_s) + 5, recover=True)
                buf.clear()
                last_recv = time.time()
                score, bads, chn = None, [], []
                self._set(present=True, msg="connected")

            chunk, tss = inlet.pull_chunk(timeout=0.5, max_samples=4096)
            now = time.time()
            if tss:
                buf.extend(chunk)
                maxlen = int(self.window_s * nominal)
                while len(buf) > maxlen:
                    buf.popleft()
                last_recv = now
                recvlog.append((now, len(tss)))
            while recvlog and now - recvlog[0][0] > 2.0:
                recvlog.popleft()

            rate = sum(n for _, n in recvlog) / 2.0 if recvlog else 0.0
            age = now - last_recv

            if now - last_score >= self.interval_s and len(buf) >= nominal * 3:
                last_score = now
                try:
                    score, bads, chn = score_live(np.asarray(buf, dtype=float),
                                                  nominal, self.preset)
                except Exception:
                    score, bads, chn = None, [], []

            stalled = age > self.stall_s
            bad = stalled or (score is not None and score < self.min_score)
            msg = ("STREAM LOST -- no samples" if stalled
                   else (f"score {score:.0f}/100" if score is not None else "scoring..."))
            self._set(rate=rate, age=age, score=score, bads=bads, ch_names=chn,
                      n=len(buf), bad=bad, msg=msg)

        try:
            if inlet is not None:
                inlet.close_stream()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Front-ends
# --------------------------------------------------------------------------- #
def run_gui(sampler, args):
    import tkinter as tk

    root = tk.Tk()
    root.title(f"EEG Watchdog -- {args.name}")
    root.configure(bg="#111")
    root.geometry("540x380")

    banner = tk.Label(root, text="STARTING", font=("Helvetica", 28, "bold"),
                      fg="white", bg="#555", height=2)
    banner.pack(fill="x", padx=8, pady=8)
    info = tk.Label(root, text="", font=("Menlo", 13), fg="#ddd", bg="#111", justify="left")
    info.pack(fill="x", padx=14, anchor="w")

    grid = tk.Frame(root, bg="#111")
    grid.pack(pady=10)
    cells = {}
    for i, ch in enumerate(qc_core.CEEGRID_CH_LABELS):
        c = tk.Label(grid, text=ch, width=5, font=("Menlo", 11, "bold"), fg="white", bg="#444")
        c.grid(row=i // 8, column=i % 8, padx=2, pady=2)
        cells[ch] = c

    msg = tk.Label(root, text="", font=("Menlo", 11), fg="#9cf", bg="#111")
    msg.pack(pady=6)
    prev_bad = {"v": None}

    def update():
        s = sampler.snapshot()
        bad = s["bad"]
        if bad and prev_bad["v"] is False:   # rising edge into a problem
            root.bell()
        prev_bad["v"] = bad

        if not s["present"]:
            banner.config(text="NO STREAM", bg="#a00")
        elif s["age"] > args.stall:
            banner.config(text="STREAM LOST", bg="#a00")
        elif bad:
            banner.config(text="EEG PROBLEM", bg="#a00")
        else:
            banner.config(text="EEG OK", bg="#0a0")

        sc = f"{s['score']:.0f}/100" if s["score"] is not None else "--"
        info.config(text=(f" score  : {sc}\n rate   : {s['rate']:.0f} Hz  (nominal 125)\n"
                          f" last   : {s['age']:.1f}s ago\n samples: {s['n']}"))
        badset = set(s["bads"])
        for ch, c in cells.items():
            if not s["ch_names"]:
                c.config(bg="#444")
            else:
                c.config(bg="#c22" if ch in badset else "#262")
        msg.config(text=s["msg"])
        root.after(400, update)

    update()
    root.protocol("WM_DELETE_WINDOW", lambda: (sampler.stop(), root.destroy()))
    root.mainloop()


def run_text(sampler, args):
    prev = None
    try:
        while True:
            s = sampler.snapshot()
            sc = f"{s['score']:.0f}" if s["score"] is not None else "--"
            flag = "OK " if not s["bad"] else "BAD"
            if s["bad"] and prev is False:
                sys.stdout.write("\a")
            prev = s["bad"]
            print(f"[{flag}] score={sc} rate={s['rate']:.0f}Hz age={s['age']:.1f}s "
                  f"n={s['n']}  {s['msg']}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        sampler.stop()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", default=EEG_NAME, help="EEG LSL stream name.")
    p.add_argument("--min-score", type=float, default=MIN_QUALITY_SCORE,
                   help="quality_score below this = problem.")
    p.add_argument("--window", type=float, default=10.0, help="rolling seconds scored.")
    p.add_argument("--interval", type=float, default=1.5, help="seconds between scorings/refreshes.")
    p.add_argument("--stall", type=float, default=3.0, help="seconds without samples = stream lost.")
    p.add_argument("--preset", default=QC_PRESET, help="qc_core preset.")
    p.add_argument("--no-gui", action="store_true", help="terminal status line instead of a window.")
    a = p.parse_args(argv)

    sampler = WatchdogSampler(a.name, a.window, a.interval, a.stall, a.min_score, a.preset)
    sampler.start()
    if a.no_gui:
        run_text(sampler, a)
    else:
        try:
            run_gui(sampler, a)
        except Exception as e:
            print(f"[watchdog] GUI unavailable ({e}); falling back to text mode.")
            run_text(sampler, a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
