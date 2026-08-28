"""Core CEEGrid EEG quality-check routines.

These functions are vendored (copied verbatim, with light trimming) from the
main analysis repo's ``preprocessing/utils.py``
(``/Users/anarghya/Developer/research/synapse/preprocessing/utils.py``) so the
data repo can run quality analysis without depending on the full 2400-line
``utils`` module. Only the pieces needed for QC are kept:

    CEEGRID_QUALITY_PRESETS  - threshold presets tuned for ear-EEG
    closest_points_vector    - marker->EEG index alignment (used by parse_xdf)
    parse_xdf                - load XDF, return (markers, eeg_stream, insert_pts)
    load_eeg_stream          - marker-independent loader (used by the driver)
    create_raw               - build an MNE Raw from an OpenBCI EEG stream
    quality_check            - the actual per-channel/overall QC
    generate_quality_report  - human-readable text report from a QC result

If the QC algorithm changes upstream, re-sync this file. The canonical
implementation lives in the analysis repo.
"""
import numpy as np
import mne
import pyxdf
from scipy.stats import median_abs_deviation


# =========================
# CEEGRID QUALITY PRESETS
# =========================
# Threshold configurations tuned for around-the-ear CEEGrid EEG.
# Ear-EEG typically has lower amplitude than scalp EEG.
CEEGRID_QUALITY_PRESETS = {
    'default': {
        'flat_voltage': 0.5,                     # uV - relaxed for ear-EEG lower amplitude
        'bad_percent': 30,                       # % - allow more transient flat periods
        'sd_floor_uv': 0.3,                      # uV - SD below this (post-HP) = dead channel
        'qc_highpass': 1.0,                      # Hz - HP copy for the dead-channel SD floor
        'correlation_threshold': (0.15, 0.85),   # wider bounds for ear-EEG (LEGACY method)
        # --- robust method (filter-first; see quality/QC_methodology_review.md) ---
        'qc_bandpass': (1.0, 50.0),              # Hz - internal band-pass applied before ALL criteria
        'corr_low': 0.40,                        # max off-diag corr below this = bad (PREP-style low-corr)
        'corr_window_s': 1.0,                    # correlation scored in 1-s windows (PREP)
        'corr_bad_time_frac': 0.10,              # bad if it fails in >10% of windows.
                                                 # PREP uses 1%, calibrated on artifact-free
                                                 # scalp EEG. cEEGrid picks up jaw/facial EMG
                                                 # that briefly decorrelates healthy channels,
                                                 # so 1% flags 29% of all channels here (median
                                                 # score 75 -> 53) and drops CTRL02/EXP02 from
                                                 # the cohort. 10% leaves the cohort and median
                                                 # score unchanged while still catching the 19
                                                 # intermittent dropouts the whole-recording
                                                 # correlation missed. See
                                                 # docs/QC_grade_bands_review.md.
        'corr_high_report': 0.999,               # near-identical pair REPORTED as possible bridging (not scored)
        'z_thresh': 3.0,                         # |robust z| (median/MAD) on log-variance (FASTER-style)
    },
    'strict': {
        'flat_voltage': 0.3,
        'bad_percent': 20,
        'sd_floor_uv': 0.5,
        'qc_highpass': 1.0,
        'correlation_threshold': (0.2, 0.8),
        'qc_bandpass': (1.0, 50.0),
        'corr_low': 0.50,
        'corr_window_s': 1.0,
        'corr_bad_time_frac': 0.05,
        'corr_high_report': 0.998,
        'z_thresh': 2.5,
    },
    'lenient': {
        'flat_voltage': 1.0,
        'bad_percent': 40,
        'sd_floor_uv': 0.2,
        'qc_highpass': 1.0,
        'correlation_threshold': (0.1, 0.9),
        'qc_bandpass': (1.0, 50.0),
        'corr_low': 0.30,
        'corr_window_s': 1.0,
        'corr_bad_time_frac': 0.20,
        'corr_high_report': 0.9995,
        'z_thresh': 3.5,
    },
}

# Standard 16-channel CEEGrid layout (OpenBCI). L = left ear, R = right ear.
CEEGRID_CH_LABELS = ['L01', 'L02', 'L04', 'L05', 'L07', 'L08', 'L09', 'L10',
                     'R01', 'R02', 'R04', 'R05', 'R07', 'R08', 'R09', 'R10']
# Neurable headset variant (12 channels).
NEURABLE_CH_LABELS = ['L01', 'L02', 'L04', 'L05', 'L07', 'L08',
                      'R01', 'R02', 'R04', 'R05', 'R07', 'R08']


def closest_points_vector(eeg_timestamps, marker_timestamps):
    """Map each marker timestamp to the index of its nearest EEG sample."""
    indices = np.searchsorted(eeg_timestamps, marker_timestamps)
    closest_eeg_indices = indices.copy()

    mask_begin = indices == 0
    closest_eeg_indices[mask_begin] = 0

    mask_end = indices == len(eeg_timestamps)
    closest_eeg_indices[mask_end] = len(eeg_timestamps) - 1

    mask_middle = (indices > 0) & (indices < len(eeg_timestamps))
    prev_times = eeg_timestamps[indices[mask_middle] - 1]
    next_times = eeg_timestamps[indices[mask_middle]]
    marker_times_middle = marker_timestamps[mask_middle]

    diff_prev = marker_times_middle - prev_times
    diff_next = next_times - marker_times_middle
    closest_eeg_indices[mask_middle] = np.where(
        diff_prev <= diff_next, indices[mask_middle] - 1, indices[mask_middle]
    )
    return closest_eeg_indices


def parse_xdf(file_path, eeg_stream_name="obci_eeg1"):
    """Load an XDF and return (marker_data, eeg_stream, eeg_insert_points).

    Raises StopIteration if the file has no Markers stream or no matching EEG
    stream. For QC you usually want :func:`load_eeg_stream`, which does not
    require a marker stream.
    """
    data, header = pyxdf.load_xdf(file_path)
    marker_stream = next(
        stream for stream in data if stream["info"]["type"][0] == "Markers"
    )
    eeg_stream = next(
        stream for stream in data
        if stream["info"]["type"][0] == "EEG"
        and stream["info"]["name"][0] == eeg_stream_name
    )
    marker_timestamps = marker_stream["time_stamps"]
    marker_data = np.array(marker_stream["time_series"]).squeeze()
    eeg_timestamps = eeg_stream["time_stamps"]
    eeg_insert_points = closest_points_vector(eeg_timestamps, marker_timestamps)
    return marker_data, eeg_stream, eeg_insert_points


def load_eeg_stream(file_path, eeg_stream_name="obci_eeg1"):
    """Load just the EEG stream from an XDF, ignoring markers.

    Unlike :func:`parse_xdf`, this does not require a Markers stream, so it
    still works for recordings where only the EEG was saved. Returns the
    pyxdf EEG-stream dict. Raises StopIteration if no matching EEG stream
    exists (i.e. a "no EEG data stream" participant).
    """
    data, _ = pyxdf.load_xdf(file_path)
    eeg_stream = next(
        stream for stream in data
        if stream["info"]["type"][0] == "EEG"
        and stream["info"]["name"][0] == eeg_stream_name
    )
    return eeg_stream


def _n_samples(stream):
    import numpy as _np
    return int(_np.asarray(stream["time_series"]).size)


def device_of_stream_name(name):
    """Classify an EEG stream name as 'OpenBCI', 'Neurable', or 'unknown'."""
    n = name.lower()
    if n.startswith("obci"):
        return "OpenBCI"
    if "neurable" in n or "mw75" in n:
        return "Neurable"
    return "unknown"


def detect_devices(file_path):
    """Return the set of device types present (from non-empty EEG streams).

    Loads the XDF, so call sparingly. Used to populate the per-participant
    device columns -- e.g. EXP10 has separate OpenBCI and Neurable sessions.
    """
    data, _ = pyxdf.load_xdf(file_path)
    out = set()
    for s in data:
        if s["info"]["type"][0] == "EEG" and _n_samples(s) > 0:
            out.add(device_of_stream_name(s["info"]["name"][0]))
    return out


def select_obci_streams(file_path):
    """Locate the raw and filtered OpenBCI streams and report what was found.

    SYNAPSE XDFs carry up to two OpenBCI EEG streams (see project notes):
      * ``obci_eeg1`` = RAW (the canonical QC input; matches the published pipeline)
      * ``obci_eeg2`` = FILTERED by the OpenBCI GUI (~5-50 Hz band-pass + 60 Hz notch)

    Identification is by stream NAME, which is consistent across the dataset
    (verified: obci_eeg1 always carries a large DC offset; obci_eeg2 has DC=0).

    Returns ``(raw_stream, filtered_stream, status, detail)`` where a stream is
    None if absent/empty. ``status`` describes the RAW (canonical) stream:

      * ``"ok"``            - non-empty obci_eeg1 present (filtered may or may not be)
      * ``"empty_eeg"``     - obci EEG stream(s) present but 0 samples (e.g. EXP44)
      * ``"non_obci_eeg"``  - only a different device present, e.g. 14-ch Neurable
                              MW75 (EXP32). ``detail`` names it; not scored here.
      * ``"no_eeg_stream"`` - no EEG stream at all (markers/video/PPG only)
    """
    data, _ = pyxdf.load_xdf(file_path)
    eeg_streams = [s for s in data if s["info"]["type"][0] == "EEG"]
    if not eeg_streams:
        return None, None, "no_eeg_stream", ""

    def by_name(name):
        for s in eeg_streams:
            if s["info"]["name"][0].lower() == name and _n_samples(s) > 0:
                return s
        return None

    raw = by_name("obci_eeg1")
    filtered = by_name("obci_eeg2")

    obci_any = [s for s in eeg_streams if s["info"]["name"][0].lower().startswith("obci")]
    if raw is not None:
        return raw, filtered, "ok", raw["info"]["name"][0]
    if obci_any:
        # OpenBCI stream(s) exist but obci_eeg1 is empty / unusable.
        # Fall back to any non-empty obci stream if one exists (rare).
        nonempty = [s for s in obci_any if _n_samples(s) > 0]
        if nonempty:
            return nonempty[0], filtered, "ok", nonempty[0]["info"]["name"][0]
        return None, None, "empty_eeg", "obci EEG stream present but 0 samples"

    nonempty = [s for s in eeg_streams if _n_samples(s) > 0]
    if nonempty:
        s = nonempty[0]
        return None, None, "non_obci_eeg", f"{s['info']['name'][0]} ({s['info']['channel_count'][0]}ch)"
    return None, None, "empty_eeg", "EEG stream(s) present but all empty"


def create_raw(eeg_stream, neurable=False, resampled_freq=125):
    """Build an MNE Raw from an OpenBCI EEG stream (uV -> V), resample to 125 Hz."""
    ch_labels = NEURABLE_CH_LABELS if neurable else CEEGRID_CH_LABELS
    sampling_rate = float(eeg_stream["info"]["nominal_srate"][0])
    # OpenBCI EEG data is in microvolts; convert to volts for MNE.
    eeg_data = eeg_stream["time_series"].T * 1e-6
    if neurable:
        eeg_data = eeg_data[:-2, :]
    info = mne.create_info(ch_names=ch_labels, sfreq=sampling_rate, ch_types="eeg")
    raw = mne.io.RawArray(eeg_data, info)
    if sampling_rate != 125:
        raw = raw.resample(resampled_freq)
    return raw


def windowed_max_corr(data, sfreq, window_s=1.0):
    """PREP-style per-window correlation.

    Returns ``(max_corr, n_windows)`` where ``max_corr`` has shape
    ``(n_channels, n_windows)`` and holds each channel's **maximum absolute
    off-diagonal correlation** within that window. A channel that is flat in a
    window (zero SD, so correlation is undefined) gets 0.0 there -- it correlates
    with nothing, which is exactly the disconnected case this detects.

    Windowing matters: a whole-recording correlation averages over time, so an
    electrode that detaches part-way through can still clear the threshold.
    PREP scores each 1-s window and flags a channel on the FRACTION of windows
    that fail (see ``quality_check``'s ``corr_bad_time_frac``).
    """
    n_ch, n_times = data.shape
    win_len = max(2, int(round(window_s * sfreq)))
    n_win = n_times // win_len
    if n_ch < 2 or n_win < 1:
        return np.ones((n_ch, max(n_win, 1))), max(n_win, 1)

    # (n_ch, n_win, win_len); trailing partial window is dropped.
    d = data[:, :n_win * win_len].reshape(n_ch, n_win, win_len)
    d = d - d.mean(axis=2, keepdims=True)
    sd = d.std(axis=2)
    good = sd > 0
    with np.errstate(invalid='ignore', divide='ignore'):
        dn = np.where(good[:, :, None], d / sd[:, :, None], 0.0)

    # Per-window correlation matrices: (n_win, n_ch, n_ch).
    corr = np.einsum('iwt,jwt->wij', dn, dn) / win_len
    np.abs(corr, out=corr)
    idx = np.arange(n_ch)
    corr[:, idx, idx] = -np.inf                      # exclude self-correlation
    max_corr = corr.max(axis=2).T                    # (n_ch, n_win)
    max_corr[~good] = 0.0                            # flat window: no correlation
    return np.nan_to_num(max_corr, nan=0.0, posinf=0.0, neginf=0.0), n_win


def quality_check(raw, flat_voltage=None, correlation_threshold=None, plot_corr=False,
                  tmin=None, tmax=None, events=None, event_margin=10.0,
                  preset='default', bad_percent=None, sd_floor_uv=None,
                  qc_highpass=None, method='robust', verbose=True):
    """Check EEG data quality with optional time-windowing for CEEGrid data.

    Returns a dict of quality metrics including bad-channel sets
    (``bads_flat`` / ``bads_variance`` / ``bads_corr`` / ``bads_combined``),
    per-channel variances, SD (uV), correlations, SNR estimates, ear
    asymmetry, and an overall ``quality_score`` (0-100 = % good channels).

    ``method`` selects the scoring algorithm:

    ``'robust'`` (default, filtering-invariant; see quality/QC_methodology_review.md)
      All criteria are computed on a copy band-passed to ``qc_bandpass`` (1-50 Hz),
      so raw (obci_eeg1) and GUI-filtered (obci_eeg2) inputs converge. Criteria:
        * flat:   amplitude < ``flat_voltage`` uV for > ``bad_percent`` of time
        * dead:   SD < ``sd_floor_uv`` uV (absolute low floor)
        * noisy:  robust z (median/MAD) of log-variance > ``z_thresh`` (FASTER-style)
        * corr:   PREP-style WINDOWED low correlation -- the max |off-diagonal|
                  correlation is scored in ``corr_window_s`` (1 s) windows and the
                  channel is bad when it falls below ``corr_low`` in more than
                  ``corr_bad_time_frac`` (10%) of them. Catches an electrode that
                  detaches part-way through, which a whole-recording correlation
                  averages away. High correlation is REPORTED
                  (``bads_highcorr``, possible bridging) but NOT counted as bad.

    ``'legacy'`` (the original metric; kept for comparison)
      flat + dead on a 1 Hz HP copy + correlation OUTSIDE ``correlation_threshold``,
      all computed on the UNFILTERED signal. On raw data the high-corr bound flags
      common-mode DC drift as bad -- see the methodology review.
    """
    config = CEEGRID_QUALITY_PRESETS.get(preset, CEEGRID_QUALITY_PRESETS['default']).copy()
    if flat_voltage is not None:
        config['flat_voltage'] = flat_voltage
    if correlation_threshold is not None:
        config['correlation_threshold'] = correlation_threshold
    if bad_percent is not None:
        config['bad_percent'] = bad_percent
    if sd_floor_uv is not None:
        config['sd_floor_uv'] = sd_floor_uv
    if qc_highpass is not None:
        config['qc_highpass'] = qc_highpass

    flat_voltage_uv = config['flat_voltage']
    bad_pct = config['bad_percent']
    sd_floor = config['sd_floor_uv']
    qc_hp = config['qc_highpass']
    low_threshold, high_threshold = config['correlation_threshold']

    duration_total = raw.times[-1] - raw.times[0]

    tmin_used = tmin
    tmax_used = tmax
    if tmin is None and tmax is None and events is not None:
        sfreq = raw.info['sfreq']
        first_event_time = events[:, 0].min() / sfreq
        last_event_time = events[:, 0].max() / sfreq
        tmin_used = max(0, first_event_time - event_margin)
        tmax_used = min(raw.times[-1], last_event_time + event_margin)
        if verbose:
            print(f"[quality_check] Auto-detected task bounds: {tmin_used:.1f}s to {tmax_used:.1f}s")

    if tmin_used is not None or tmax_used is not None:
        tmin_crop = tmin_used if tmin_used is not None else raw.times[0]
        tmax_crop = tmax_used if tmax_used is not None else raw.times[-1]
        raw_qc = raw.copy().crop(tmin=tmin_crop, tmax=tmax_crop)
        duration_analyzed = raw_qc.times[-1] - raw_qc.times[0]
        if verbose:
            print(f"[quality_check] Analyzing {duration_analyzed:.1f}s of {duration_total:.1f}s total recording")
    else:
        raw_qc = raw
        tmin_used = raw.times[0]
        tmax_used = raw.times[-1]
        duration_analyzed = duration_total

    ch_names_qc = list(raw_qc.ch_names)
    flat_voltage_volts = flat_voltage_uv * 1e-6
    bads_noisy = []
    bads_highcorr = []

    if method == 'robust':
        # --- filter-first normalization (1-50 Hz): makes the metric
        #     filtering-invariant so raw and GUI-filtered inputs converge. ---
        bp_lo, bp_hi = config.get('qc_bandpass', (1.0, 50.0))
        raw_norm = raw_qc.copy().filter(l_freq=bp_lo, h_freq=bp_hi,
                                        picks='eeg', verbose=False)
        data_qc = raw_norm.get_data()
        raw_for_flat = raw_norm

        # flat (on normalized data, so a DC offset is no longer mistaken for signal)
        _, bads_flat = mne.preprocessing.annotate_amplitude(
            raw_for_flat, flat=dict(eeg=flat_voltage_volts), bad_percent=bad_pct)
        bads_flat = list(bads_flat)

        variances = data_qc.var(axis=1)
        sd_uv = data_qc.std(axis=1) * 1e6          # already band-passed
        variance_threshold = (sd_floor * 1e-6) ** 2

        # dead: absolute low SD floor
        bads_variance = [ch_names_qc[i] for i, s in enumerate(sd_uv) if s < sd_floor]

        # noisy: robust-z (median/MAD) outlier on the HIGH side of log-variance
        z_thresh = config.get('z_thresh', 3.0)
        logv = np.log10(np.maximum(variances, 1e-30))
        med, mad = np.median(logv), median_abs_deviation(logv)
        if mad > 0:
            rz = (logv - med) / (1.4826 * mad)
            bads_noisy = [ch_names_qc[i] for i in range(len(logv)) if rz[i] > z_thresh]

        # correlation: PREP-style. A good channel correlates well with at least
        # ONE other channel, so use the MAX off-diagonal correlation (mean is
        # inappropriate for ear-EEG, where the contralateral ear is weakly
        # correlated and drags a healthy channel's mean down). LOW max = bad
        # (disconnected); very HIGH max = possible bridging (reported, not scored).
        if data_qc.shape[0] == 1:
            corr_matrix = np.array([[1.0]])
            max_offdiag = np.array([1.0])
        else:
            corr_matrix = np.corrcoef(data_qc)
            cm = corr_matrix.copy()
            np.fill_diagonal(cm, np.nan)
            with np.errstate(invalid='ignore'):
                max_offdiag = np.nanmax(cm, axis=1)   # nan for a flat/constant channel
        mean_corr = corr_matrix.mean(axis=1)          # kept for reporting only
        corr_low = config.get('corr_low', 0.40)
        corr_hi_rep = config.get('corr_high_report', 0.985)

        # PREP-style WINDOWED low-correlation criterion: score each window, then
        # flag a channel when it fails in more than `corr_bad_time_frac` of them.
        # (A single whole-recording correlation misses an electrode that detaches
        # part-way through -- see docs/QC_grade_bands_review.md.)
        win_s = config.get('corr_window_s', 1.0)
        bad_frac_thresh = config.get('corr_bad_time_frac', 0.01)
        win_max_corr, n_corr_windows = windowed_max_corr(
            data_qc, raw_qc.info['sfreq'], window_s=win_s)
        corr_bad_frac = (win_max_corr < corr_low).mean(axis=1)
        bads_corr = [ch_names_qc[i] for i in range(len(corr_bad_frac))
                     if corr_bad_frac[i] > bad_frac_thresh]
        # Bridging stays a whole-recording report (it is a stationary property).
        bads_highcorr = [ch_names_qc[i] for i in range(len(max_offdiag))
                         if np.isfinite(max_offdiag[i]) and max_offdiag[i] >= corr_hi_rep]
        corr_thresh_used = (float(corr_low), float(corr_hi_rep))
    else:
        # --- legacy: criteria on the UNFILTERED signal ---
        _, bads_flat = mne.preprocessing.annotate_amplitude(
            raw_qc, flat=dict(eeg=flat_voltage_volts), bad_percent=bad_pct)
        bads_flat = list(bads_flat)

        data_qc = raw_qc.get_data()
        variances = data_qc.var(axis=1)
        sd_uv = (raw_qc.copy()
                 .filter(l_freq=qc_hp, h_freq=None, picks='eeg', verbose=False)
                 .get_data().std(axis=1) * 1e6)
        bads_variance = [ch_names_qc[i] for i, s in enumerate(sd_uv) if s < sd_floor]
        variance_threshold = (sd_floor * 1e-6) ** 2

        if data_qc.shape[0] == 1:
            corr_matrix = np.array([[1.0]])
        else:
            corr_matrix = np.corrcoef(data_qc)
        mean_corr = corr_matrix.mean(axis=1)
        bads_corr = [ch_names_qc[i] for i, c in enumerate(mean_corr)
                     if (c < low_threshold) or (c > high_threshold)]
        corr_thresh_used = (float(low_threshold), float(high_threshold))
        # Legacy is whole-recording by definition; keep the keys uniform.
        corr_bad_frac = np.full(len(ch_names_qc), np.nan)
        n_corr_windows = 0

    if plot_corr:
        import matplotlib.pyplot as plt
        plt.imshow(corr_matrix, cmap='viridis', aspect='auto')
        plt.colorbar(label='Correlation Coefficient')
        plt.title('Channel Correlation Matrix')
        plt.xticks(ticks=np.arange(len(ch_names_qc)), labels=ch_names_qc, rotation=90)
        plt.yticks(ticks=np.arange(len(ch_names_qc)), labels=ch_names_qc)
        plt.tight_layout()
        plt.show()

    bads_custom = set(bads_flat) | set(bads_variance) | set(bads_corr) | set(bads_noisy)

    # Robust SNR estimate (peak-to-peak / MAD) on the same data the criteria used.
    mad_per_channel = median_abs_deviation(data_qc, axis=1)
    peak_to_peak = np.ptp(data_qc, axis=1)
    snr_estimate = peak_to_peak / (mad_per_channel + 1e-12)

    # Ear asymmetry (left vs right variance).
    left_idx = [i for i, ch in enumerate(raw_qc.ch_names) if ch.startswith('L')]
    right_idx = [i for i, ch in enumerate(raw_qc.ch_names) if ch.startswith('R')]
    if left_idx and right_idx:
        left_var = variances[left_idx].mean()
        right_var = variances[right_idx].mean()
        ear_asymmetry = abs(left_var - right_var) / (left_var + right_var + 1e-12)
    else:
        ear_asymmetry = None

    n_channels = len(raw_qc.ch_names)
    n_bad = len(bads_custom)
    quality_score = 100 * (1 - n_bad / n_channels)

    if verbose:
        print(f"[quality_check] Quality score: {quality_score:.0f}/100 ({n_bad}/{n_channels} bad channels)")
        if bads_custom:
            print(f"[quality_check] Bad channels: {list(bads_custom)}")

    return {
        'ch_names': list(raw_qc.ch_names),
        'method': method,
        'bads_flat': list(bads_flat),
        'bads_variance': bads_variance,
        'bads_noisy': bads_noisy,
        'bads_corr': bads_corr,
        'bads_highcorr': bads_highcorr,
        'bads_combined': list(bads_custom),
        'variances': variances,
        'variance_threshold': float(variance_threshold),
        'ch_sd_uv': sd_uv,
        'corr_matrix': corr_matrix,
        'mean_corr': mean_corr,
        'corr_bad_frac': corr_bad_frac,       # fraction of windows below corr_low
        'n_corr_windows': int(n_corr_windows),
        'correlation_threshold': corr_thresh_used,
        'flat_voltage_volts': float(flat_voltage_volts),
        'time_window': (float(tmin_used), float(tmax_used)),
        'duration_analyzed': float(duration_analyzed),
        'duration_total': float(duration_total),
        'snr_estimate': snr_estimate,
        'ear_asymmetry': ear_asymmetry,
        'quality_score': float(quality_score),
        'preset_used': preset,
        'config': config,
    }


def generate_quality_report(qc, ch_names=None, output_path=None):
    """Build a human-readable text report from a :func:`quality_check` result."""
    if ch_names is None:
        ch_names = qc.get('ch_names') or [f'Ch{i}' for i in range(len(qc['variances']))]

    lines = [
        "=" * 60,
        "CEEGrid EEG Quality Report",
        "=" * 60,
        "",
        f"Overall Quality Score: {qc['quality_score']:.1f}/100",
        f"Preset Used: {qc.get('preset_used', 'unknown')}",
        "",
        "Time Window Analyzed:",
        f"  - Start: {qc['time_window'][0]:.1f}s",
        f"  - End: {qc['time_window'][1]:.1f}s",
        f"  - Duration: {qc['duration_analyzed']:.1f}s of {qc['duration_total']:.1f}s total",
        "",
        "Bad Channels Summary:",
        f"  - Total bad: {len(qc['bads_combined'])}/{len(ch_names)}",
        f"  - Flat: {qc['bads_flat']}",
        f"  - Low variance (dead): {qc['bads_variance']}",
        f"  - Noisy (high-variance outlier): {qc.get('bads_noisy', [])}",
        f"  - Low correlation: {qc['bads_corr']}",
        f"  - High correlation (possible bridging; not scored): {qc.get('bads_highcorr', [])}",
        "",
        "Thresholds Used:",
        f"  - Flat voltage: {qc['flat_voltage_volts']*1e6:.2f} uV",
        f"  - Correlation bounds: {qc['correlation_threshold']}",
        f"  - Dead-channel SD floor: {qc['config'].get('sd_floor_uv', 'N/A')} uV "
        f"(on {qc['config'].get('qc_highpass', 'N/A')} Hz high-passed copy)",
        "",
        "Per-Channel Metrics:",
    ]
    for i, ch in enumerate(ch_names):
        if i < len(qc['variances']):
            status = "BAD" if ch in qc['bads_combined'] else "OK"
            snr = qc['snr_estimate'][i] if i < len(qc['snr_estimate']) else 0
            corr = qc['mean_corr'][i] if i < len(qc['mean_corr']) else 0
            var = qc['variances'][i]
            sd = qc['ch_sd_uv'][i] if i < len(qc['ch_sd_uv']) else 0
            lines.append(
                f"  {ch}: {status:3} | var={var:.2e} | sd={sd:6.3f}uV | "
                f"corr={corr:.3f} | snr={snr:.1f}"
            )

    if qc.get('ear_asymmetry') is not None:
        lines += ["", f"Ear Asymmetry Index: {qc['ear_asymmetry']:.3f}",
                  "  (0 = symmetric, 1 = completely asymmetric)"]
    lines.append("=" * 60)

    report = "\n".join(lines)
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)
    return report
