"""Compatibility shims for older checkouts of the analysis repo.

The pipelines reuse the published preprocessing code live from the analysis
repo (see ``synapse_qc.paths.synapse_repo``). Different checkouts of that repo
are not identical, so a feature this project depends on may be missing. Rather
than editing the analysis repo -- which is a separate project with its own
history -- the gap is patched here, at import time, and only when absent.
"""
import inspect

import numpy as np


def _source_of(fn):
    try:
        return inspect.getsource(fn)
    except (OSError, TypeError):
        return ""


def supports_keep_all(utils):
    """Does this checkout's ``create_mne`` know ``channel_strategy='keep_all'``?"""
    return "keep_all" in _source_of(utils.create_mne)


def ensure_keep_all(utils):
    """Give ``utils.create_mne`` a ``keep_all`` strategy if it lacks one.

    ``pair_video`` is detect-and-defer: it must run QC and filtering but leave
    every channel untouched, so ``finalize_dataset`` can apply the channel
    strategy later (``av_align.pair_recording`` therefore hardcodes
    ``channel_strategy='keep_all'``). Older checkouts of ``create_mne`` only
    accept interpolate / drop / zero_mask and raise ``ValueError: Unknown
    channel_strategy: keep_all``.

    The shim exploits the fact that ``create_mne``'s channel-handling block is
    guarded by ``if len(bads) > 0``. Wrapping ``quality_check`` so it reports an
    empty ``bads_combined`` makes that block a no-op -- which *is* keep_all --
    and the real bad-channel list is written back afterwards onto the very same
    result dict, which ``create_mne`` stored by reference in
    ``raw.info['temp']['quality_check']``. ``av_align`` reads the bads from
    there, so nothing downstream can tell the difference.

    Returns True if a shim was installed, False if the checkout already
    supported it.
    """
    if supports_keep_all(utils):
        return False

    orig_create_mne = utils.create_mne

    def _create_mne(*args, **kwargs):
        if kwargs.get("channel_strategy") != "keep_all":
            return orig_create_mne(*args, **kwargs)

        captured = {}
        orig_qc = utils.quality_check

        def _quality_check(*qa, **qk):
            res = orig_qc(*qa, **qk)
            captured["res"] = res
            captured["bads"] = list(res.get("bads_combined", []))
            # Hide the bads so create_mne's dispatch block is skipped entirely:
            # no interpolation, no dropping, no zeroing. That is keep_all.
            res["bads_combined"] = []
            return res

        utils.quality_check = _quality_check
        try:
            kw = dict(kwargs)
            # Never reached (bads is empty), but must be a value this checkout
            # accepts so the argument validation upstream does not object.
            kw["channel_strategy"] = "zero_mask"
            out = orig_create_mne(*args, **kw)
        finally:
            utils.quality_check = orig_qc

        if "res" in captured:
            # Same dict object create_mne stored in raw.info['temp'].
            captured["res"]["bads_combined"] = captured["bads"]
            raw = out[0] if isinstance(out, tuple) else out
            try:
                raw.info["bads"] = list(captured["bads"])
                names = list(raw.info["ch_names"])
                mask = np.array([ch not in captured["bads"] for ch in names])
                raw.info.setdefault("temp", {})["channel_mask"] = mask
            except Exception:  # noqa: BLE001 - cosmetic only; av_align re-reads qc
                pass
        return out

    utils.create_mne = _create_mne
    return True
