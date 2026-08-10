# LC Ephys and tongue movement kinematics

Scripts to produce figure panels associated with Lightning Pose tongue kinematics and relationship to LC electrophysiology.

Code Ocean release:
https://codeocean.allenneuraldynamics.org/capsule/8486617/

Github:
https://github.com/AllenNeuralDynamics/LC-ephys-tonguemovements.git

## Data assets

**LCrecordings_combined_units**
- Curated ephys data table (Sue)

**LC-subject-level-processing**
- Ephys spike time data (Sue)

**keypoint_tracking_bottomview_LCrecordings_20260403**
- Raw and processed keypoint tracking data
- Processed via [`tongue_analysis.py`](https://github.com/AllenNeuralDynamics/aind-dynamic-foraging-behavior-video-analysis/blob/cfda1b41e9e317f8859ecd05be0b4e794b86da32/src/aind_dynamic_foraging_behavior_video_analysis/kinematics/tongue_analysis.py#L51)

## Key analysis steps

Main pipeline: [`code/tongue_kinematics_ephys_figures.ipynb`](code/tongue_kinematics_ephys_figures.ipynb) (entry point: `code/run`).

1. **Filter units and sessions** by QC criteria (ISI violations, opto-tagging fit, trial count, etc.) and tracking quality (coverage, movement duration).
2. **Attach spike times** to filtered units from per-session curated summary files (`find_summary_pkl`, `ensure_spike_times_column`).
3. **Count spikes per trial** in baseline/response windows aligned to go-cue (`make_session_bundle`, `analyze_unit_for_session`).
4. **Compute reaction times** from tongue-movement annotations (`build_trial_features`, using `annotate_movement_timing`/`add_lick_metadata_to_movements` from `aind-dynamic-foraging-behavior-video-analysis`).
5. **Correlate spike counts with reaction time** per unit (Spearman/Pearson, BH-FDR corrected) (`analyze_unit_correlations`, `run_and_plot_for_predictor`).
6. **Test spatial structure** of correlation strength across LC anatomy (CCF coordinates), via linear-trend and kNN permutation tests (`spatial_dependence_summary`, [`ccf_utils.py`](code/ccf_utils.py)).
7. **Cross-check** against an independently computed behavior-outcome table (`features_combined_beh_all.pkl`).

A separate export step builds the full annotated movements table: [`code/export/build_all_tongue_movements.py`](code/export/build_all_tongue_movements.py) (metadata written by [`code/export/metadata.py`](code/export/metadata.py)).

## Outputs
### Figure Outputs

**`results/ephys_kinematics_panels/`** — figure panels (`.png`/`.svg`, each with a companion `.csv` of source data), named by figure ID:

| Figure | Description |
|---|---|
| `FigureS12g_example_trials_with_kins` | Example trials: tongue position + spike raster around go-cue |
| `FigureS15g_example_trial_zoom_for_reaction_time` | Zoomed single-trial example near go-cue |
| `spkct_rt`, `spkct_rt_bl` | Population summary: spike-count vs. reaction-time correlations (response / baseline window) |
| `FigureS15l_example_unit_spkct_vs_rt(_bl)` | Example unit: spike count vs. reaction time (response / baseline window) |
| `FigureS15jm_spatial_tstats` | Correlation strength mapped onto LC anatomy, with spatial trend/permutation tests |
| `FigureS15k`, `FigureS15n` | Validation scatterplots vs. independently computed T-stats |

### Separate Outputs
**`results/all_tongue_movements.parquet`** — combined, annotated tongue-movement table across sessions.

**`results/processing.json`, `results/data_description.json`** — AIND processing/data-description metadata for the above table.