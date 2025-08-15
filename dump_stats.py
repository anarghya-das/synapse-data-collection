import argparse
import numpy as np
import os
import pickle
from pathlib import Path

PROCESSED_DIR = "processed"
TIMINGS = ['prestim', 'stim']
DISPS = ['neutral', 'trigger'] # dispositions, may not be the best name

def main():
    stats = {}

    for entry in Path(PROCESSED_DIR).iterdir():
        in_pkl = os.path.join(entry, "data.pkl")
        with open(in_pkl, 'rb') as f:
            data = pickle.load(f)

        tfr_delta_freqs = np.logspace(*np.log10([1, 4]), num=8)
        tfr_theta_freqs = np.logspace(*np.log10([4, 8]), num=8)
        tfr_alpha_freqs = np.logspace(*np.log10([8, 13]), num=8)
        tfr_beta_freqs = np.logspace(*np.log10([13, 30]), num=8)
        tfr_gamma_freqs = np.logspace(*np.log10([30, 50]), num=8)

        tfr_bands = {'delta': tfr_delta_freqs, 'theta': tfr_theta_freqs, 'alpha': tfr_alpha_freqs, 'beta': tfr_beta_freqs, 'gamma': tfr_gamma_freqs}

        avg_negative = {}
        avg_positive = {}
        for disp in DISPS:
            avg_negative[disp] = {}
            avg_positive[disp] = {}
            for band in tfr_bands:
                prestim_power = data['tfr'][band]['power']['prestim'][disp].data
                stim_power = data['tfr'][band]['power']['stim'][disp].data
                diff_power = stim_power - prestim_power
                avg_negative[disp][band] = np.where(diff_power > 0, 0, diff_power).mean()
                avg_positive[disp][band] = np.where(diff_power < 0, 0, diff_power).mean()
        
        avg_negative_ratio = {
            band: float(avg_negative['trigger'][band] / avg_negative['neutral'][band])
            for band in tfr_bands
        }
        avg_positive_ratio = {
            band: float(avg_positive['trigger'][band] / avg_positive['neutral'][band])
            for band in tfr_bands
        }
        
        avg_psd = {}
        for band in tfr_bands:
            avg_psd[band] = {}
            for disp in DISPS:
                psd = data['psd']['normalized_power'][disp]
                freqs = data['psd']['freqs']['prestim'][disp]
                band_mask = (freqs >= tfr_bands[band][0]) & (freqs <= tfr_bands[band][-1])
                avg_psd[band][disp] = psd[band_mask].mean()
        
        avg_psd_ratio = {
            band: float(avg_psd[band]['trigger'] / avg_psd[band]['neutral'])
            for band in tfr_bands
        }

        stats[entry.name] = {
            'avg_negative_ratio': avg_negative_ratio,
            'avg_positive_ratio': avg_positive_ratio,
            'avg_psd_ratio': avg_psd_ratio
        }

    with open(os.path.join("stats", "stats.pkl"), 'wb') as f:
        pickle.dump(stats, f)

main()
