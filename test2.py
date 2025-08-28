import os
import pickle
import numpy as np
import mne
from mne.stats import spatio_temporal_cluster_1samp_test
import glob
import matplotlib.pyplot as plt

def analyze_tfr_feature(data, band, measure, p_threshold=0.05, output_dir="tfr_analysis"):

    print(f"--- Analyzing: {band.upper()} Band / {measure.upper()} ---")

    stim_neutral = data['tfr'][band][measure]['stim']['neutral'].copy()
    stim_trigger = data['tfr'][band][measure]['stim']['trigger'].copy()

    if measure == 'power':
        stim_neutral.apply_baseline(baseline=(None, 0), mode='logratio')
        stim_trigger.apply_baseline(baseline=(None, 0), mode='logratio')
        
    elif measure == 'itc':
        stim_neutral.apply_baseline(baseline=(None, 0), mode='mean')
        stim_trigger.apply_baseline(baseline=(None, 0), mode='mean')

    difference_tfr = stim_trigger - stim_neutral
    diff_data = difference_tfr.data 
    
    montage = mne.channels.read_custom_montage('ceegrid_coords.csv', coord_frame='head')
    difference_tfr.info.set_montage(montage)
    
    adjacency, _ = mne.channels.find_ch_adjacency(difference_tfr.info, ch_type='eeg')  
    
    difference_reshaped = np.transpose(diff_data, (1, 2, 0))
    n_freqs, n_times, n_channels = difference_reshaped.shape
    difference_reshaped = difference_reshaped.reshape(n_freqs * n_times, n_channels)

    t_obs, clusters, cluster_p_values, H0 = spatio_temporal_cluster_1samp_test(
            difference_reshaped,
            n_permutations=1000,
            adjacency=adjacency,
            tail=0,
            n_jobs=-1,
            threshold=None 
        )
    
    significant_clusters = np.where(cluster_p_values < p_threshold)[0]
    print(f"Result: FOUND {len(significant_clusters)} SIGNIFICANT!")

    sig_ch_indices = np.unique(np.concatenate([clusters[i][0] for i in significant_clusters]))
        
    sig_ch_names = [difference_tfr.ch_names[i] for i in sig_ch_indices]
    
    sig_tfr = difference_tfr.copy().pick(sig_ch_names)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    sig_tfr.plot(
        axes=ax,
        colorbar=True,
        show=False,
        combine='mean',
        
    )
    if measure == 'power':
            cbar_label = 'Difference (Log Ratio)'
    else: # itc 
        cbar_label = 'Difference (ITC)'
        
    fig.axes[-1].set_ylabel(cbar_label)
    ax.set_title(f"Mean Difference in {band} {measure} (Significant Channels)")
    
    os.makedirs(output_dir, exist_ok=True)
    fig_path = os.path.join(output_dir, f"sig_diff_{band}_{measure}.png")
    fig.savefig(fig_path)
    print(f"Plot saved to: {fig_path}")

    fig_topo, ax_topo = plt.subplots(1, 1, figsize=(7, 7))
    t_obs_mask = np.zeros((t_obs.shape[0], 1), dtype=bool)
    t_obs_mask[sig_ch_indices, 0] = True
    
    im, _ = mne.viz.plot_topomap(t_obs, difference_tfr.info, 
                         ch_type='eeg', 
                         axes=ax_topo, 
                         show=False,  # show plot in new window
                         names=montage.ch_names, 
                         extrapolate='local', 
                         mask=t_obs_mask,
                         mask_params=dict(markersize=12, markerfacecolor='y'))
    ax_topo.set_title(f"T-values for {band} {measure} Difference")
    
    fig_topo.colorbar(im, ax=ax_topo, label="T-values", location='bottom', shrink=0.6)
    ax_topo.set_title(f"T-values for {band.capitalize()} {measure.capitalize()} Difference")
    
    fig_topo_path = os.path.join(output_dir, f"sig_topo_{band}_{measure}.png")
    fig_topo.savefig(fig_topo_path)
    print(f"Topography plot saved to: {fig_topo_path}")
    


for file in glob.glob("/Users/aditya/Downloads/processed/**/*.pkl"):
    print(f"Processing file: {file}")
    with open(file, "rb") as f:
        data = pickle.load(f)
        
        patient = file.split("/")[-2]
        print(f"Patient: {patient}")


    BANDS = ['alpha', 'beta', 'gamma', 'delta', 'theta']
    MEASURES = ['power', 'itc']

    for band in BANDS:
        for measure in MEASURES:
            analyze_tfr_feature(data, band, measure, p_threshold=0.005, output_dir=f"{patient}_analysis")

    print("\nAnalysis complete.")