"""EEG epoching: XDF -> annotated, filtered MNE Raw + events.

**Vendored** from the analysis repo's ``preprocessing/utils.py`` (branch `main`,
commit e3aa291, 2026-08-28). Copied rather than rewritten so that
``build_dataset cohort=published`` still reproduces the published
``synapse_preprocessed.pkl`` bit-for-bit -- ``pipelines/compare.py`` is the
regression test for exactly that.

WHY IT LIVES HERE: this repo owns processing; the analysis repo should only ever
read a finished pickle. Importing the analysis repo at runtime made the pipeline
depend on which branch that checkout happened to be on, which already bit us
once (a checkout predating ``channel_strategy='keep_all'`` broke pairing).

Only these functions are vendored -- the transitive closure of ``read_data`` and
``create_mne``, which is what the pipelines actually call. ``create_raw``,
``quality_check``, ``closest_points_vector`` and ``parse_xdf`` are NOT copied:
this repo already has its own in :mod:`synapse_qc.qc_core`, and the QC one is
deliberately different (robust/windowed rather than the legacy metric).

If the upstream algorithm changes, re-vendor and re-run
``python -m pipelines.compare`` to confirm the published mirror still matches.
"""
import glob
import os
import re

import numpy as np
import mne
import pyxdf

from scipy.stats import median_abs_deviation

from .qc_core import (                      # this repo's own implementations
    closest_points_vector,
    create_raw,
    parse_xdf,
)

# NOTE ON QUALITY_CHECK -- there are two, deliberately.
#
# The one vendored below is the analysis repo's LEGACY metric (mean-correlation
# bounds on the unfiltered signal). It is the default here because
# ``build_dataset cohort=published`` must mirror the published pkl, which was
# built with it -- swapping in the robust metric changes the bad-channel sets on
# 23 of 28 subjects and breaks the reproduction check.
#
# ``synapse_qc.qc_core.quality_check`` is this repo's ROBUST, windowed,
# filtering-invariant replacement, and is what every QC entry point uses.
# ``pipelines/pair_video.py`` rebinds ``epoching.quality_check`` to it at run
# time, so the multimodal dataset gets the corrected metric while the published
# mirror stays faithful. Do not "unify" these.

__all__ = [
    "create_mappings", "create_events", "contralateral_reference",
    "select_event_ids", "create_mne", "read_data",
    "build_hed_event_mapping", "hed_events_array",
]


def _parse_marker_string(marker: str):
    """Parse a single marker string into structured facets.

    Supports tasks: PMT, HLT, LET, AST. Returns a dict of facets. Unknown or
    malformed markers are returned with minimal info. Parsing is intentionally
    permissive so downstream code can still operate when some markers are
    missing or slightly malformed.

        Marker formats handled (case-insensitive):
            pmt_<phase>
            hlt_<phase>-tone_<INT>dB
            let_<phase>-<TRIAL>_snr<SNR>
            ast_<phase>-<condition>-<stimulus_name>
            ast_<phase>-<stimulus_name>

        AST RULES:
            - Explicit condition tokens: 'trigger' or 'control'.
            - 'control' is normalized to disposition 'neutral'.
            - If condition token omitted (ast_<phase>-<stimulus>) the event is
                assumed to be a TRIGGER unless the stimulus part contains the word
                'control' (case-insensitive) in which case it's treated as NEUTRAL and
                the word 'control' is stripped from the stimulus label for cleanliness.
            - Downstream structures only expose 'neutral' and 'trigger' (no raw
                'control' term remains).

    Returns
    -------
    dict with keys:
      raw: original marker string
      task: one of {'pmt','hlt','let','ast','other'}
      phase: prestim|stim|poststim|response|other
      disposition: 'trigger'|'neutral'|'all'
      intensity_db: int or None (HLT)
      snr_db: int or None (LET)
      trial: int or None (LET) - NOTE: stored in metadata but NOT used in event names
    ast_condition: 'trigger'|'neutral'|None (AST)
      stimulus: stimulus identifier (LET trial, AST stimulus) or None
      hed_tags: list of preliminary HED-like tags (will be finalized later)

    Note
    ----
    Trial numbers are parsed and stored in the facets but are NOT included in the
    composite event names. This allows all trials of the same condition (e.g., same
    SNR level, same phase) to be pooled together under one event ID, which is the
    standard approach in EEG analysis for better statistical power.
    """
    m = (marker or '').strip()
    lower = m.lower()
    facets = {
        'raw': m,
        'task': 'other',
        'phase': 'other',
        'disposition': 'all',
        'intensity_db': None,
        'snr_db': None,
        'trial': None,
        'ast_condition': None,
        'stimulus': None,
        'hed_tags': []
    }

    # Early exit for obvious non-task markers
    if lower in {'start', 'end'}:
        facets['task'] = 'other'
        facets['phase'] = lower
        facets['hed_tags'] = [f'Task/Other', f'Phase/{lower.capitalize()}']
        return facets

    # Generic regex groups
    phase_pat = r'(prestim|stim|poststim|response)'

    # HLT
    hlt_re = re.compile(rf'^hlt_{phase_pat}-tone_(\d+)db$')
    mo = hlt_re.match(lower)
    if mo:
        phase, intensity = mo.group(1), mo.group(2)
        facets.update({
            'task': 'hlt',
            'phase': phase,
            'intensity_db': int(intensity),
            'stimulus': f'tone_{intensity}dB'
        })
        # No explicit neutral/trigger rule provided; keep 'all'. Users can reclassify later.
        facets['hed_tags'] = [
            'Task/HLT', f'Phase/{phase.capitalize()}', f'Stimulus/Auditory/Tone', f'Attribute/Intensity/{intensity}dB'
        ]
        return facets

    # LET
    let_re = re.compile(rf'^let_{phase_pat}-(\d+)_snr(\d+)$')
    mo = let_re.match(lower)
    if mo:
        phase, trial, snr = mo.group(1), mo.group(2), mo.group(3)
        facets.update({
            'task': 'let',
            'phase': phase,
            'trial': int(trial),
            'snr_db': int(snr),
            'stimulus': f'trial_{trial}',
        })
        # No rule for neutral/trigger: keep 'all'.
        facets['hed_tags'] = [
            'Task/LET', f'Phase/{phase.capitalize()}', f'Stimulus/Speech', f'Attribute/SNR/{snr}dB', f'Attribute/Trial/{trial}'
        ]
        return facets

    # AST
    # AST (explicit condition)
    ast_re = re.compile(rf'^ast_{phase_pat}-(trigger|control)-(.+)$')
    mo = ast_re.match(lower)
    if mo:
        phase, cond_raw, stim = mo.group(1), mo.group(2), mo.group(3)
        cond = 'neutral' if cond_raw == 'control' else 'trigger'
        facets.update({
            'task': 'ast',
            'phase': phase,
            'ast_condition': cond,
            'stimulus': stim,
            'disposition': cond
        })
        facets['hed_tags'] = [
            'Task/AST', f'Phase/{phase.capitalize()}', f'Condition/{cond.capitalize()}', f'Stimulus/Sound/{stim}'
        ]
        return facets

    # AST (implicit condition: assume trigger unless 'control' present in stimulus)
    ast_fallback_re = re.compile(rf'^ast_{phase_pat}-(.+)$')
    mo = ast_fallback_re.match(lower)
    if mo:
        phase, stim_full = mo.group(1), mo.group(2)
        # avoid misclassifying already-trigger-like names
        if 'trigger-' in stim_full or stim_full.startswith('trigger'):
            assumed_cond = 'trigger'
            stim_clean = stim_full.replace(
                'trigger-', '').replace('trigger', '') or stim_full
        else:
            if 'control' in stim_full:
                assumed_cond = 'neutral'
                stim_clean = re.sub(r'control', '', stim_full).replace(
                    '--', '-').strip('-_') or 'control'
            else:
                assumed_cond = 'trigger'
                stim_clean = stim_full
        facets.update({
            'task': 'ast',
            'phase': phase,
            'ast_condition': assumed_cond,
            'stimulus': stim_clean,
            'disposition': assumed_cond
        })
        facets['hed_tags'] = [
            'Task/AST', f'Phase/{phase.capitalize()}', f'Condition/{assumed_cond.capitalize()}', f'Stimulus/Sound/{stim_clean}'
        ]
        return facets

    # PMT
    pmt_re = re.compile(rf'^pmt_{phase_pat}$')
    mo = pmt_re.match(lower)
    if mo:
        phase = mo.group(1)
        facets.update({'task': 'pmt', 'phase': phase})
        facets['hed_tags'] = ['Task/PMT', f'Phase/{phase.capitalize()}']
        return facets

    # Fallback unparsed marker
    facets['hed_tags'] = ['Task/Other', 'Marker/Unparsed', f'Raw/{m}']
    return facets


def build_hed_event_mapping(marker_sequence, tasks=('pmt', 'hlt', 'let', 'ast'), base_code=100, global_event_id_map=None):
    """Build HED-style mapping structures from the ordered marker sequence.

    Parameters
    ----------
    marker_sequence : sequence of str
        Ordered list/array of marker labels from the XDF file.
    tasks : iterable
        Tasks to include. Unknown tasks are skipped but kept in the events id binding.
    base_code : int
        Starting integer code for assigning event IDs (to avoid collisions with 0).
    global_event_id_map : dict or None
        Optional pre-existing mapping of composite event names to IDs. If provided,
        ensures consistent event IDs across multiple subjects. If None, IDs are
        assigned sequentially as markers are encountered.

    Returns
    -------
    events_meta : dict
        'by_id' -> id -> facets dict (includes hed_tags)
        'by_marker' -> marker -> id
    task_mapping : dict
        task -> phase -> disposition -> dict(name -> event_id)
        Names are composite human-readable labels for MNE event selection.
    warnings : list of str
        Any parsing warnings encountered.
    fixed_marker_sequence : list of str
        The marker sequence after applying AST prestim placeholder fixes.
    """
    warnings = []

    # --- Pre-correction step for malformed AST prestim placeholders ---
    # Some recordings have 'ast_prestim-name' instead of the actual stimulus/condition.
    # Heuristic: if we see pattern ast_prestim-name and the *next* two markers are
    # ast_stim-<payload> and ast_poststim-<payload>, infer condition/stimulus from stim marker.
    def _fix_ast_prestim_placeholders(seq):
        seq = list(seq)  # make mutable copy
        for i in range(len(seq)-2):
            cur = str(seq[i]).lower()
            if cur == 'ast_prestim-name':
                stim_raw = str(seq[i+1]).lower()
                post_raw = str(seq[i+2]).lower()
                if stim_raw.startswith('ast_stim-') and post_raw.startswith('ast_poststim-'):
                    # Extract payload after 'ast_stim-'
                    payload = stim_raw[len('ast_stim-'):]
                    # If explicit condition exists it will be like 'trigger-xxx' or 'control-xxx'
                    if payload.startswith('trigger-'):
                        cond = 'trigger'
                        stim_name = payload[len('trigger-'):]
                    elif payload.startswith('control-'):
                        cond = 'control'
                        stim_name = payload[len('control-'):]
                    else:
                        # implicit condition: decide by presence of 'control'
                        if 'control' in payload:
                            cond = 'control'
                            stim_name = payload.replace(
                                'control', '').strip('-_') or 'control'
                        else:
                            cond = 'trigger'
                            stim_name = payload
                    repaired = f"ast_prestim-{cond}-{stim_name}"
                    warnings.append(
                        f"Repaired placeholder 'ast_prestim-name' -> '{repaired}' using subsequent stim marker '{seq[i+1]}'")
                    seq[i] = repaired
        return seq

    marker_sequence = _fix_ast_prestim_placeholders(marker_sequence)
    # Unique markers preserving order of first appearance
    seen = {}
    unique_markers = []
    for mk in marker_sequence:
        mk_str = str(mk)
        if mk_str not in seen:
            seen[mk_str] = True
            unique_markers.append(mk_str)

    by_id = {}
    by_marker = {}

    # Track if we're building a new global map
    building_global_map = global_event_id_map is None
    if building_global_map:
        global_event_id_map = {}
        next_code = base_code

    # First pass: build composite names for all markers to check global map
    marker_to_composite_name = {}
    for mk in unique_markers:
        facets = _parse_marker_string(mk)
        task = facets['task']
        phase = facets['phase']

        # Build composite label (same logic as below)
        # Note: trial numbers are NOT included in event names to allow pooling trials
        label_parts = [task, phase]
        if facets.get('intensity_db') is not None:
            label_parts.append(f"{facets['intensity_db']}dB")
        if facets.get('snr_db') is not None:
            label_parts.append(f"SNR{facets['snr_db']}")
        # Trial numbers removed - all trials of same condition share same event ID
        if facets.get('ast_condition') is not None:
            label_parts.append(facets['ast_condition'])
        if facets.get('stimulus') and task == 'ast':
            label_parts.append(facets['stimulus'])
        name = '/'.join(label_parts)
        marker_to_composite_name[mk] = name

    # Second pass: assign IDs using global map
    if building_global_map:
        next_code = base_code

    for mk in unique_markers:
        facets = _parse_marker_string(mk)
        composite_name = marker_to_composite_name[mk]

        # Get or assign event ID
        if composite_name in global_event_id_map:
            ev_id = global_event_id_map[composite_name]
        else:
            if building_global_map:
                ev_id = next_code
                global_event_id_map[composite_name] = ev_id
                next_code += 1
            else:
                # If not building and name not in map, this is unexpected
                warnings.append(
                    f"Event '{composite_name}' not found in global map, assigning new ID")
                # Find next available ID
                if global_event_id_map:
                    ev_id = max(global_event_id_map.values()) + 1
                else:
                    ev_id = base_code
                global_event_id_map[composite_name] = ev_id

        by_id[ev_id] = facets
        by_marker[mk] = ev_id

    # Build hierarchical task mapping
    # Desired structure:
    #   AST: task_mapping['ast'][phase] = {'neutral': {...}, 'trigger': {...}}
    #   Others: task_mapping[task][phase] = {name: id}
    task_mapping = {}
    for ev_id, facets in by_id.items():
        task = facets['task']
        if task not in tasks:
            continue
        phase = facets['phase']
        if task not in task_mapping:
            task_mapping[task] = {}
        # Build composite label
        # Note: trial numbers are NOT included in event names to allow pooling trials
        label_parts = [task, phase]
        if facets.get('intensity_db') is not None:
            label_parts.append(f"{facets['intensity_db']}dB")
        if facets.get('snr_db') is not None:
            label_parts.append(f"SNR{facets['snr_db']}")
        # Trial numbers removed - all trials of same condition share same event ID
        if facets.get('ast_condition') is not None:
            label_parts.append(facets['ast_condition'])
        if facets.get('stimulus') and task == 'ast':
            label_parts.append(facets['stimulus'])
        name = '/'.join(label_parts)

        if task == 'ast':
            if phase not in task_mapping[task]:
                task_mapping[task][phase] = {'neutral': {}, 'trigger': {}}
            disp = facets.get('disposition')
            if disp == 'neutral':
                task_mapping[task][phase]['neutral'][name] = ev_id
            elif disp == 'trigger':
                task_mapping[task][phase]['trigger'][name] = ev_id
            else:
                warnings.append(
                    f"AST marker without disposition (placed in both): {facets['raw']}")
                task_mapping[task][phase]['neutral'][name] = ev_id
                task_mapping[task][phase]['trigger'][name] = ev_id
        else:
            if phase not in task_mapping[task]:
                task_mapping[task][phase] = {}
            task_mapping[task][phase][name] = ev_id

    events_meta = {'by_id': by_id, 'by_marker': by_marker}
    return events_meta, task_mapping, warnings, marker_sequence


def hed_events_array(marker_sequence, eeg_insert_points, by_marker):
    """Create an events array (n_events, 3) aligned to EEG indices using HED mapping.

    Parameters
    ----------
    marker_sequence : sequence of str
    eeg_insert_points : array of shape (n_markers,) integer indices aligning markers
    by_marker : dict mapping raw marker string -> event ID

    Returns
    -------
    events : ndarray int, shape (n_markers, 3)
    """
    label_id_func = np.vectorize(lambda x: by_marker.get(str(x), 0))
    events = np.zeros((len(marker_sequence), 3), dtype=int)
    events[:, 0] = eeg_insert_points
    events[:, 2] = label_id_func(marker_sequence)
    return events


# --- vendored verbatim: the LEGACY quality metric (see note above) ---
CEEGRID_QUALITY_PRESETS = {
    'default': {
        'flat_voltage': 0.5,           # µV - relaxed for ear-EEG lower amplitude
        'bad_percent': 30,             # % - allow more transient flat periods
        'sd_floor_uv': 0.3,            # µV - SD below this (post-HP) = dead channel
        'qc_highpass': 1.0,            # Hz - HP copy for the dead-channel SD floor
        'correlation_threshold': (0.15, 0.85),  # wider bounds for ear-EEG
    },
    'strict': {
        'flat_voltage': 0.3,
        'bad_percent': 20,
        'sd_floor_uv': 0.5,
        'qc_highpass': 1.0,
        'correlation_threshold': (0.2, 0.8),
    },
    'lenient': {
        'flat_voltage': 1.0,
        'bad_percent': 40,
        'sd_floor_uv': 0.2,
        'qc_highpass': 1.0,
        'correlation_threshold': (0.1, 0.9),
    }
}


def quality_check(raw, flat_voltage=None, correlation_threshold=None, plot_corr=False,
                  tmin=None, tmax=None, events=None, event_margin=10.0,
                  preset='default', bad_percent=None, sd_floor_uv=None,
                  qc_highpass=None, verbose=True):
    """Check EEG data quality with optional time-windowing for CEEGrid data.

    Parameters
    ----------
    raw : mne.io.Raw
        Raw EEG data object.
    flat_voltage : float, optional
        Flat voltage threshold in microvolts. If None, uses preset value.
    correlation_threshold : tuple, optional
        (low, high) correlation bounds. If None, uses preset value.
    plot_corr : bool
        Whether to plot the correlation matrix.
    tmin : float, optional
        Start time in seconds for quality assessment window.
    tmax : float, optional
        End time in seconds for quality assessment window.
    events : ndarray, optional
        MNE events array (n_events, 3). If provided and tmin/tmax not set,
        auto-detects task bounds from first/last event.
    event_margin : float
        Seconds to add before first and after last event for auto-bounds.
    preset : str
        Quality preset: 'default', 'strict', or 'lenient'. CEEGrid-tuned.
    bad_percent : float, optional
        Percentage threshold for flat voltage detection. If None, uses preset.
    sd_floor_uv : float, optional
        Dead-channel SD floor (µV) on a high-passed copy: channels whose SD is
        below this are flagged as dead. If None, uses preset.
    qc_highpass : float, optional
        High-pass cutoff (Hz) applied to a copy before computing the SD floor,
        so it reflects signal rather than DC drift. If None, uses preset.
    verbose : bool
        Print diagnostic information.

    Returns
    -------
    dict
        Quality metrics including bad channels, variances, correlations,
        SNR estimates, and quality score.
    """
    # Get preset configuration
    config = CEEGRID_QUALITY_PRESETS.get(preset, CEEGRID_QUALITY_PRESETS['default']).copy()

    # Override with explicit parameters if provided
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

    # Extract final parameters
    flat_voltage_uv = config['flat_voltage']
    bad_pct = config['bad_percent']
    sd_floor = config['sd_floor_uv']
    qc_hp = config['qc_highpass']
    low_threshold, high_threshold = config['correlation_threshold']

    # Store original duration
    duration_total = raw.times[-1] - raw.times[0]

    # Determine time window for quality assessment
    tmin_used = tmin
    tmax_used = tmax

    if tmin is None and tmax is None and events is not None:
        # Auto-detect bounds from events
        sfreq = raw.info['sfreq']
        first_event_time = events[:, 0].min() / sfreq
        last_event_time = events[:, 0].max() / sfreq

        tmin_used = max(0, first_event_time - event_margin)
        tmax_used = min(raw.times[-1], last_event_time + event_margin)

        if verbose:
            print(f"[quality_check] Auto-detected task bounds: {tmin_used:.1f}s to {tmax_used:.1f}s")

    # Create cropped copy for quality assessment if time bounds specified
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

    # Flat voltage check (on cropped data)
    flat_voltage_volts = flat_voltage_uv * 1e-6
    _, bads_flat = mne.preprocessing.annotate_amplitude(
        raw_qc, flat=dict(eeg=flat_voltage_volts), bad_percent=bad_pct)

    # Variance / amplitude check.
    # NOTE: the correlation check below still runs on the UNFILTERED data_qc,
    # because its (low, high) bounds are calibrated for the shared DC drift of
    # unfiltered ear-EEG. Only the dead-channel test is moved to a high-passed
    # copy, where an absolute SD floor is meaningful.
    data_qc = raw_qc.get_data()
    variances = data_qc.var(axis=1)  # unfiltered; kept for plotting/reporting

    # Dead-channel floor on a 1 Hz high-passed copy: SD below an absolute µV
    # floor = dead. LOW side only. Replaces the old percentile rank, which
    # always flagged the single lowest-variance channel even on clean data.
    sd_uv = (raw_qc.copy()
             .filter(l_freq=qc_hp, h_freq=None, picks='eeg', verbose=False)
             .get_data().std(axis=1) * 1e6)
    bads_variance = [raw_qc.ch_names[i]
                     for i, s in enumerate(sd_uv) if s < sd_floor]
    # Floor expressed as a variance, for the plotting cell's threshold line
    variance_threshold = (sd_floor * 1e-6) ** 2

    # Correlation check (on cropped data)
    if data_qc.shape[0] == 1:
        corr_matrix = np.array([[1.0]])
    else:
        corr_matrix = np.corrcoef(data_qc)

    mean_corr = corr_matrix.mean(axis=1)
    bads_corr = [raw_qc.ch_names[i] for i, c in enumerate(mean_corr)
                 if (c < low_threshold) or (c > high_threshold)]

    if plot_corr:
        plt.imshow(corr_matrix, cmap='viridis', aspect='auto')
        plt.colorbar(label='Correlation Coefficient')
        plt.title('Channel Correlation Matrix')
        plt.xlabel('Channels')
        plt.ylabel('Channels')
        plt.xticks(ticks=np.arange(len(raw_qc.ch_names)),
                   labels=raw_qc.ch_names, rotation=90)
        plt.yticks(ticks=np.arange(len(raw_qc.ch_names)), labels=raw_qc.ch_names)
        plt.tight_layout()
        plt.show()

    bads_custom = set(bads_variance + bads_corr + bads_flat)

    # Enhanced metrics
    # SNR estimate using median absolute deviation as robust noise estimate
    mad_per_channel = median_abs_deviation(data_qc, axis=1)
    peak_to_peak = np.ptp(data_qc, axis=1)
    snr_estimate = peak_to_peak / (mad_per_channel + 1e-12)

    # Ear asymmetry (left vs right variance)
    left_idx = [i for i, ch in enumerate(raw_qc.ch_names) if ch.startswith('L')]
    right_idx = [i for i, ch in enumerate(raw_qc.ch_names) if ch.startswith('R')]
    if left_idx and right_idx:
        left_var = variances[left_idx].mean()
        right_var = variances[right_idx].mean()
        ear_asymmetry = abs(left_var - right_var) / (left_var + right_var + 1e-12)
    else:
        ear_asymmetry = None

    # Quality score (0-100 based on % good channels)
    n_channels = len(raw_qc.ch_names)
    n_bad = len(bads_custom)
    quality_score = 100 * (1 - n_bad / n_channels)

    if verbose:
        print(f"[quality_check] Quality score: {quality_score:.0f}/100 ({n_bad}/{n_channels} bad channels)")
        if bads_custom:
            print(f"[quality_check] Bad channels: {list(bads_custom)}")

    # Return detailed diagnostics
    result = {
        'bads_flat': list(bads_flat),
        'bads_variance': bads_variance,
        'bads_corr': bads_corr,
        'bads_combined': list(bads_custom),
        'variances': variances,
        'variance_threshold': float(variance_threshold),
        'ch_sd_uv': sd_uv,
        'corr_matrix': corr_matrix,
        'mean_corr': mean_corr,
        'correlation_threshold': (float(low_threshold), float(high_threshold)),
        'flat_voltage_volts': float(flat_voltage_volts),
        # New fields
        'time_window': (float(tmin_used), float(tmax_used)),
        'duration_analyzed': float(duration_analyzed),
        'duration_total': float(duration_total),
        'snr_estimate': snr_estimate,
        'ear_asymmetry': ear_asymmetry,
        'quality_score': float(quality_score),
        'preset_used': preset,
        'config': config,
    }

    return result



def create_mappings(event_names, prefix):
    marker_dict = {p: i for i, p in enumerate(np.unique(event_names))}
    id_binding = {v: k for k, v in marker_dict.items()}
    category_mapping = {}
    for p in prefix:
        # All keys for this prefix
        sub_map = {k: v for k, v in marker_dict.items() if k.startswith(p)}
        # Special handling for 'ast'
        if p == "ast":
            # Separate keys containing 'control' from others, store as dicts
            ast_prefix = {"prestim", "stim", "poststim"}
            ast_map = {}
            for ap in ast_prefix:
                sub_map = {
                    k: v for k, v in marker_dict.items() if k.startswith(p + "_" + ap)
                }
                ast_keys = list(sub_map.keys())
                ast_map[ap] = {"neutral": {}, "trigger": {}, "all": {}}
                for key in ast_keys:
                    ast_map[ap]["all"][key] = sub_map[key]
                    if "control" in key.lower():
                        ast_map[ap]["neutral"][key] = sub_map[key]
                    else:
                        ast_map[ap]["trigger"][key] = sub_map[key]
            category_mapping[p] = ast_map
        else:
            category_mapping[p] = sub_map
    return marker_dict, id_binding, category_mapping


def create_events(time_points, event_mapping, event_names):
    label_id_func = np.vectorize(event_mapping.get)
    events = np.zeros((len(time_points), 3), dtype=int)
    events[:, 0] = time_points
    events[:, 2] = label_id_func(event_names)
    return events


def contralateral_reference(raw):
    left_channels = [ch for ch in raw.ch_names if ch.startswith('L')]
    right_channels = [ch for ch in raw.ch_names if ch.startswith('R')]

    data, times = raw.get_data(return_times=True)
    left_idx = [raw.ch_names.index(ch) for ch in left_channels]
    right_idx = [raw.ch_names.index(ch) for ch in right_channels]

    # Calculate contralateral means
    mean_right = data[right_idx].mean(axis=0)
    mean_left = data[left_idx].mean(axis=0)

    # Subtract contralateral mean from each channel
    for i, ch in enumerate(left_idx):
        data[ch] = data[ch] - mean_right
    for i, ch in enumerate(right_idx):
        data[ch] = data[ch] - mean_left

    raw._data = data
    return raw


def select_event_ids(mapping, task, phases=None, disposition=None, predicate=None, include_phase_in_key=False):
    """Select event IDs from task_mapping supporting both AST & non-AST structures.

    AST structure: mapping['ast'][phase] = {'neutral': {...}, 'trigger': {...}}
    Non-AST: mapping[task][phase] = {name: id}
    """
    if task not in mapping:
        raise ValueError(
            f"Task '{task}' not present in mapping keys: {list(mapping.keys())}")
    out = {}
    phases_iter = phases or list(mapping[task].keys())
    is_ast = (task == 'ast')
    if is_ast:
        dispo_iter = ['neutral', 'trigger'] if disposition is None else [
            disposition]
        for ph in phases_iter:
            if ph not in mapping[task]:
                continue
            for disp in dispo_iter:
                block = mapping[task][ph].get(disp, {})
                for name, ev_id in block.items():
                    if predicate and not predicate(name, ev_id):
                        continue
                    key = name if disposition else f"{name}/{disp}"
                    if include_phase_in_key and not key.startswith(ph):
                        key = f"{ph}:{key}"
                    out[key] = ev_id
    else:
        if disposition is not None:
            print(
                f"[select_event_ids] disposition='{disposition}' ignored for non-AST task '{task}'.")
        for ph in phases_iter:
            block = mapping[task].get(ph, {})
            for name, ev_id in block.items():
                if predicate and not predicate(name, ev_id):
                    continue
                key = name
                if include_phase_in_key and not key.startswith(ph):
                    key = f"{ph}:{key}"
                out[key] = ev_id
    return out


def create_mne(
    eeg_stream,
    events,
    id_binding,
    flat_voltage=None,
    bandpass={"low": 1, "high": 50},
    notch_freq=60,
    re_reference=None,
    channel_strategy="drop",
    montage_file="ceegrid_montage_head.npz",
    quality_preset='default',
    quality_event_margin=10.0,
    quality_verbose=True,
):
    """Create MNE Raw object from EEG stream with quality checking.

    Parameters
    ----------
    eeg_stream : dict
        EEG stream data from XDF file.
    events : ndarray
        MNE events array (n_events, 3).
    id_binding : dict
        Event ID to name mapping.
    flat_voltage : float, optional
        Override flat voltage threshold (µV). If None, uses preset.
    bandpass : dict
        Bandpass filter settings with 'low' and 'high' keys.
    notch_freq : float
        Notch filter frequency (Hz). None to skip.
    re_reference : str, optional
        Re-referencing method: 'average' or 'contralateral'.
    channel_strategy : str
        How to handle bad channels: 'drop' (remove them), 'interpolate'
        (spatially interpolate), 'zero_mask' (zero out, keep 16 channels),
        or 'keep_all' (skip bad-channel handling; quality check still runs
        and is stored, but no channels are dropped/interpolated/zeroed).
    montage_file : str
        Path to CEEGrid montage file.
    quality_preset : str
        Quality preset: 'default', 'strict', or 'lenient'.
    quality_event_margin : float
        Seconds margin around events for quality check window.
    quality_verbose : bool
        Print quality check diagnostics.

    Returns
    -------
    mne.io.Raw
        Processed Raw object with quality_check results stored in raw.info.
    """
    raw = create_raw(eeg_stream)
    sampling_rate = raw.info["sfreq"]
    montage_data = np.load(montage_file)
    montage = mne.channels.make_dig_montage(
        ch_pos=dict(zip(montage_data['labels'], montage_data['points'])),
        nasion=montage_data['nasion'],
        lpa=montage_data['lpa'],
        rpa=montage_data['rpa'],
        coord_frame='head')
    raw.set_montage(montage)

    # Run quality check with time-windowing based on events
    quality_result = quality_check(
        raw,
        flat_voltage=flat_voltage,
        events=events,
        event_margin=quality_event_margin,
        preset=quality_preset,
        verbose=quality_verbose,
    )
    bads = quality_result['bads_combined']
    raw.info["bads"] = bads

    # Store quality result for later inspection (use 'temp' as MNE doesn't allow custom keys)
    if 'temp' not in raw.info or raw.info['temp'] is None:
        raw.info['temp'] = {}
    raw.info['temp']['quality_check'] = quality_result

    if len(bads) == len(raw.ch_names) and channel_strategy != "keep_all":
        raise ValueError(f"All channels marked as bad. Quality score: {quality_result['quality_score']:.0f}/100")

    # --- Channel handling strategy ---
    channel_mask = np.ones(len(raw.ch_names), dtype=bool)

    if channel_strategy == "keep_all":
        # Record which channels QC flagged, but keep every channel untouched
        if len(bads) > 0:
            bad_indices = [raw.ch_names.index(ch) for ch in bads]
            channel_mask[bad_indices] = False
        raw.info["bads"] = []
    elif len(bads) > 0:
        if channel_strategy == "interpolate":
            if len(bads) >= 12:
                raise ValueError(
                    f"Too many bad channels ({len(bads)}/{len(raw.ch_names)}), cannot interpolate. "
                    f"Quality score: {quality_result['quality_score']:.0f}/100")
            raw = raw.interpolate_bads()
        elif channel_strategy == "drop":
            bad_indices = [raw.ch_names.index(ch) for ch in bads]
            channel_mask[bad_indices] = False
            raw = raw.drop_channels(bads)
        elif channel_strategy == "zero_mask":
            bad_indices = [raw.ch_names.index(ch) for ch in bads]
            channel_mask[bad_indices] = False
            raw._data[bad_indices, :] = 0.0
            raw.info["bads"] = []  # clear so MNE doesn't flag them
        else:
            raise ValueError(f"Unknown channel_strategy: {channel_strategy}")

    raw.info['temp']['channel_mask'] = channel_mask

    annot = mne.annotations_from_events(events, raw.info["sfreq"], id_binding)
    raw.set_annotations(annot)

    if notch_freq is not None:
        raw = raw.notch_filter(
            np.arange(notch_freq, sampling_rate / 2, notch_freq), picks="eeg"
        )

    if bandpass is not None:
        raw = raw.filter(l_freq=bandpass["low"], h_freq=bandpass["high"])

    if re_reference is not None:
        if re_reference == 'average':
            raw.set_eeg_reference(re_reference, projection=True)
        if re_reference == 'contralateral':
            raw = contralateral_reference(raw)
    return raw


def read_data(
    file_path,
    eeg_stream_name="obci_eeg1",
    bindings=None,
    bandpass={"low": 1, "high": 50},
    flat_voltage=None,
    re_reference=None,  # 'average' or 'contralateral'
    use_hed=False,
    channel_strategy="drop",
    global_event_id_map=None,  # Added parameter for consistent event IDs across subjects
    quality_preset='default',
    quality_event_margin=10.0,
    quality_verbose=True,
):
    """Load and preprocess EEG data from XDF file.

    Parameters
    ----------
    file_path : str
        Path to XDF file.
    eeg_stream_name : str
        Name of EEG stream in XDF file.
    bindings : list, optional
        Task bindings for event mapping (legacy mode).
    bandpass : dict
        Bandpass filter settings with 'low' and 'high' keys.
    flat_voltage : float, optional
        Override flat voltage threshold (µV). If None, uses preset.
    re_reference : str, optional
        Re-referencing method: 'average' or 'contralateral'.
    use_hed : bool
        Use HED-style event mapping.
    channel_strategy : str
        How to handle bad channels: 'drop', 'interpolate', or 'zero_mask'.
    global_event_id_map : dict, optional
        Global event ID mapping for consistency across subjects.
    quality_preset : str
        Quality preset: 'default', 'strict', or 'lenient'.
    quality_event_margin : float
        Seconds margin around events for quality check window.
    quality_verbose : bool
        Print quality check diagnostics.

    Returns
    -------
    tuple
        (raw, events, mapping) - Processed Raw object, events array, and event mapping.
    """
    marker_data, eeg_stream, eeg_insert_points = parse_xdf(
        file_path, eeg_stream_name)
    if use_hed:
        # Build HED-style mapping
        events_meta, mapping, _, fixed_marker_data = build_hed_event_mapping(
            marker_data, global_event_id_map=global_event_id_map)
        events = hed_events_array(
            fixed_marker_data, eeg_insert_points, events_meta['by_marker'])
        # id_binding for annotations: map int id -> a concise joined HED tag string
        id_binding = {ev_id: ';'.join(f['hed_tags'])
                      for ev_id, f in events_meta['by_id'].items()}
    else:
        # Backward-compatible original mapping
        if bindings is None:
            bindings = ["pmt", "hlt", "let", "ast"]
        marker_dict, id_binding, mapping = create_mappings(
            marker_data, bindings)
        events = create_events(eeg_insert_points, marker_dict, marker_data)
    raw = create_mne(
        eeg_stream, events, id_binding, bandpass=bandpass,
        flat_voltage=flat_voltage, re_reference=re_reference,
        channel_strategy=channel_strategy,
        quality_preset=quality_preset,
        quality_event_margin=quality_event_margin,
        quality_verbose=quality_verbose,
    )
    return raw, events, mapping
