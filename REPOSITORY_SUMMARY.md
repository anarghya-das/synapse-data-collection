# Hearing Data Collection Repository Summary

## Overview
This repository contains a comprehensive **hearing study data collection system** designed for multi-modal neurophysiological experiments. The system integrates behavioral testing, brain activity recording (EEG/fNIRS), video capture, and synchronized data analysis to study auditory processing and hearing responses.

## Primary Purpose
The repository enables researchers to:
- Conduct controlled auditory experiments with various sound stimuli
- Collect synchronized neurophysiological data (EEG, fNIRS) 
- Record behavioral responses and video data
- Process and analyze multi-modal experimental data
- Study hearing sensitivity and auditory processing across different populations

## Key Components

### 1. Experimental Framework
- **PsychoPy Integration**: Uses PsychoPy for precise stimulus presentation and response collection
- **Lab Streaming Layer (LSL)**: Provides real-time data synchronization across multiple recording devices
- **Configurable Protocols**: YAML-based configuration system supporting different experimental modalities (EEG, fNIRS, test modes)

### 2. Auditory Stimuli Categories
- **HLT (Hearing Level Tones)**: Pure tones at various intensity levels (3dB, 5dB, 10dB, 20dB, 40dB) for hearing threshold testing
- **AST (Auditory Stimuli)**: Complex sounds including baby crying, chewing, sneezing, and environmental sounds
- **LET**: Additional auditory stimulus category (specific contents in stimuli/let directory)

### 3. Multi-Modal Data Collection
- **Neurophysiological**: EEG and fNIRS recording capabilities with precise timing synchronization
- **Behavioral**: Response collection and reaction time measurement
- **Video**: Raspberry Pi and USB camera integration for facial expression and movement recording
- **Physiological**: Support for additional sensors (PPG/pulse data collection)

### 4. Data Processing Pipeline
- **Raw Data Handling**: Processing of XDF (Extensible Data Format) files containing time-series data
- **EEG Analysis**: Complete EEG preprocessing pipeline using MNE-Python including:
  - Artifact rejection (AutoReject)
  - Independent Component Analysis (ICA)
  - Component labeling (ICLabel)
  - Epoching and event-related analysis
- **Video Processing**: Automated video segmentation and synchronization with experimental markers
- **Batch Analysis**: Scripts for processing multiple subjects and experimental sessions

### 5. Hardware Integration
- **Raspberry Pi**: Remote video recording with real-time streaming capabilities
- **Multiple Camera Support**: USB cameras and Pi cameras with FFMPEG/GStreamer streaming
- **Neurophysiology Equipment**: Integration with standard EEG/fNIRS recording systems
- **Audio Systems**: Calibrated audio presentation through PsychToolbox

## Experimental Workflow

### Setup Phase
1. Configure experimental parameters in `config.yaml`
2. Set up recording environment (EEG/fNIRS electrodes, cameras)
3. Initialize Lab Streaming Layer for data synchronization
4. Launch data recording software (Lab Recorder)

### Data Collection Phase
1. Run PsychoPy experiment (`hearing.py` or `passive.py`)
2. Present auditory stimuli according to configured protocol
3. Collect synchronized data streams:
   - EEG/fNIRS signals
   - Behavioral responses
   - Video recordings
   - Experimental markers and timing

### Analysis Phase
1. Move raw data files to appropriate directories (`exp_data/`, `input/`)
2. Run processing scripts to segment and analyze data
3. Generate processed outputs including:
   - Epoched neurophysiological data
   - Segmented video files
   - Statistical analysis results
   - Visualization plots

## Technical Architecture

### File Organization
```
├── hearing.py/passive.py     # Main experiment scripts
├── config.yaml              # Experimental configuration
├── sounds/                   # Organized audio stimuli
├── exp_data/                 # Raw experimental data storage
├── input/                    # Video input processing
├── analyze_subject.py        # Single-subject analysis
├── batch_analysis.ipynb      # Multi-subject analysis
├── processing.ipynb          # Data processing workflows
├── utils.py                  # Common analysis functions
└── usb-camera/              # Camera recording utilities
```

### Dependencies
- **PsychoPy**: Experiment presentation and behavioral data collection
- **MNE-Python**: EEG/MEG data analysis
- **PyXDF**: XDF file format handling
- **OpenCV**: Video processing
- **NumPy/SciPy**: Numerical computations
- **Lab Streaming Layer**: Real-time data synchronization

## Research Applications
This system is designed for studies investigating:
- Hearing sensitivity and threshold detection
- Auditory processing disorders
- Neurophysiological responses to sound
- Multi-modal sensory integration
- Clinical hearing assessments
- Developmental auditory neuroscience

## Data Types Supported
- **Neurophysiological**: EEG, fNIRS time-series data
- **Behavioral**: Reaction times, button press responses
- **Video**: Facial expressions, head movements, eye tracking potential
- **Audio**: Stimulus presentation logs and timing
- **Physiological**: Heart rate, pulse data (via additional sensors)

The repository provides a complete end-to-end solution for conducting sophisticated hearing research with precise temporal control and multi-modal data integration.