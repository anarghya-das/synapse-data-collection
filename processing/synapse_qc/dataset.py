"""Dataset transforms, and an optional view-based loader.

`finalize_dataset` turns the shared ``processed/eeg/`` tree into a dataset
variant by applying two decisions: a channel strategy and PTP epoch rejection.
Both transforms live HERE rather than in the pipeline, so the builder and any
reader run the same code. A second implementation of the same computation is a
drift waiting to happen — this repo already carries one hard-won lesson about
exactly that (the two `quality_check`s; see the repo-root CLAUDE.md).

Variants come in two layouts, chosen by ``dataset_layout`` in
``conf/finalize.yaml``:

* ``materialized`` (default) — the transformed epochs are written as ``.fif``
  under ``<variant>/<PID>/eeg/``. Directly loadable with ``mne.read_epochs()``,
  self-contained, ~390 MB per variant.
* ``view`` — only the decisions are stored (``sub-<PID>_epochs.json`` +
  ``channel_mask.npy``) and :func:`load_epochs` replays the transforms against
  ``processed/eeg/`` on demand. ~2 MB per variant, but useless without that tree.

Views are worth it when you are sweeping channel strategies; materialized is
worth it when the dataset has to stand on its own. Use
``scripts/export_dataset.py`` to turn either into a shareable bundle.

    from synapse_qc import dataset
    ep = dataset.load_epochs(variant_dir, "EXP51", "ast")   # view variants only
    al = dataset.load_alignment(variant_dir, "EXP51")       # trial index

``eeg_epoch_index`` in the alignment indexes the finalized epochs (row k is row
k); ``source_epoch_index`` indexes the untouched file under ``processed/eeg/``.
"""

from __future__ import annotations

import csv
import json
import os

import numpy as np

# Written into every variant so a reader can tell a view from a materialised
# copy without guessing from the file list.
LAYOUT_VIEW = "view"
LAYOUT_MATERIALIZED = "materialized"


# --------------------------------------------------------------------------- #
# The two transforms. One implementation, shared by the builder and the loader.
# --------------------------------------------------------------------------- #
def apply_channel_strategy(epochs, bads, strategy, montage_file):
    """Apply ``strategy`` to a 16-channel ``Epochs``; returns
    ``(epochs, mask, ch_names)`` where ``mask[i] == 1`` means channel ``i``
    carries real measured signal (0 = interpolated / masked / dropped).

    * interpolate — spline-interpolate bads from neighbours (fixed 16 ch); mask
      marks the interpolated channels 0.
    * zero_mask   — zero the bad channels (fixed 16 ch); mask marks them 0.
    * drop        — remove bad channels (variable ch count); mask is all-ones.
    * keep_all    — leave the raw bad channels untouched (fixed 16 ch); mask
      marks them 0. The honest "give the model the data + a mask" option.

    NB ``interpolate`` is the one strategy that is not a pure view: it synthesises
    samples. It is deterministic given (bads, montage), so the loader reproduces
    it exactly rather than storing the result.
    """
    import mne

    orig_names = list(epochs.ch_names)
    mask = np.array([0 if ch in bads else 1 for ch in orig_names], dtype=np.int8)

    if not bads or strategy == "keep_all":
        return epochs, mask, orig_names

    if strategy == "interpolate":
        md = np.load(montage_file)
        montage = mne.channels.make_dig_montage(
            ch_pos=dict(zip(md["labels"], md["points"])),
            nasion=md["nasion"], lpa=md["lpa"], rpa=md["rpa"], coord_frame="head")
        epochs.set_montage(montage)
        epochs.info["bads"] = list(bads)
        epochs.interpolate_bads(reset_bads=True, verbose=False)
        return epochs, mask, orig_names

    if strategy == "zero_mask":
        bad_idx = [orig_names.index(ch) for ch in bads]
        epochs._data[:, bad_idx, :] = 0.0
        epochs.info["bads"] = []
        return epochs, mask, orig_names

    if strategy == "drop":
        epochs.drop_channels(bads)
        kept = list(epochs.ch_names)
        return epochs, np.ones(len(kept), dtype=np.int8), kept

    raise ValueError(f"unknown channel_strategy: {strategy}")


def reject_epochs(epochs, mask, rej):
    """PTP z-score rejection over the GOOD channels only — a noisy bad channel
    cannot drag the threshold. Returns
    ``(kept_positions, n_before, n_after, excluded, reason)``; ``kept_positions``
    index the *input* epochs.
    """
    n_before = len(epochs)
    z = rej.get("z_threshold", 3)
    min_epochs = rej.get("min_epochs", 5)
    max_reject_pct = rej.get("max_reject_pct", 50)
    enabled = rej.get("enabled", True)

    kept = list(range(n_before))
    if enabled and n_before >= 3:
        data = epochs.get_data(copy=True)
        good = np.where(mask == 1)[0]
        if len(good) == 0:
            good = np.arange(data.shape[1])
        ptps = np.ptp(data[:, good, :], axis=2).max(axis=1)
        thresh = ptps.mean() + z * ptps.std()
        bad = np.where(ptps > thresh)[0]
        if len(bad):
            epochs.drop(bad, reason="PTP_ZSCORE", verbose=False)
            drop = {int(b) for b in bad}
            kept = [i for i in range(n_before) if i not in drop]

    n_after = len(epochs)
    pct = ((n_before - n_after) / n_before * 100) if n_before else 0.0
    excluded, reason = False, ""
    if enabled and n_before >= 3:
        if n_after < min_epochs:
            excluded, reason = True, f"<{min_epochs} epochs survive"
        elif pct > max_reject_pct:
            excluded, reason = True, f">{max_reject_pct}% rejected"
    return kept, n_before, n_after, excluded, reason


# --------------------------------------------------------------------------- #
# Reading a variant
# --------------------------------------------------------------------------- #
def read_manifest(variant_dir):
    path = os.path.join(variant_dir, "manifest.json")
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return json.load(fh)


def _spec(variant_dir, pid):
    path = os.path.join(variant_dir, pid, f"sub-{pid}_epochs.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. A materialised (pre-view) variant has .fif files "
            f"under {pid}/eeg/ instead — read those directly."
        )
    with open(path) as fh:
        return json.load(fh)


def subjects(variant_dir):
    """Subject ids in this variant, in sorted order."""
    return sorted(
        d for d in os.listdir(variant_dir)
        if os.path.isdir(os.path.join(variant_dir, d))
        and os.path.exists(os.path.join(variant_dir, d, f"sub-{d}_channels.json"))
    )


def channel_mask(variant_dir, pid):
    """``(mask, ch_names)`` — ``mask[i] == 1`` means real measured signal."""
    with open(os.path.join(variant_dir, pid, f"sub-{pid}_channels.json")) as fh:
        meta = json.load(fh)
    return np.array(meta["mask"], dtype=np.int8), meta["ch_names"]


def load_alignment(variant_dir, pid):
    """Surviving (EEG epoch, video clip) pairs; ``[]`` if the subject had no
    video."""
    path = os.path.join(variant_dir, pid, f"sub-{pid}_alignment.csv")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return list(csv.DictReader(fh))


def load_epochs(variant_dir, pid, task, base=None, montage_file=None):
    """Reconstruct one finalized ``Epochs`` for ``pid``/``task``.

    Reads the untouched source epochs from ``processed/eeg/``, replays the
    variant's channel strategy, then selects the epochs the build kept. The
    result equals what the materialised variant used to hold on disk.

    Raises ``KeyError`` if the task was excluded by the build.
    """
    import mne

    spec = _spec(variant_dir, pid)
    tasks = spec["tasks"]
    if task not in tasks:
        raise KeyError(f"{pid} has no task {task!r} in this variant")
    entry = tasks[task]
    if entry.get("excluded"):
        raise KeyError(f"{pid}/{task} was excluded by the build: "
                       f"{entry.get('reason', 'no reason recorded')}")

    base = base or spec["base"]
    src = os.path.join(base, entry["source_file"])
    epochs = mne.read_epochs(src, preload=True, verbose=False)

    with open(os.path.join(variant_dir, pid, f"sub-{pid}_channels.json")) as fh:
        meta = json.load(fh)
    epochs, _mask, _names = apply_channel_strategy(
        epochs, meta["bads_detected"], meta["strategy"],
        montage_file or spec.get("montage_file"))

    kept = entry["kept"]
    if kept != list(range(len(epochs))):
        epochs = epochs[kept]
    return epochs


def load_subject(variant_dir, pid, base=None, montage_file=None):
    """``{task: Epochs}`` for every task this variant kept for ``pid``."""
    spec = _spec(variant_dir, pid)
    out = {}
    for task, entry in spec["tasks"].items():
        if entry.get("excluded"):
            continue
        out[task] = load_epochs(variant_dir, pid, task, base, montage_file)
    return out
