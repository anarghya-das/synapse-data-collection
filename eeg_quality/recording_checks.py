"""Minimal, dependency-light EEG pre-flight gate for the PsychoPy recording.

Imported by ``hearing.psyexp`` (the ``code_init`` Code Component), so it MUST
stay importable inside the PsychoPy app bundle -- which ships only numpy +
pylsl, NOT mne/scipy. It therefore does only cheap structural / flow checks:

  * stream resolves?          -> catches "No EEG stream in XDF"
  * samples actually flowing?  -> catches "Empty EEG data (0 samples)" (the 16x0 case)
  * effective rate near nominal? -> catches a half-dead / heavily-dropping stream
  * every channel frozen?      -> catches a fully flat / disconnected board

What it deliberately does NOT do is score signal quality (railed / noisy /
low-correlation channels). That needs the project's mne-based ``qc_core``, which
cannot run in the PsychoPy bundle. For live quality monitoring run
``eeg_watchdog.py`` in a second window (in an env that has mne); for offline
file checking use ``calibrate_quality.py`` / ``eeg_watchdog.validate_xdf``.

So: this gate stops you recording into a dead/empty stream; the watchdog catches
a montage that is connected but railed, and a stream that dies mid-session.
"""

import time

import numpy as np

EEG_TYPE = "EEG"        # resolve by LSL *type*, not name, so any board works
VIDEO_NAME = "VideoStream"
PROBE_S = 3.0
MIN_RATE_FRAC = 0.5     # fail if effective rate < this * nominal srate
FLAT_STD_UV = 1.0       # if EVERY channel's DC-removed SD is below this -> frozen
VIDEO_MIN_FRAMES = 5    # frames that must arrive for the camera to count as live


def assert_eeg_flowing(stream_type=EEG_TYPE, probe_s=PROBE_S, timeout=10.0):
    """Resolve an EEG stream by *type* and confirm real samples are flowing.

    Resolving by LSL stream *type* (``"EEG"``) rather than a fixed name keeps the
    gate device-agnostic: it accepts OpenBCI's ``obci_eeg1``, a Neurable stream,
    or any other board that advertises an ``EEG``-type LSL stream. Returns
    ``(ok: bool, detail: str)`` and never raises, so it is safe to call inline
    before the LabRecorder ``start`` command.
    """
    from pylsl import StreamInlet, resolve_byprop

    infos = resolve_byprop("type", stream_type, timeout=timeout)
    if not infos:
        return False, f"No '{stream_type}' stream FOUND (nothing resolved in {timeout:.0f}s)"

    info = infos[0]
    name = info.name()      # actual device stream name, for logging
    nominal = info.nominal_srate() or 0.0
    inlet = StreamInlet(info, max_buflen=int(probe_s) + 5, recover=False)
    try:
        inlet.flush()  # drop stale samples so we measure the live rate
    except Exception:
        pass

    buf = []
    t_end = time.time() + probe_s
    while time.time() < t_end:
        chunk, tss = inlet.pull_chunk(timeout=0.5, max_samples=4096)
        if tss:
            buf.extend(chunk)
    try:
        inlet.close_stream()
    except Exception:
        pass

    if not buf:
        return False, f"EEG '{name}' resolved but pushed ZERO samples in {probe_s:.0f}s"

    X = np.asarray(buf, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    rate = len(X) / probe_s
    if nominal and rate < MIN_RATE_FRAC * nominal:
        return False, (f"EEG '{name}' only ~{rate:.0f} Hz (nominal {nominal:.0f}) "
                       "-- dropping samples / unstable link")

    # DC-removed per-channel SD: a frozen/disconnected board reads as a constant
    # (after removing its huge DC offset, SD ~ 0). This does NOT catch a railed
    # channel that still oscillates -- that is the watchdog's job.
    stds = (X - X.mean(axis=0)).std(axis=0)
    if np.all(stds < FLAT_STD_UV):
        return False, (f"EEG '{name}' all {X.shape[1]} channels flat/frozen "
                       "(board off, not streaming, or fully disconnected)")

    return True, f"EEG '{name}' flowing -- ~{rate:.0f} Hz, {X.shape[1]} ch, {len(X)} samples"


def preflight_eeg_gate(win=None, stream_type=EEG_TYPE, name=None):
    """Check the EEG stream and log the verdict -- no GUI, no prompt.

    Returns ``(ok: bool, detail: str)``. On failure the caller (the psyexp)
    simply ends the experiment (``original_quit()``); this function only checks
    and writes the reason to the console and the PsychoPy log file so it lands
    in ``<participant>.log``. ``win`` is accepted but unused (kept so the
    existing Builder call site does not need to change). ``name`` is a legacy
    no-op kept only so a stale ``hearing_lastrun.py`` (which still passes
    ``name="obci_eeg1"``) does not crash before it is regenerated -- the stream
    is now resolved by *type*, so the name is ignored.
    """
    ok, detail = assert_eeg_flowing(stream_type=stream_type)
    line = f"EEG preflight {'OK' if ok else 'FAILED'}: {detail}"
    print(f"[preflight] {line}")
    try:
        from psychopy import logging

        (logging.info if ok else logging.error)(line)
        logging.flush()
    except Exception:
        pass
    return ok, detail


def assert_video_flowing(name=VIDEO_NAME, min_frames=VIDEO_MIN_FRAMES,
                         resolve_timeout=10.0, probe_s=5.0):
    """Confirm the webcam's LSL ``VideoStream`` is actually pushing frames.

    The experiment's ``VideoRecorder`` creates the outlet in ``__init__`` (before
    it opens the camera), so a camera that fails to open shows up as an outlet
    that resolves but never pushes frames -- exactly the "empty video stream"
    case. We poll up to ``probe_s`` and succeed as soon as ``min_frames`` arrive,
    which also absorbs the 1-2 s a webcam can take to deliver its first frame.

    Returns ``(ok: bool, detail: str)``; never raises.
    """
    from pylsl import StreamInlet, resolve_byprop

    infos = resolve_byprop("name", name, timeout=resolve_timeout)
    if not infos:
        return False, f"Video '{name}' NOT FOUND (camera outlet never appeared)"

    inlet = StreamInlet(infos[0], max_buflen=2, recover=False)
    try:
        inlet.flush()
    except Exception:
        pass

    got = 0
    t_end = time.time() + probe_s
    while time.time() < t_end and got < min_frames:
        _chunk, tss = inlet.pull_chunk(timeout=0.5, max_samples=512)
        got += len(tss)
    try:
        inlet.close_stream()
    except Exception:
        pass

    if got < min_frames:
        return False, (f"Video '{name}' sent only {got} frames in {probe_s:.0f}s "
                       "-- camera failed to open / not capturing")
    return True, f"Video flowing -- {got}+ frames"


def preflight_video_gate(win=None, name=VIDEO_NAME):
    """Check the webcam stream and log the verdict -- no GUI, no prompt.

    Mirror of ``preflight_eeg_gate`` for video. The caller should only invoke
    this when video recording is enabled. ``win`` is accepted but unused.
    """
    ok, detail = assert_video_flowing(name=name)
    line = f"Video preflight {'OK' if ok else 'FAILED'}: {detail}"
    print(f"[preflight] {line}")
    try:
        from psychopy import logging

        (logging.info if ok else logging.error)(line)
        logging.flush()
    except Exception:
        pass
    return ok, detail
