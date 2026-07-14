# LC Ephys and tongue movement kinematics

Scripts to produce figure panels associated with Lightning Pose tongue kinematics and relationship to LC electrophysiology.

https://github.com/AllenNeuralDynamics/LC-ephys-tonguemovements.git

## Data assets

**LCrecordings_combined_units**
- Curated ephys data table

**LC-subject-level-processing**
- Ephys spike time data

**keypoint_tracking_bottomview_LCrecordings_20260403**
- Raw and processed keypoint tracking data
- Processed via [`tongue_analysis.py`](https://github.com/AllenNeuralDynamics/aind-dynamic-foraging-behavior-video-analysis/blob/cfda1b41e9e317f8859ecd05be0b4e794b86da32/src/aind_dynamic_foraging_behavior_video_analysis/kinematics/tongue_analysis.py#L51)

**LC_percentile_meshes_2026-07-10_21-13-43**
- LC mesh

## Processing metadata for keypoint_tracking_bottomview_LCrecordings_20260403

- [x] Create processing metadata JSON per `aind-data-schema`
- [x] Point to GitHub repo for intermediate data asset generation
- [x] Include required input JSON file of asset names (`pred_csv_list_LCmanuscript.json`, branch `LC_manuscript`)
- [ ] Combine processing metadata with asset — [issue #1](https://github.com/AllenNeuralDynamics/LC-ephys-tonguemovements/issues/1)
- [ ] Consider combining raw and videoprocessed (Lightning Pose output) assets for clarity
  - These assets are not used by the capsule directly
  - Relevant as inputs to generate the intermediate asset; may want to include on publishing
- [ ] Remove other unused data assets