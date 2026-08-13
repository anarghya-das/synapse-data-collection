"""Align CEEGrid EEG with the webcam recording from one LSL XDF file.

Library half of the video+EEG pairing pipeline (the Hydra entry point is
``pipelines/pair_video.py``). Faithfully ported from ``../../synapse/split_video.py``
with the CLI / file-discovery removed: this repo resolves recordings through
``synapse_qc.inventory`` and drives parameters through Hydra, so everything here
takes explicit arguments instead.

Two modes (see :func:`pair_recording`):
  * ``epoch``  — one stim-locked clip + one EEG epoch per trial, windowed to the
    task timings, with a per-frame ``*_frames.csv`` sidecar so a downstream step
    can resample video onto the 125 Hz EEG grid. This is what a multimodal model
    consumes.
  * ``marker`` — legacy marker-to-marker segments (one clip per marker span) plus
    a single filtered ``Raw`` ``.fif``.

EEG bad-channel handling is delegated to ``../../synapse``'s ``create_mne`` via the
``preprocessing.utils`` module (imported lazily so the analysis repo only needs
to be on ``sys.path`` at call time, and so the caller's montage monkeypatch on
``utils.create_mne`` is honoured).
"""
import os
import re

import numpy as np


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _progress(iterable):
    """Wrap ``iterable`` in a tqdm progress bar when tqdm is available."""
    try:
        from tqdm import tqdm

        return tqdm(iterable)
    except ImportError:
        return iterable


def _sanitize(label):
    """Turn a marker label into a filesystem-safe filename fragment."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(label)).strip("_") or "segment"


def _stream_by_type(streams, stream_type):
    """Return all streams whose ``info.type`` equals ``stream_type``."""
    return [s for s in streams if s["info"]["type"][0] == stream_type]


def _select_eeg(streams, name=None):
    """Pick the EEG stream by exact name.

    When ``name`` is given (the pipeline uses ``obci_eeg1``), only an exact match
    is returned — never a fall-back to some other EEG-typed stream. This matters
    for recordings that carry a second device (e.g. a 14-ch Neurable) or a second
    OpenBCI stream; silently grabbing the wrong one yields all-bad channels.
    """
    eeg = _stream_by_type(streams, "EEG")
    if name:
        named = [s for s in eeg if s["info"]["name"][0] == name]
        return named[0] if named else None
    return eeg[0] if eeg else None


# --------------------------------------------------------------------------- #
# EEG: align markers to EEG samples and build a filtered MNE Raw
# --------------------------------------------------------------------------- #
def align_eeg(
    eeg_stream, marker_stream, bindings, bandpass, flat_voltage, notch_freq,
    channel_strategy="interpolate", quality_preset="default",
):
    """Build an annotated, filtered ``mne.io.Raw`` from the EEG + marker streams.

    ``channel_strategy`` controls bad-channel handling (see ``create_mne``):
    ``interpolate`` (default) keeps a fixed 16-channel layout for every subject,
    which a cross-subject multimodal model needs; ``drop`` removes bad channels;
    ``zero_mask``/``keep_all`` retain the 16 channels without interpolating.

    ``preprocessing.utils`` is imported here (not at module top) so that the
    analysis repo only needs to be on ``sys.path`` by call time, and so a caller
    that has monkeypatched ``utils.create_mne`` (to inject an absolute montage
    path) gets the patched version.
    """
    from preprocessing import utils  # analysis-repo helpers; see module docstring

    marker_data = np.atleast_1d(np.array(marker_stream["time_series"]).squeeze())
    marker_timestamps = marker_stream["time_stamps"]

    # For each marker, find the index of the nearest EEG sample.
    eeg_insert_points = utils.closest_points_vector(
        eeg_stream["time_stamps"], marker_timestamps
    )

    marker_dict, id_binding, _category_mapping = utils.create_mappings(
        marker_data, bindings
    )
    events = utils.create_events(eeg_insert_points, marker_dict, marker_data)
    raw = utils.create_mne(
        eeg_stream,
        events,
        id_binding,
        bandpass=bandpass,
        flat_voltage=flat_voltage,
        notch_freq=notch_freq,
        channel_strategy=channel_strategy,
        quality_preset=quality_preset,
    )
    return raw, events, marker_dict


# --------------------------------------------------------------------------- #
# Video: align markers to frames and split the raw recording
# --------------------------------------------------------------------------- #
def video_segments(video_stream, marker_stream, exclude_phases=None):
    """Build ``(start_frame, end_frame, label)`` tuples, one per marker segment.

    Segment ``i`` covers the frames streamed between marker ``i`` and marker
    ``i + 1`` and is labelled with marker ``i``. Empty segments (two markers
    landing on the same frame) are dropped.

    ``exclude_phases`` is a list of phase tokens (e.g. ``["response"]``) whose
    segments are skipped. The ``response`` phase is the brief score-entry window
    after poststim in the HLT/LET tasks, not a stimulus epoch, so it is dropped
    by default.
    """
    from preprocessing import utils

    exclude_phases = exclude_phases or []
    marker_data = np.atleast_1d(np.array(marker_stream["time_series"]).squeeze())
    video_frames = np.atleast_1d(np.asarray(video_stream["time_series"]).squeeze())

    insert_points = utils.closest_points_vector(
        video_stream["time_stamps"], marker_stream["time_stamps"]
    )

    segments = []
    skipped_phase = 0
    for i in range(len(insert_points) - 1):
        label = str(marker_data[i])
        if any(re.search(rf"_{re.escape(p)}\b", label) for p in exclude_phases):
            skipped_phase += 1
            continue
        frames = video_frames[insert_points[i] : insert_points[i + 1]]
        if len(frames) == 0:
            print(f"  [skip] empty video segment for marker '{label}'")
            continue
        segments.append((int(frames[0]), int(frames[-1]), label))
    if skipped_phase:
        print(
            f"  [skip] excluded {skipped_phase} segment(s) for phases "
            f"{exclude_phases}"
        )
    return segments


def split_video(input_file, segments, output_folder, fps_override=None):
    """Cut ``input_file`` into one ``.avi`` per ``(start, end, label)`` segment.

    Guards a missing file, prefixes each clip with its segment index so duplicate
    marker labels do not overwrite one another, and degrades gracefully without
    tqdm.
    """
    import cv2

    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video file: {input_file}")

    fps = fps_override or cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = (
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    print(
        f"  video: {os.path.basename(input_file)}  "
        f"fps={fps:.3f}  frames={frame_count}  size={width}x{height}"
    )

    os.makedirs(output_folder, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"XVID")

    written = []
    for i, (start_frame, end_frame, label) in enumerate(_progress(segments)):
        out_path = os.path.join(output_folder, f"{i:03d}_{_sanitize(label)}.avi")
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_frame))
        writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
        for _ in range(int(start_frame), int(end_frame)):
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)
        writer.release()
        written.append(out_path)

    cap.release()
    return written


# --------------------------------------------------------------------------- #
# Epoch-aligned mode: one clip + one EEG epoch per stim trial
# --------------------------------------------------------------------------- #
def _condition_from_label(task, label):
    """Strip the ``<task>_stim-`` prefix to get the trial condition tag."""
    cond = re.sub(rf"^{re.escape(task)}_stim[-_]?", "", label)
    return cond or "stim"


def epoch_video_segments(video_stream, marker_stream, task_timings):
    """One segment per *stim* marker, spanning the task's ``[tmin, tmax]`` window.

    Returns a list of dicts (chronological, with a per-task ``trial`` counter)
    each holding the source frame range plus the true per-frame timestamps
    (relative to stim onset and in raw LSL time) needed to align pupillometry to
    the EEG epoch samples. The webcam's frame rate is sub-nominal and dejittered,
    so alignment uses these timestamps, never an assumed fps.
    """
    marker_data = np.atleast_1d(np.array(marker_stream["time_series"]).squeeze())
    marker_ts = np.asarray(marker_stream["time_stamps"]).squeeze()
    video_frames = np.atleast_1d(np.asarray(video_stream["time_series"]).squeeze())
    video_ts = np.asarray(video_stream["time_stamps"]).squeeze()

    segments = []
    trial_counter = {}
    for i, raw_label in enumerate(marker_data):
        label = str(raw_label)
        m = re.match(r"^(pmt|hlt|let|ast)_stim\b", label)
        if not m:
            continue
        task = m.group(1)
        timings = task_timings.get(task)
        if timings is None:
            continue

        t_stim = float(marker_ts[i])
        win_lo = t_stim + timings["tmin"]
        win_hi = t_stim + timings["tmax"]
        mask = (video_ts >= win_lo) & (video_ts <= win_hi)
        n = int(mask.sum())
        trial = trial_counter.get(task, 0)
        trial_counter[task] = trial + 1
        if n == 0:
            print(f"  [skip] {task} trial {trial:02d}: no video frames in window.")
            continue

        src = video_frames[mask].astype(int)
        t_lsl = video_ts[mask].astype(float)
        partial = win_lo < video_ts[0] or win_hi > video_ts[-1]
        segments.append(
            {
                "task": task,
                "label": label,
                "condition": _condition_from_label(task, label),
                "trial": trial,
                "t_stim": t_stim,
                "tmin": timings["tmin"],
                "tmax": timings["tmax"],
                "src_start": int(src[0]),
                "src_end": int(src[-1]),
                "src_frames": src,
                "t_rel": t_lsl - t_stim,
                "t_lsl": t_lsl,
                "n_frames": n,
                "partial": bool(partial),
            }
        )
    return segments


def write_epoch_clips(input_file, segments, video_root, subject_id, fps_override=None):
    """Write one ``.avi`` + one ``_frames.csv`` per stim epoch under ``video_root``.

    The CSV is the alignment key: for every written frame it records the source
    frame index, the time relative to stim onset, and the raw LSL timestamp, so a
    downstream pupillometry step can resample frames onto the 125 Hz EEG grid.
    """
    import csv

    import cv2

    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video file: {input_file}")

    fps = fps_override or cap.get(cv2.CAP_PROP_FPS)
    width, height = (
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    print(
        f"  video: {os.path.basename(input_file)}  tag_fps={fps:.3f}  "
        f"size={width}x{height}  (clip timing comes from *_frames.csv, not fps)"
    )
    fourcc = cv2.VideoWriter_fourcc(*"XVID")

    manifest = []
    for seg in _progress(segments):
        task_dir = os.path.join(video_root, seg["task"])
        os.makedirs(task_dir, exist_ok=True)
        stem = (
            f"sub-{subject_id}_{seg['task']}_trial-{seg['trial']:02d}_"
            f"{_sanitize(seg['condition'])}"
        )
        clip_path = os.path.join(task_dir, stem + ".avi")
        csv_path = os.path.join(task_dir, stem + "_frames.csv")

        cap.set(cv2.CAP_PROP_POS_FRAMES, seg["src_start"])
        writer = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
        rows = []
        for k, src_frame in enumerate(seg["src_frames"]):
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)
            rows.append((k, int(src_frame), float(seg["t_rel"][k]), float(seg["t_lsl"][k])))
        writer.release()

        with open(csv_path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["clip_frame", "src_frame", "t_rel_stim_s", "t_lsl_s"])
            w.writerows(rows)

        manifest.append(
            {
                "task": seg["task"],
                "trial": seg["trial"],
                "eeg_epoch_index": seg.get("eeg_epoch_index"),
                "condition": seg["condition"],
                "label": seg["label"],
                "t_stim_lsl": seg["t_stim"],
                "tmin": seg["tmin"],
                "tmax": seg["tmax"],
                "video_clip": os.path.relpath(clip_path, os.path.dirname(video_root)),
                "video_frames_csv": os.path.relpath(csv_path, os.path.dirname(video_root)),
                "n_frames_written": len(rows),
                "n_frames_expected": seg["n_frames"],
                "partial_window": seg["partial"],
            }
        )

    cap.release()
    return manifest


def _write_qc_sidecar(qc_result, ch_names, out_dir, subject_id):
    """Persist the QC verdict next to the epochs so the downstream finalize step
    can apply a channel strategy without re-running QC.

    Writes a BIDS-style ``*_channels.tsv`` (channel / status / reasons) and a
    ``*_qc.json`` (score, method, preset, per-criterion bad lists). This is the
    source of truth for the per-channel validity mask: pairing detects the bad
    channels but does NOT act on them, so this file is what tells the model which
    channels are real vs interpolated/masked."""
    import csv
    import json

    os.makedirs(out_dir, exist_ok=True)
    reasons_by_crit = {
        "flat": set(qc_result.get("bads_flat", [])),
        "dead": set(qc_result.get("bads_variance", [])),
        "noisy": set(qc_result.get("bads_noisy", [])),
        "lowcorr": set(qc_result.get("bads_corr", [])),
    }
    bads = set(qc_result.get("bads_combined", []))

    tsv_path = os.path.join(out_dir, f"sub-{subject_id}_channels.tsv")
    with open(tsv_path, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["channel", "status", "reasons"])
        for ch in ch_names:
            hit = ";".join(k for k, v in reasons_by_crit.items() if ch in v)
            w.writerow([ch, "bad" if ch in bads else "good", hit or "n/a"])

    json_path = os.path.join(out_dir, f"sub-{subject_id}_qc.json")
    with open(json_path, "w") as fh:
        json.dump(
            {
                "subject_id": subject_id,
                "quality_score": qc_result.get("quality_score"),
                "method": qc_result.get("method"),
                "preset": qc_result.get("preset_used"),
                "n_channels": len(ch_names),
                "ch_names": list(ch_names),
                "bads_combined": sorted(bads),
                "bads_flat": sorted(reasons_by_crit["flat"]),
                "bads_dead": sorted(reasons_by_crit["dead"]),
                "bads_noisy": sorted(reasons_by_crit["noisy"]),
                "bads_lowcorr": sorted(reasons_by_crit["lowcorr"]),
                "bads_highcorr_reported": sorted(qc_result.get("bads_highcorr", [])),
            },
            fh,
            indent=2,
        )
    return tsv_path, json_path


def epoch_eeg_all(raw, events, marker_dict, task_timings, out_dir, subject_id):
    """Epoch on stim markers per task and save EVERY boundary-valid epoch.

    Detect-and-defer: no PTP rejection and no channel repair happen here. Bad
    channels detected by QC stay in ``raw.info['bads']`` and are written into each
    ``_epo.fif`` (MNE persists ``info['bads']``), so the downstream finalize step
    can interpolate / mask / drop them and apply epoch rejection over *good*
    channels. This keeps the slow alignment + video encoding a one-time cost and
    makes channel strategy / rejection cheap, swappable downstream transforms.

    MNE may still drop epochs whose ``[tmin, tmax]`` window falls outside the
    recording; ``kept_positions`` therefore reflects the trials actually saved
    (chronological trial index within the task), keeping the video side matched
    1:1 with the saved epochs. ``excluded`` is always False here — task exclusion
    is a rejection decision, and rejection lives in finalize."""
    import mne

    eeg_dir = os.path.join(out_dir, "eeg")
    os.makedirs(eeg_dir, exist_ok=True)

    info = {}
    for task, timings in task_timings.items():
        stim_ids = {
            lbl: code
            for lbl, code in marker_dict.items()
            if re.match(rf"^{re.escape(task)}_stim\b", lbl)
        }
        if not stim_ids:
            continue
        stim_codes = set(stim_ids.values())
        # Chronological event-array rows for this task's stim markers. A saved
        # epoch's position within this list is its trial index, shared with video.
        task_event_rows = [i for i, r in enumerate(events) if int(r[2]) in stim_codes]

        epochs = mne.Epochs(
            raw, events, event_id=stim_ids,
            tmin=timings["tmin"], tmax=timings["tmax"],
            baseline=None, preload=True, reject_by_annotation=False, verbose=False,
        )
        n_trials = len(task_event_rows)
        n_epochs = len(epochs)
        kept_positions = [task_event_rows.index(int(r)) for r in epochs.selection]

        epo_path = os.path.join(eeg_dir, f"sub-{subject_id}_{task}_epo.fif")
        epochs.save(epo_path, overwrite=True, verbose=False)
        n_boundary = n_trials - n_epochs
        print(
            f"  [eeg] {task}: {n_trials} stim trials -> {n_epochs} epochs saved"
            + (f" ({n_boundary} outside recording)" if n_boundary else "")
            + f"  bads={list(raw.info['bads'])} -> {os.path.basename(epo_path)}"
        )
        info[task] = {
            "excluded": False,           # rejection/exclusion deferred to finalize
            "kept_positions": kept_positions,
            "n_epochs": n_epochs,
            "n_trials": n_trials,
        }
    return info


def _match_segments_to_eeg(segments, eeg_info):
    """Keep only video segments whose trial survived EEG rejection, tagging each
    with its index into the saved ``_epo.fif`` so clips pair 1:1 with epochs."""
    kept = []
    for seg in segments:
        stats = eeg_info.get(seg["task"])
        if not stats or stats["excluded"]:
            continue
        positions = stats["kept_positions"]
        if seg["trial"] in positions:
            seg["eeg_epoch_index"] = positions.index(seg["trial"])
            kept.append(seg)
    return kept


def _write_alignment_manifest(manifest, eeg_info, out_dir, subject_id):
    """Write the master video<->EEG trial index and flag any count mismatch."""
    import csv

    path = os.path.join(out_dir, f"sub-{subject_id}_alignment.csv")
    cols = [
        "task", "trial", "eeg_epoch_index", "condition", "label", "t_stim_lsl",
        "tmin", "tmax", "video_clip", "video_frames_csv", "n_frames_written",
        "n_frames_expected", "partial_window",
    ]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(manifest)
    print(f"  [align] wrote {path}  ({len(manifest)} paired trials)")

    # Video clips and saved EEG epochs should match 1:1 per task. A mismatch here
    # is expected only when video ran out before an epoch's window (fewer clips)
    # or a subject has no video at all; it is NOT a rejection artifact — rejection
    # happens downstream in finalize, over this full paired set.
    vid_per_task = {}
    for row in manifest:
        vid_per_task[row["task"]] = vid_per_task.get(row["task"], 0) + 1
    eeg_saved = {
        t: s["n_epochs"] for t, s in (eeg_info or {}).items() if not s["excluded"]
    }
    for task in sorted(set(vid_per_task) | set(eeg_saved)):
        nv, ne = vid_per_task.get(task, 0), eeg_saved.get(task, 0)
        flag = "" if nv == ne else "  <-- MISMATCH, check alignment"
        print(f"    {task}: {nv} video clips / {ne} EEG epochs{flag}")


# --------------------------------------------------------------------------- #
# Model-side alignment helpers (import these when building the multimodal dataset)
# --------------------------------------------------------------------------- #
def eeg_time_grid(tmin, tmax, sfreq=125.0):
    """Epoch sample times (s) relative to stim onset — matches the MNE epoch axis."""
    n = int(round((tmax - tmin) * sfreq)) + 1
    return tmin + np.arange(n) / sfreq


def resample_frames_to_eeg(frame_t_rel, frame_values, tmin, tmax, sfreq=125.0):
    """Resample a per-frame signal (e.g. pupil diameter) onto the EEG grid.

    Uses each frame's true ``t_rel_stim_s`` (from the clip's ``*_frames.csv``), so
    the returned array is aligned 1:1 with the EEG epoch's time axis — EEG[c, t]
    and pupil[t] then share the same t. Frames need not be evenly spaced; values
    outside the frame range are held flat. This is the correct way to pair the two
    modalities — do NOT use frame_index / nominal_fps.
    """
    grid = eeg_time_grid(tmin, tmax, sfreq)
    frame_t_rel = np.asarray(frame_t_rel, dtype=float)
    frame_values = np.asarray(frame_values, dtype=float)
    order = np.argsort(frame_t_rel)
    return np.interp(grid, frame_t_rel[order], frame_values[order])


def nearest_frame_for_eeg(frame_t_rel, tmin, tmax, sfreq=125.0):
    """For each EEG sample, the row index of the nearest video frame in time.

    Use when the model needs the actual frame image per EEG timestep (feeding
    frames to a CNN) rather than an interpolated scalar.
    """
    grid = eeg_time_grid(tmin, tmax, sfreq)
    frame_t_rel = np.asarray(frame_t_rel, dtype=float)
    idx = np.clip(np.searchsorted(frame_t_rel, grid), 1, len(frame_t_rel) - 1)
    left = grid - frame_t_rel[idx - 1]
    right = frame_t_rel[idx] - grid
    return np.where(left <= right, idx - 1, idx)


# --------------------------------------------------------------------------- #
# Per-recording orchestration (called once per participant by the pipeline)
# --------------------------------------------------------------------------- #
def pair_recording(
    xdf_path, video_path, subject_id, out_dir, *,
    eeg_stream_name="obci_eeg1", channel_strategy="interpolate",
    bandpass=None, flat_voltage=0.5, notch_freq=60.0, quality_preset="default",
    bindings=("pmt", "hlt", "let", "ast"), task_timings=None,
    mode="epoch", exclude_phases=("response",), fps=None, sfreq=125.0,
    no_eeg=False, no_video=False,
):
    """Align EEG + video for a single recording and write the paired outputs.

    Replaces ``split_video.py``'s ``process_recording`` / ``_process_epoch_mode``;
    file discovery is the caller's job (``video_path`` comes from
    ``inventory.Participant.video``), and all parameters are explicit so Hydra is
    the single source of truth.

    ``epoch`` mode is now *detect-and-defer*: it filters, epochs, and pairs EVERY
    boundary-valid trial with all 16 channels intact (bad channels detected but
    untouched), leaving channel repair + epoch rejection to ``finalize_dataset``.
    ``channel_strategy`` therefore only affects the legacy ``marker`` mode here.

    Returns a uniform summary dict regardless of mode. Raises on a hard failure
    (e.g. missing EEG stream in epoch mode) so the pipeline can isolate the
    subject and keep going.
    """
    import pyxdf

    bandpass = bandpass or {"low": 1, "high": 50}
    task_timings = task_timings or {}
    # Negative thresholds disable the corresponding step (CLI convention preserved).
    flat_voltage = None if (flat_voltage is not None and flat_voltage < 0) else flat_voltage
    notch_freq = None if (notch_freq is not None and notch_freq < 0) else notch_freq

    print(f"\n=== {subject_id}  ({os.path.basename(xdf_path)}) ===")
    streams, _header = pyxdf.load_xdf(xdf_path)
    marker_streams = _stream_by_type(streams, "Markers")
    if not marker_streams:
        raise ValueError("no marker stream found; cannot align anything")
    marker_stream = marker_streams[0]

    summary = {
        "subject_id": subject_id,
        "mode": mode,
        "n_bad_detected": None,
        "quality_score": None,
        "task_counts": {},
        "excluded_tasks": [],
        "video_present": False,
        "paired_trials": 0,
    }

    if mode == "marker":
        return _pair_marker_mode(
            streams, marker_stream, xdf_path, video_path, subject_id, out_dir,
            bindings, bandpass, flat_voltage, notch_freq, channel_strategy,
            quality_preset, exclude_phases, fps, no_eeg, no_video, summary,
        )
    return _pair_epoch_mode(
        streams, marker_stream, video_path, subject_id, out_dir,
        bindings, bandpass, flat_voltage, notch_freq,
        quality_preset, eeg_stream_name, task_timings, fps,
        no_eeg, no_video, summary,
    )


def _pair_epoch_mode(
    streams, marker_stream, video_path, subject_id, out_dir,
    bindings, bandpass, flat_voltage, notch_freq,
    quality_preset, eeg_stream_name, task_timings, fps,
    no_eeg, no_video, summary,
):
    """Detect-and-defer epoch export: paired EEG epochs + per-trial video clips.

    One stim trial -> one EEG epoch (``eeg/*_epo.fif``, all 16 channels) + one clip
    with a frame-timestamp sidecar (``video/<task>/*.avi`` + ``*_frames.csv``). A
    master ``*_alignment.csv`` ties them by (task, trial). QC runs for DETECTION
    only: bad channels are recorded (in ``info['bads']`` + a ``*_channels.tsv`` /
    ``*_qc.json`` sidecar) but NOT interpolated/dropped/zeroed, and no epochs are
    rejected. ``finalize_dataset`` applies the channel strategy + rejection later.
    Because nothing is dropped on quality grounds, no subject fails here for bad
    channels (that decision is deferred), so out_dir is always created.
    """
    import mne

    eeg_info = {}
    if not no_eeg:
        eeg_stream = _select_eeg(streams, name=eeg_stream_name)
        if eeg_stream is None:
            # The dataset is EEG-anchored; a recording without the CEEGrid stream
            # is not part of the cohort (e.g. a Neurable-only session). Excluding
            # it here mirrors the pipeline, which keys on obci_eeg1.
            raise ValueError(f"no '{eeg_stream_name}' EEG stream in recording")
        # keep_all = run QC + filter, but do NOT touch channels. keep_all clears
        # info['bads'], so restore the detected bads from the stored QC result;
        # the epochs then carry them for finalize, and the sidecar records them.
        raw, events, marker_dict = align_eeg(
            eeg_stream, marker_stream, bindings, bandpass, flat_voltage,
            notch_freq, channel_strategy="keep_all",
            quality_preset=quality_preset,
        )
        qc = raw.info.get("temp", {}).get("quality_check", {})
        raw.info["bads"] = list(qc.get("bads_combined", []))
        summary["n_bad_detected"] = len(raw.info["bads"])
        summary["quality_score"] = qc.get("quality_score")
        os.makedirs(out_dir, exist_ok=True)
        _write_qc_sidecar(qc, list(raw.info["ch_names"]), out_dir, subject_id)
        eeg_info = epoch_eeg_all(
            raw, events, marker_dict, task_timings, out_dir, subject_id
        )

    manifest = []
    if not no_video:
        video_streams = _stream_by_type(streams, "Video")
        if not video_streams:
            print("  [skip] no video stream in this recording.")
        elif not video_path:
            print("  [skip] video stream present but no raw .avi resolved for this subject.")
        else:
            segments = epoch_video_segments(
                video_streams[0], marker_stream, task_timings
            )
            # Keep only trials that produced a saved epoch (MNE drops windows past
            # the recording bounds). No rejection filtering here — that is deferred
            # to finalize, which drops the matching video via this manifest.
            if eeg_info:
                segments = _match_segments_to_eeg(segments, eeg_info)
            if not segments:
                print("  [skip] no stim epochs with video frames to write.")
            else:
                video_root = os.path.join(out_dir, "video")
                manifest = write_epoch_clips(
                    video_path, segments, video_root, subject_id, fps_override=fps
                )
                print(f"  [video] wrote {len(manifest)} epoch clips to {video_root}")

    # The alignment manifest records the video<->EEG trial pairing; only write it
    # when the video side actually ran (else the 1:1 mismatch check is spurious).
    if not no_video and (manifest or eeg_info):
        os.makedirs(out_dir, exist_ok=True)
        _write_alignment_manifest(manifest, eeg_info, out_dir, subject_id)

    summary["task_counts"] = {t: s["n_epochs"] for t, s in eeg_info.items()}
    summary["excluded_tasks"] = []          # exclusion is a finalize decision
    summary["video_present"] = bool(manifest)
    summary["paired_trials"] = len(manifest)
    return summary


def _pair_marker_mode(
    streams, marker_stream, xdf_path, video_path, subject_id, out_dir,
    bindings, bandpass, flat_voltage, notch_freq, channel_strategy,
    quality_preset, exclude_phases, fps, no_eeg, no_video, summary,
):
    """Legacy marker-to-marker export: a filtered Raw ``.fif`` + one clip per
    marker span. Whichever modality is present is processed; the other is
    skipped with a warning."""
    import mne

    if not no_eeg:
        eeg_stream = _select_eeg(streams, name=None)
        if eeg_stream is None:
            print("  [skip] no EEG stream in this recording.")
        else:
            raw, events, _marker_dict = align_eeg(
                eeg_stream, marker_stream, bindings, bandpass, flat_voltage,
                notch_freq, channel_strategy=channel_strategy,
                quality_preset=quality_preset,
            )
            qc = raw.info.get("temp", {}).get("quality_check", {})
            summary["n_bad_channels"] = len(qc.get("bads_combined", qc.get("bads", [])))
            os.makedirs(out_dir, exist_ok=True)
            raw_path = os.path.join(out_dir, f"sub-{subject_id}_eeg_raw.fif")
            eve_path = os.path.join(out_dir, f"sub-{subject_id}_eve.fif")
            raw.save(raw_path, overwrite=True)
            mne.write_events(eve_path, events, overwrite=True)
            print(f"  [eeg] saved {raw_path}")
            print(f"  [eeg] saved {eve_path}  ({len(events)} events)")

    written = []
    if not no_video:
        video_streams = _stream_by_type(streams, "Video")
        if not video_streams:
            print("  [skip] no video stream in this recording.")
        elif not video_path:
            print("  [skip] video stream present but no raw .avi resolved for this subject.")
        else:
            segments = video_segments(
                video_streams[0], marker_stream, exclude_phases=exclude_phases
            )
            if not segments:
                print("  [skip] no non-empty video segments to write.")
            else:
                video_out = os.path.join(out_dir, "video")
                written = split_video(video_path, segments, video_out, fps_override=fps)
                print(f"  [video] wrote {len(written)} clips to {video_out}")

    summary["video_present"] = bool(written)
    summary["paired_trials"] = len(written)
    return summary
