import seaborn as sns
from scipy import signal, stats
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import glob
import numpy as np
import os
import mne
import pyxdf
import cv2


def closest_points_vector(eeg_timestamps, marker_timestamps):
    # Get the insertion indices for each marker timestamp
    indices = np.searchsorted(eeg_timestamps, marker_timestamps)

    # Preallocate the output array as a copy of indices.
    closest_eeg_indices = indices.copy()

    # Create a mask for markers where the insertion index equals 0 (marker before first EEG timestamp)
    mask_begin = indices == 0
    # For these, the closest EEG index is 0 (they cannot use a previous value)
    closest_eeg_indices[mask_begin] = 0

    # Create a mask for markers where the insertion index equals the length of the EEG timestamps
    mask_end = indices == len(eeg_timestamps)
    # For these markers, set the closest EEG index to the last index
    closest_eeg_indices[mask_end] = len(eeg_timestamps) - 1

    # Create a mask for the "middle" markers, i.e., not at the very beginning or end
    mask_middle = (indices > 0) & (indices < len(eeg_timestamps))

    # For markers in the middle, compute the distance to the previous and next EEG timestamps:
    prev_times = eeg_timestamps[indices[mask_middle] - 1]
    next_times = eeg_timestamps[indices[mask_middle]]
    marker_times_middle = marker_timestamps[mask_middle]

    # Calculate the differences
    diff_prev = marker_times_middle - prev_times
    diff_next = next_times - marker_times_middle

    # For each marker in the middle, choose the index of the EEG timestamp that is closer:
    # If the distance to the previous timestamp is less or equal than the distance to the next,
    # then we pick indices[mask_middle]-1; otherwise, we pick indices[mask_middle].
    closest_eeg_indices[mask_middle] = np.where(
        diff_prev <= diff_next, indices[mask_middle] - 1, indices[mask_middle]
    )

    return closest_eeg_indices


def split_video(input_file, time_segments, output_folder):
    cap = cv2.VideoCapture(input_file)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    print(f"Video FPS: {fps}")
    print(f"Video duration: {duration} seconds")
    print(f"Number of time segments: {frame_count}")

    file_name = os.path.splitext(os.path.basename(input_file))[0]
    output_folder = os.path.join(output_folder, file_name)
    os.makedirs(output_folder, exist_ok=True)

    for start_frame, end_frame, segment_name in tqdm(time_segments):
        output_path = os.path.join(output_folder, f"{segment_name}.avi")

        # Set the video capture to the start frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_frame))
        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(
            output_path, fourcc, fps, (int(cap.get(3)), int(cap.get(4)))
        )

        # Read and write frames from start to end
        for _ in range(int(start_frame), int(end_frame)):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
        out.release()

    cap.release()


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


def create_mne(
    eeg_stream,
    events,
    id_binding,
    flat_voltage=0.1,
    bandpass={"low": 1, "high": 50},
    notch_freq=60,
):
    ch_labels = [
        "L1",
        "L2",
        "L4",
        "L5",
        "L7",
        "L8",
        "L9",
        "L10",
        "R1",
        "R2",
        "R4",
        "R5",
        "R7",
        "R8",
        "R9",
        "R10",
    ]
    sampling_rate = float(eeg_stream["info"]["nominal_srate"][0])
    if sampling_rate != 125:
        raise ValueError(
            f"Expected sampling rate of 125 Hz, got {sampling_rate} Hz")
    # Openbci EEG data is in microvolts, convert to volts for MNE
    eeg_data = eeg_stream["time_series"].T * 1e-6
    info = mne.create_info(
        ch_names=ch_labels, sfreq=sampling_rate, ch_types="eeg")
    raw = mne.io.RawArray(eeg_data, info)

    if flat_voltage != None:
        flat_voltage *= 1e-6  # Flat voltage threshold in Volts
        _, bads = mne.preprocessing.annotate_amplitude(
            raw, flat=dict(eeg=flat_voltage))
        raw.info["bads"] = bads
        print(f"Bad channels: {bads}")

    # raw.interpolate_bads()
    annot = mne.annotations_from_events(events, raw.info["sfreq"], id_binding)
    raw.set_annotations(annot)

    if notch_freq is not None:
        raw = raw.notch_filter(
            np.arange(notch_freq, sampling_rate / 2, notch_freq), picks="eeg"
        )

    # raw.set_montage(montage)  # Set the montage to the raw object
    if bandpass != None:
        raw = raw.filter(l_freq=bandpass["low"], h_freq=bandpass["high"])
        raw = raw.set_eeg_reference("average")
    return raw


def parse_xdf(file_path, eeg_stream_name="obci_eeg1"):
    data, header = pyxdf.load_xdf(file_path)
    # print([stream['info']['type'][0] for stream in data])
    # Extract the EEG and marker streams
    marker_stream = next(
        stream for stream in data if stream["info"]["type"][0] == "Markers"
    )
    eeg_stream = next(
        stream
        for stream in data
        if stream["info"]["type"][0] == "EEG"
        and stream["info"]["name"][0] == eeg_stream_name
    )
    marker_timestamps = marker_stream["time_stamps"]
    marker_data = np.array(marker_stream["time_series"]).squeeze()
    eeg_timestamps = eeg_stream["time_stamps"]
    eeg_insert_points = closest_points_vector(
        eeg_timestamps, marker_timestamps)
    return marker_data, eeg_stream, eeg_insert_points


def get_event_names(files, prefix="ast_stim", exclude_participants=[]):
    """
    Extracts event names from marker data that start with a given prefix.
    Returns:
        name_mapping: dict mapping participant to their event names
        common_names: set of event names present for every participant
    """
    name_mapping = {}
    all_names = []
    for file in files:
        participant_number = file.split(os.sep)[2]
        if participant_number in exclude_participants:
            continue
        participant_id = file.split(os.sep)[-1].split("_")[0]
        marker_data, _, _ = parse_xdf(file)
        names = {str(f) for f in np.unique(marker_data)
                 if str(f).startswith(prefix)}
        name_mapping[f"{participant_number}_{participant_id}"] = names
        all_names.append(names)
    # Intersection: names present for every participant
    if all_names:
        common_names = set.intersection(*all_names)
    else:
        common_names = set()
    return name_mapping, common_names


def read_data(
    file_path,
    eeg_stream_name="obci_eeg1",
    bindings=None,
    bandpass={"low": 1, "high": 50},
    flat_voltage=0.1,
):
    marker_data, eeg_stream, eeg_insert_points = parse_xdf(
        file_path, eeg_stream_name)
    # Create MNE events from the marker data
    if bindings is None:
        bindings = ["pmt", "hlt", "let", "ast"]
    marker_dict, id_binding, category_mapping = create_mappings(
        marker_data, bindings)
    events = create_events(eeg_insert_points, marker_dict, marker_data)
    raw = create_mne(
        eeg_stream, events, id_binding, bandpass=bandpass, flat_voltage=flat_voltage
    )
    return raw, events, category_mapping
    # return eeg_stream, events, id_binding, category_mapping


class EEGSignalQuality:
    """
    Comprehensive signal quality assessment for around-the-ear EEG devices.
    Designed for academic research with MNE Python raw objects.
    """

    def __init__(self, raw, ear_channels, reference_channels=None):
        """
        Initialize signal quality analyzer.

        Parameters:
        -----------
        raw : mne.io.Raw
            MNE raw object containing EEG data
        ear_channels : list
            List of ear-EEG channel names (e.g., ['ear_left', 'ear_right'])
        reference_channels : list, optional
            List of reference scalp channel names for comparison
        """
        self.raw = raw.copy()
        self.ear_channels = ear_channels
        self.reference_channels = reference_channels or []
        self.sfreq = raw.info["sfreq"]
        self.results = {}

    def calculate_rms(self, channels=None, window_size=1.0):
        """
        Calculate Root Mean Square (RMS) for signal amplitude assessment.

        Parameters:
        -----------
        channels : list, optional
            Channels to analyze (default: ear_channels)
        window_size : float
            Window size in seconds for RMS calculation

        Returns:
        --------
        dict : RMS values and statistics
        """
        if channels is None:
            channels = self.ear_channels

        data, times = self.raw[channels, :]
        window_samples = int(window_size * self.sfreq)

        rms_results = {}
        for i, ch in enumerate(channels):
            ch_data = data[i, :]
            # Calculate windowed RMS
            rms_windows = []
            for start in range(0, len(ch_data) - window_samples, window_samples):
                window_data = ch_data[start: start + window_samples]
                rms_val = np.sqrt(np.mean(window_data**2))
                rms_windows.append(rms_val)

            rms_results[ch] = {
                "mean_rms": np.mean(rms_windows),
                "std_rms": np.std(rms_windows),
                "rms_windows": rms_windows,
                "stability_score": 1
                / (1 + np.std(rms_windows)),  # Higher = more stable
            }

        return rms_results

    def calculate_snr_alpha(self, channels=None, eyes_closed_segments=None):
        """
        Calculate Signal-to-Noise Ratio using alpha peak detection.

        Parameters:
        -----------
        channels : list, optional
            Channels to analyze
        eyes_closed_segments : list of tuples, optional
            [(start_time, end_time), ...] for eyes-closed segments

        Returns:
        --------
        dict : SNR values and alpha power metrics
        """
        if channels is None:
            channels = self.ear_channels

        # Apply minimal preprocessing for spectral analysis
        raw_filtered = self.raw.copy().filter(l_freq=0.5, h_freq=None)
        raw_filtered.notch_filter(freqs=[50, 60])  # Remove line noise

        snr_results = {}

        for ch in channels:
            data, times = raw_filtered[ch, :]
            data = data.flatten()

            # Calculate power spectral density
            freqs, psd = signal.welch(
                data, fs=self.sfreq, nperseg=int(4 * self.sfreq))

            # Define frequency bands
            alpha_band = (8, 13)
            # Delta and beta as noise reference
            noise_bands = [(1, 4), (15, 25)]

            # Find alpha peak
            alpha_mask = (freqs >= alpha_band[0]) & (freqs <= alpha_band[1])
            alpha_power = np.mean(psd[alpha_mask])
            alpha_peak_freq = freqs[alpha_mask][np.argmax(psd[alpha_mask])]

            # Calculate noise power
            noise_power = 0
            for noise_band in noise_bands:
                noise_mask = (freqs >= noise_band[0]) & (
                    freqs <= noise_band[1])
                noise_power += np.mean(psd[noise_mask])
            noise_power /= len(noise_bands)

            # SNR calculation
            snr_db = 10 * np.log10(alpha_power / noise_power)

            snr_results[ch] = {
                "snr_db": snr_db,
                "alpha_power": alpha_power,
                "alpha_peak_freq": alpha_peak_freq,
                "noise_power": noise_power,
                "psd": psd,
                "freqs": freqs,
            }

        return snr_results

    def calculate_spectral_power(self, channels=None):
        """
        Calculate power spectral density across canonical EEG frequency bands.

        Returns:
        --------
        dict : Power values for each frequency band
        """
        if channels is None:
            channels = self.ear_channels

        # Apply filtering for spectral analysis
        raw_filtered = self.raw.copy().filter(l_freq=0.5, h_freq=40)
        raw_filtered.notch_filter(freqs=[50, 60])

        # Define frequency bands
        bands = {
            "delta": (0.5, 4),
            "theta": (4, 8),
            "alpha": (8, 13),
            "beta": (13, 30),
            "gamma": (30, 40),
        }

        spectral_results = {}

        for ch in channels:
            data, times = raw_filtered[ch, :]
            data = data.flatten()

            # Calculate PSD using multitaper method for better variance reduction
            freqs, psd = signal.welch(
                data, fs=self.sfreq, nperseg=int(4 * self.sfreq))

            ch_bands = {}
            total_power = np.sum(psd)

            for band_name, (low, high) in bands.items():
                band_mask = (freqs >= low) & (freqs <= high)
                absolute_power = np.sum(psd[band_mask])
                relative_power = absolute_power / total_power

                ch_bands[band_name] = {
                    "absolute_power": absolute_power,
                    "relative_power": relative_power,
                    "peak_freq": freqs[band_mask][np.argmax(psd[band_mask])],
                }

            spectral_results[ch] = ch_bands

        return spectral_results

    def calculate_cross_correlation(self, reference_channel=None):
        """
        Calculate cross-correlation between ear-EEG and reference channels.

        Parameters:
        -----------
        reference_channel : str, optional
            Reference channel name (e.g., scalp electrode)

        Returns:
        --------
        dict : Correlation coefficients and lag information
        """
        if not reference_channel or reference_channel not in self.raw.ch_names:
            print("Warning: No valid reference channel provided")
            return {}

        correlation_results = {}

        # Use filtered data for correlation analysis
        raw_filtered = self.raw.copy().filter(l_freq=1, h_freq=40)

        ref_data, _ = raw_filtered[reference_channel, :]
        ref_data = ref_data.flatten()

        for ch in self.ear_channels:
            ear_data, _ = raw_filtered[ch, :]
            ear_data = ear_data.flatten()

            # Pearson correlation
            pearson_r, pearson_p = stats.pearsonr(ear_data, ref_data)

            # Cross-correlation with lags
            cross_corr = np.correlate(ear_data, ref_data, mode="full")
            lags = signal.correlation_lags(
                len(ear_data), len(ref_data), mode="full")
            max_corr_idx = np.argmax(np.abs(cross_corr))
            max_lag_samples = lags[max_corr_idx]
            max_lag_ms = (max_lag_samples / self.sfreq) * 1000

            correlation_results[ch] = {
                "pearson_r": pearson_r,
                "pearson_p": pearson_p,
                "max_cross_corr": cross_corr[max_corr_idx],
                "optimal_lag_ms": max_lag_ms,
                "cross_corr": cross_corr,
                "lags": lags,
            }

        return correlation_results

    def calculate_coherence(self, reference_channel=None):
        """
        Calculate coherence between ear-EEG and reference channels.

        Returns:
        --------
        dict : Coherence values across frequency bands
        """
        if not reference_channel or reference_channel not in self.raw.ch_names:
            print("Warning: No valid reference channel provided")
            return {}

        coherence_results = {}
        raw_filtered = self.raw.copy().filter(l_freq=1, h_freq=40)

        ref_data, _ = raw_filtered[reference_channel, :]
        ref_data = ref_data.flatten()

        for ch in self.ear_channels:
            ear_data, _ = raw_filtered[ch, :]
            ear_data = ear_data.flatten()

            # Calculate coherence
            freqs, coherence = signal.coherence(
                ear_data, ref_data, fs=self.sfreq, nperseg=int(4 * self.sfreq)
            )

            # Calculate coherence in frequency bands
            bands = {
                "delta": (0.5, 4),
                "theta": (4, 8),
                "alpha": (8, 13),
                "beta": (13, 30),
                "gamma": (30, 40),
            }

            band_coherence = {}
            for band_name, (low, high) in bands.items():
                band_mask = (freqs >= low) & (freqs <= high)
                band_coherence[band_name] = np.mean(coherence[band_mask])

            coherence_results[ch] = {
                "band_coherence": band_coherence,
                "mean_coherence": np.mean(coherence),
                "max_coherence": np.max(coherence),
                "coherence_spectrum": coherence,
                "freqs": freqs,
            }

        return coherence_results

    def detect_artifacts(self, channels=None, voltage_threshold=100e-6):
        """
        Detect artifacts using voltage threshold and gradient criteria.

        Parameters:
        -----------
        channels : list, optional
            Channels to analyze
        voltage_threshold : float
            Voltage threshold in volts (default: 100 µV)

        Returns:
        --------
        dict : Artifact detection results
        """
        if channels is None:
            channels = self.ear_channels

        artifact_results = {}

        for ch in channels:
            data, times = self.raw[ch, :]
            data = data.flatten()

            # Voltage threshold artifacts
            voltage_artifacts = np.abs(data) > voltage_threshold

            # Gradient artifacts (rapid voltage changes)
            gradient = np.gradient(data)
            gradient_threshold = 5 * np.std(gradient)
            gradient_artifacts = np.abs(gradient) > gradient_threshold

            # Combined artifact mask
            all_artifacts = voltage_artifacts | gradient_artifacts
            artifact_proportion = np.sum(all_artifacts) / len(data)

            # Artifact-free segments
            clean_data = data[~all_artifacts]

            artifact_results[ch] = {
                "artifact_proportion": artifact_proportion,
                "voltage_artifacts": np.sum(voltage_artifacts),
                "gradient_artifacts": np.sum(gradient_artifacts),
                "clean_data_length": len(clean_data),
                "artifact_mask": all_artifacts,
                "data_quality_score": 1 - artifact_proportion,
            }

        return artifact_results

    def alpha_modulation_test(self, eyes_open_segments, eyes_closed_segments):
        """
        Test alpha rhythm modulation (eyes-open vs eyes-closed).

        Parameters:
        -----------
        eyes_open_segments : list of tuples
            [(start_time, end_time), ...] for eyes-open periods
        eyes_closed_segments : list of tuples
            [(start_time, end_time), ...] for eyes-closed periods

        Returns:
        --------
        dict : Alpha modulation results
        """
        raw_filtered = self.raw.copy().filter(l_freq=1, h_freq=30)
        raw_filtered.notch_filter(freqs=[50, 60])

        modulation_results = {}

        for ch in self.ear_channels:
            # Extract alpha power for each condition
            alpha_power_open = []
            alpha_power_closed = []

            # Eyes open segments
            for start_time, end_time in eyes_open_segments:
                start_sample = int(start_time * self.sfreq)
                end_sample = int(end_time * self.sfreq)
                segment_data = raw_filtered[ch,
                                            start_sample:end_sample][0].flatten()

                freqs, psd = signal.welch(segment_data, fs=self.sfreq)
                alpha_mask = (freqs >= 8) & (freqs <= 13)
                alpha_power_open.append(np.mean(psd[alpha_mask]))

            # Eyes closed segments
            for start_time, end_time in eyes_closed_segments:
                start_sample = int(start_time * self.sfreq)
                end_sample = int(end_time * self.sfreq)
                segment_data = raw_filtered[ch,
                                            start_sample:end_sample][0].flatten()

                freqs, psd = signal.welch(segment_data, fs=self.sfreq)
                alpha_mask = (freqs >= 8) & (freqs <= 13)
                alpha_power_closed.append(np.mean(psd[alpha_mask]))

            # Statistical comparison
            alpha_power_open = np.array(alpha_power_open)
            alpha_power_closed = np.array(alpha_power_closed)

            stat, p_value = stats.wilcoxon(
                alpha_power_open, alpha_power_closed, alternative="less"
            )

            modulation_ratio = np.mean(
                alpha_power_closed) / np.mean(alpha_power_open)

            modulation_results[ch] = {
                "alpha_power_eyes_open": np.mean(alpha_power_open),
                "alpha_power_eyes_closed": np.mean(alpha_power_closed),
                "modulation_ratio": modulation_ratio,
                "statistical_significance": p_value,
                "modulation_detected": p_value < 0.05 and modulation_ratio > 1.2,
            }

        return modulation_results

    def comprehensive_quality_assessment(self, reference_channel=None):
        """
        Run comprehensive signal quality assessment.

        Returns:
        --------
        dict : Complete quality assessment results
        """
        print("Running comprehensive EEG signal quality assessment...")

        results = {}

        # 1. RMS Analysis
        print("1. Calculating RMS...")
        results["rms"] = self.calculate_rms()

        # 2. SNR Analysis
        print("2. Calculating SNR...")
        results["snr"] = self.calculate_snr_alpha()

        # 3. Spectral Power Analysis
        print("3. Analyzing spectral power...")
        results["spectral_power"] = self.calculate_spectral_power()

        # 4. Cross-correlation (if reference available)
        if reference_channel:
            print("4. Calculating cross-correlation...")
            results["correlation"] = self.calculate_cross_correlation(
                reference_channel)

            print("5. Calculating coherence...")
            results["coherence"] = self.calculate_coherence(reference_channel)

        # 6. Artifact Detection
        print("6. Detecting artifacts...")
        results["artifacts"] = self.detect_artifacts()

        # 7. Overall Quality Score
        results["quality_summary"] = self._calculate_overall_quality_score(
            results)

        print("Assessment complete!")
        self.results = results
        return results

    def _calculate_overall_quality_score(self, results):
        """Calculate overall quality score based on multiple metrics."""
        quality_scores = []

        for ch in self.ear_channels:
            ch_scores = []

            # RMS stability score
            if "rms" in results:
                ch_scores.append(results["rms"][ch]["stability_score"])

            # SNR score (normalized)
            if "snr" in results:
                snr_db = results["snr"][ch]["snr_db"]
                # -10 to 10 dB range
                snr_score = min(1.0, max(0.0, (snr_db + 10) / 20))
                ch_scores.append(snr_score)

            # Artifact score
            if "artifacts" in results:
                ch_scores.append(results["artifacts"]
                                 [ch]["data_quality_score"])

            # Correlation score (if available)
            if "correlation" in results and ch in results["correlation"]:
                corr_score = abs(results["correlation"][ch]["pearson_r"])
                ch_scores.append(corr_score)

            overall_score = np.mean(ch_scores) if ch_scores else 0.0
            quality_scores.append(
                {
                    "channel": ch,
                    "overall_score": overall_score,
                    "quality_grade": self._grade_quality(overall_score),
                }
            )

        return quality_scores

    # ----------------- Visualization methods -----------------
    def plot_quality_summary(
        self, results=None, figsize=(10, 4), palette=None, show=True
    ):
        """Plot overall quality scores as a bar chart.

        Expects results['quality_summary'] to be a list of dicts with keys
        'channel' and 'overall_score'. If results is None, uses self.results.
        """
        if results is None:
            results = getattr(self, "results", None)
        if not results or "quality_summary" not in results:
            raise ValueError(
                "No quality_summary available in results. Run comprehensive_quality_assessment first or pass results."
            )

        qs = results["quality_summary"]
        channels = [q["channel"] for q in qs]
        scores = [q["overall_score"] for q in qs]
        grades = [q.get("quality_grade", "") for q in qs]

        plt.figure(figsize=figsize)
        if palette is None:
            palette = sns.color_palette("viridis", len(scores))
        sns.barplot(x=scores, y=channels, palette=palette)
        plt.xlabel("Overall Quality Score")
        plt.ylabel("Channel")
        plt.title("EEG Channel Quality Summary")
        for i, (s, g) in enumerate(zip(scores, grades)):
            plt.text(s + 0.01, i, f"{g} ({s:.2f})", va="center")
        plt.xlim(0, 1)
        if show:
            plt.tight_layout()
            plt.show()

    def plot_rms_stability(
        self, results=None, channels=None, figsize=(12, 4), show=True
    ):
        """Plot RMS windows for channels or boxplot of stability."""
        if results is None:
            results = getattr(self, "results", None)
        if not results or "rms" not in results:
            raise ValueError(
                "No rms results available. Run comprehensive_quality_assessment first or pass results."
            )

        rms = results["rms"]
        if channels is None:
            channels = list(rms.keys())

        plt.figure(figsize=figsize)
        # plot each channel's rms windows as a line
        for ch in channels:
            windows = rms[ch]["rms_windows"]
            plt.plot(windows, label=ch)
        plt.xlabel("Window #")
        plt.ylabel("RMS (V)")
        plt.title("RMS windows by channel")
        plt.legend(loc="upper right", bbox_to_anchor=(1.15, 1))
        if show:
            plt.tight_layout()
            plt.show()

    def plot_snr(self, results=None, figsize=(10, 4), show=True):
        """Plot SNR (dB) per channel as a horizontal bar chart."""
        if results is None:
            results = getattr(self, "results", None)
        if not results or "snr" not in results:
            raise ValueError(
                "No snr results available. Run comprehensive_quality_assessment first or pass results."
            )

        snr = results["snr"]
        channels = list(snr.keys())
        snr_db = [snr[ch]["snr_db"] for ch in channels]

        plt.figure(figsize=figsize)
        sns.barplot(x=snr_db, y=channels, palette="magma")
        plt.xlabel("SNR (dB)")
        plt.title("SNR per channel")
        if show:
            plt.tight_layout()
            plt.show()

    def plot_artifact_proportions(self, results=None, figsize=(10, 4), show=True):
        """Plot artifact proportion or data quality score per channel."""
        if results is None:
            results = getattr(self, "results", None)
        if not results or "artifacts" not in results:
            raise ValueError(
                "No artifacts results available. Run comprehensive_quality_assessment first or pass results."
            )

        art = results["artifacts"]
        channels = list(art.keys())
        proportions = [art[ch]["artifact_proportion"] for ch in channels]

        plt.figure(figsize=figsize)
        sns.barplot(x=proportions, y=channels, palette="rocket")
        plt.xlabel("Artifact Proportion")
        plt.title("Artifact proportion by channel (higher = worse)")
        plt.xlim(0, 1)
        if show:
            plt.tight_layout()
            plt.show()

    def _grade_quality(self, score):
        """Convert quality score to letter grade."""
        if score >= 0.8:
            return "A - Excellent"
        elif score >= 0.6:
            return "B - Good"
        elif score >= 0.4:
            return "C - Fair"
        elif score >= 0.2:
            return "D - Poor"
        else:
            return "F - Unacceptable"


def calculate_power_spectrum(epoch, method="multitaper", fmin=1, fmax=20, mean=False):
    """Calculate power spectrum for given epochs."""
    psd = epoch.compute_psd(method=method, fmin=fmin, fmax=fmax)
    power, freqs = psd.get_data(return_freqs=True)
    # if compute_method == 'wavelet':
    #     freqs = np.logspace(*np.log10([fmin, fmax]), num=8)
    #     n_cycles = freqs / 2.0  # different number of cycle per frequency
    #     power, itc = epoch.compute_tfr(
    #         method="morlet",
    #         freqs=freqs,
    #         n_cycles=n_cycles,
    #         average=True,
    #         return_itc=True,
    #         decim=3,
    #     )
    if mean:
        power = power.mean(axis=(0, 1))
    return power, freqs


def plot_power_spectrum(
    power, freq, average_axis=(0, 1), title="Power Spectrum", already_mean=False
):
    print(f"Power shape: {power.shape}, Frequency shape: {freq.shape}")
    bands = {
        "delta": (freq[0], 4, "blue"),
        "theta": (4, 8, "green"),
        "alpha": (8, 13, "orange"),
        "beta": (13, 30, "red"),
        "gamma": (30, freq[-1], "purple"),
    }

    if not already_mean:
        mean_power = power.mean(axis=average_axis)
    else:
        mean_power = power

    fig = plt.figure(figsize=(10, 6))
    for band, (low, high, color) in bands.items():
        idx = np.where((freq >= low) & (freq < high))[0]
        if len(idx) > 0:
            plt.fill_between(
                freq[idx],
                mean_power[idx],
                color=color,
                alpha=0.5,
                label=band.capitalize(),
            )

    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Power (dB)")
    plt.title("Power Spectrum by Frequency Band")
    plt.xlim(0, 50)
    plt.grid()
    plt.legend()
    plt.tight_layout()

    return fig


# probably redundant but fits the pattern of having a compute and plot function for each step
def compute_tf_analysis(epochs, freqs, n_cycles):
    return epochs.compute_tfr(
        method="morlet",
        freqs=freqs,
        n_cycles=n_cycles,
        average=True,
        return_itc=True,
        decim=3,
    )


def plot_tf_analysis(power):
    channels = power.ch_names
    n_channels = len(channels)
    n_cols = 4
    n_rows = int(np.ceil(n_channels / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 3 * n_rows))
    axes = axes.flatten()

    # Normalize each channel's power between 0 and 1
    for idx, ch in enumerate(channels):
        data = power.data[idx]
        data_norm = (data - data.min()) / (data.max() - data.min() + 1e-12)
        im = axes[idx].imshow(
            data_norm,
            aspect="auto",
            origin="lower",
            extent=[power.times[0], power.times[-1],
                    power.freqs[0], power.freqs[-1]],
            vmin=0,
            vmax=1,
            cmap="Reds",
        )
        axes[idx].set_title(ch)
        axes[idx].set_ylabel("Freq (Hz)")
        axes[idx].set_xlabel("Time (s)")

    # Hide any unused subplots
    for ax in axes[n_channels:]:
        ax.axis("off")

    # Add a single colorbar to the right
    fig.subplots_adjust(right=0.88)
    cbar_ax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
    plt.colorbar(im, cax=cbar_ax)

    plt.tight_layout(rect=[0, 0, 0.88, 1])


def plot_tf_difference(power1, power2):
    assert np.array_equal(power1.ch_names, power2.ch_names)
    assert np.array_equal(power1.times, power2.times)
    channels = power1.ch_names
    n_channels = len(channels)
    n_cols = 4
    n_rows = int(np.ceil(n_channels / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 3 * n_rows))
    axes = axes.flatten()

    # Normalize each channel's power between 0 and 1
    for idx, ch in enumerate(channels):
        diff = power1.data[idx] - power2.data[idx]
        norm = TwoSlopeNorm(vmin=diff.min(), vcenter=0, vmax=diff.max())
        im = axes[idx].imshow(
            diff,
            aspect="auto",
            origin="lower",
            extent=[
                power1.times[0],
                power1.times[-1],
                power1.freqs[0],
                power1.freqs[-1],
            ],
            cmap="bwr",
            norm=norm,
        )
        axes[idx].set_title(ch)
        axes[idx].set_ylabel("Freq (Hz)")
        axes[idx].set_xlabel("Time (s)")

    # Hide any unused subplots
    for ax in axes[n_channels:]:
        ax.axis("off")

    # Add a single colorbar to the right
    fig.subplots_adjust(right=0.88)
    cbar_ax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
    plt.colorbar(im, cax=cbar_ax)

    plt.tight_layout(rect=[0, 0, 0.88, 1])


def compute_band_ratios(
    power,
    freqs,
    bands={
        "delta": (1, 4),
        "theta": (4, 8),
        "alpha": (8, 13),
        "beta": (13, 30),
        "gamma": (30, 50),
    },
):
    """
    Compute normalized average power per band per channel for PSD data.
    power: shape (n_epochs, n_channels, n_freqs)
    freqs: shape (n_freqs,)
    Returns: dict of band -> array of shape (n_channels,)
    """

    # Get frequency indices for each band
    band_indices = {
        band: np.where((freqs >= low) & (freqs < high))[0]
        for band, (low, high) in bands.items()
    }

    # Average power over epochs: shape (n_channels, n_freqs)
    mean_power = power.mean(axis=0)

    # Calculate normalized average power per band per channel
    band_power_norm = {}
    for band, idxs in band_indices.items():
        band_power_norm[band] = []
        for ch in range(mean_power.shape[0]):
            data = mean_power[ch]
            # Normalize the PSD for this channel
            data_norm = (data - data.min()) / (data.max() - data.min() + 1e-12)
            # Average over band freqs
            band_avg = data_norm[idxs].mean()
            band_power_norm[band].append(band_avg)
        band_power_norm[band] = np.array(band_power_norm[band])

    return band_power_norm


if __name__ == "__main__":
    exp_path = os.path.join("exp_data", "02_Experimental")
    control_path = os.path.join("exp_data", "01_Control")
    glob_pattern = os.path.join("**", "*.xdf")

    exp_files = glob.glob(os.path.join(exp_path, glob_pattern), recursive=True)
    control_files = glob.glob(os.path.join(control_path, glob_pattern), recursive=True)[
        :6
    ]
    # CTRL03-sub-129059-old error
    read_data(exp_files[0])
