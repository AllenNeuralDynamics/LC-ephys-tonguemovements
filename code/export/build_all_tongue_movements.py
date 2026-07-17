"""
Build and save the combined tongue-movements table.

  1. Load and filter the combined ephys unit table.
  2. Attach spike times per unit.
  3. Collect and annotate tongue movements across sessions.
  4. Save the combined movements table to a parquet file.
"""

import re
import pickle
from pathlib import Path
from typing import Optional, Iterable, Dict, Any

import pandas as pd

from aind_dynamic_foraging_behavior_video_analysis.kinematics.tongue_analysis import (
    get_session_name_from_path,
)
from aind_dynamic_foraging_behavior_video_analysis.kinematics.tongue_kinematics_utils import (
    annotate_movement_timing,
    add_lick_metadata_to_movements,
)


# =========================
# Load ephys data
# =========================
with open('/root/capsule/data/LCrecordings_combined_units/combined_unit_tbl.pkl', 'rb') as file:
    combined_ephys_data = pickle.load(file)


# =========================
# Filter units
# =========================
# ---------- criteria filter ----------
criteria = {
    "isi_violations": {"bounds": [0.0, 0.1]},
    "p_max": {"bounds": [0.5, 1.0]},
    "lat_max_p": {"bounds": [0.005, 0.02]},
    "eu": {"bounds": [0.0, 0.25]},
    "corr": {"bounds": [0.95, 1.0]},
    "qc_pass": {"items": [True]},
    "peak": {"bounds": [-1000, 0]},
    "trial_count": {"bounds": [100, 2000]},
    "in_df": {"items": [True]},
}

mask = pd.Series(True, index=combined_ephys_data.index)
for col, rule in criteria.items():
    if "bounds" in rule:
        lo, hi = rule["bounds"]
        mask &= combined_ephys_data[col].between(lo, hi)
    if "items" in rule:
        mask &= combined_ephys_data[col].isin(rule["items"])

criteria_filtered = combined_ephys_data.loc[mask].copy()

# ---------- session allow (prefix-based) ----------
pred_csv_list = [
    "/root/capsule/data/BottomViewPylon1-MIB-2025-02-17/inference/behavior_716325_2024-05-31_10-31-14/bottom_camera.csv",
    "/root/capsule/data/BottomViewPylon1-MIB-2025-02-17/inference/behavior_717121_2024-06-15_10-00-58/bottom_camera.csv",
    "/root/capsule/data/BottomViewPylon1-MIB-2025-02-17/inference/behavior_717259_2024-06-28_11-17-19/bottom_camera.csv",
    "/root/capsule/data/BottomViewPylon1-MIB-2025-02-17/inference/behavior_717263_2024-07-24_10-40-05/bottom_camera.csv",
    "/root/capsule/data/BottomViewPylon1-MIB-2025-02-17/inference/behavior_751004_2024-12-20_13-26-07/bottom_camera.csv",
    "/root/capsule/data/BottomViewPylon1-MIB-2025-02-17/inference/behavior_751004_2024-12-21_13-28-24/bottom_camera.csv",
    "/root/capsule/data/BottomViewPylon1-MIB-2025-02-17/inference/behavior_751004_2024-12-22_13-09-11/bottom_camera.csv",
    "/root/capsule/data/BottomViewPylon1-MIB-2025-02-17/inference/behavior_751004_2024-12-23_14-19-57/bottom_camera.csv",
]

def get_session_prefix(s: str) -> str:
    # 'behavior_751004_2024-12-20_13-26-07' -> 'behavior_751004_2024-12-20'
    return re.sub(r'_\d{2}-\d{2}-\d{2}$', '', s)

session_order_full   = [get_session_name_from_path(p) for p in pred_csv_list]
session_prefix_order = [get_session_prefix(s) for s in session_order_full]
session_prefix_allow = set(session_prefix_order)

# add prefix columns
combined_ephys_data = combined_ephys_data.copy()
combined_ephys_data.loc[:, "session_prefix"]  = combined_ephys_data["session"].map(get_session_prefix)
criteria_filtered.loc[:, "session_prefix"]     = criteria_filtered["session"].map(get_session_prefix)

# ---------- summary table (before vs. after, for queried prefixes only) ----------
counts_before = combined_ephys_data.groupby("session_prefix").size().rename("units_before")
counts_after  = criteria_filtered.groupby("session_prefix").size().rename("units_after")

base = pd.concat([counts_before, counts_after], axis=1).reindex(session_prefix_order)
base["units_before"] = base["units_before"].astype("Int64")        # keep NA if not present before
base["units_after"]  = base["units_after"].fillna(0).astype(int)   # 0 if none survived

session_summary_allowed = base.reset_index().rename(columns={"index": "session_prefix"})

# ---------- final filtered units (criteria + session prefix allow) ----------
filtered_ephys = criteria_filtered.loc[
    criteria_filtered["session_prefix"].isin(session_prefix_allow)
].copy()

# ---------- prints ----------
print(f"Filtered units: {len(filtered_ephys)} / {len(combined_ephys_data)}")
print(session_summary_allowed.to_string(index=False))


# =========================
# Attach spike times per unit
# =========================
ROOT_SCRATCH = "/data/LC-subject-level-processing"

def get_animal_id(session: str) -> str:
    m = re.match(r'^behavior_(\d+)_', session)
    if not m:
        raise ValueError(f"Cannot parse animal id from session: {session}")
    return m.group(1)

def find_summary_pkl(root: str, session: str) -> Optional[Path]:
    """Try exact path; if missing, fall back to prefix glob search."""
    animal = get_animal_id(session)
    exact = Path(root) / animal / session / "ephys" / "opto" / "curated" / f"{session}_curated_soma_opto_tagging_summary.pkl"
    if exact.exists():
        return exact
    pref = get_session_prefix(session)
    candidates = list((Path(root) / animal).glob(f"{pref}_*/ephys/opto/curated/*_curated_soma_opto_tagging_summary.pkl"))
    return candidates[0] if candidates else None

def ensure_spike_times_column(df: pd.DataFrame, session_dir: Path) -> pd.DataFrame:
    """Attach 'spike_times' from NWB if possible; else create empty column."""
    if "spike_times" in df.columns:
        return df
    try:
        from pynwb import NWBHDF5IO
        nwb_files = list(session_dir.rglob("*.nwb"))
        if nwb_files:
            with NWBHDF5IO(str(nwb_files[0]), "r") as io:
                nwb = io.read()
                units_df = nwb.units.to_dataframe()  # index = unit id
            df = df.merge(units_df[["spike_times"]], left_on="unit_id", right_index=True, how="left")
            if "spike_times" not in df.columns:
                df["spike_times"] = None
            return df
    except Exception as e:
        print(f"[warn] Could not attach spike_times from NWB: {e}")
    df = df.copy()
    df["spike_times"] = None
    return df

# ---- main loop ----
units_with_spikes = []
for session, subdf in filtered_ephys.groupby("session"):
    pkl_path = find_summary_pkl(ROOT_SCRATCH, session)
    if pkl_path is None:
        print(f"[skip] No summary .pkl found for {session}")
        continue

    with open(pkl_path, "rb") as f:
        ephys_session_data = pickle.load(f)
    if not isinstance(ephys_session_data, pd.DataFrame):
        try:
            ephys_session_data = pd.DataFrame(ephys_session_data)
        except Exception:
            print(f"[skip] Summary not a DataFrame for {session}")
            continue

    session_dir = pkl_path.parents[3]  # .../{animal}/{session}/
    ephys_session_data = ensure_spike_times_column(ephys_session_data, session_dir)

    unit_ids = subdf["unit"].unique()
    ephys_data = (
        ephys_session_data[ephys_session_data["unit_id"].isin(unit_ids)]
        .copy()
        .assign(session=session)
    )
    print(f"[ok] {session}: {len(ephys_data)}/{len(unit_ids)} units with 'spike_times' column")
    units_with_spikes.append(ephys_data)

units_with_spikes = (
    pd.concat(units_with_spikes, ignore_index=True)
    if units_with_spikes else pd.DataFrame(columns=["session","unit_id","spike_times"])
)
print("Final units_with_spikes shape:", units_with_spikes.shape)


# =========================
# Locate + load session intermediate data
# =========================
# Root where kinematics/intermediate data live
KIN_ROOT = Path("/root/capsule/data/keypoint_tracking_bottomview_LCrecordings_20260403")

def find_scratch_session_dir(session: str) -> Path:
    """Return scratch folder for a session; try exact, else prefix glob."""
    exact = KIN_ROOT / session
    if exact.exists():
        return exact
    pref = get_session_prefix(session)
    hits = sorted(KIN_ROOT.glob(pref + "*"))
    if not hits:
        raise FileNotFoundError(f"No scratch folder for session/prefix: {session} / {pref}")
    return hits[0]

def load_intermediate_data(session_dir: Path) -> dict:
    """Load the four intermediate parquet tables for a session."""
    idir = session_dir / "intermediate_data"
    return {
        "movs":   pd.read_parquet(idir / "tongue_movs.parquet"),
        "trials": pd.read_parquet(idir / "nwb_df_trials.parquet"),
        "licks":  pd.read_parquet(idir / "nwb_df_licks.parquet"),
        "kins":   pd.read_parquet(idir / "tongue_kins.parquet"),
    }


# =========================
# Collect + annotate movements across sessions
# =========================
REQUIRED_COLS = {
    "cue_response_movement_number",
    "movement_latency_from_go",
    "movement_number_in_trial",
    "cue_response",
}

def _prepare_movements(movs: pd.DataFrame, licks: pd.DataFrame, df_trials: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure movement annotations exist; return a copy with required columns present.
    """
    tm = movs.copy()

    # (Re)annotate if any required columns are missing
    if not REQUIRED_COLS.issubset(tm.columns):
        tm = add_lick_metadata_to_movements(tm, licks, fields=["timestamps"]).rename(
            columns={"timestamps": "lick_time"}
        )
        tm = annotate_movement_timing(tm, df_trials)

    # Light dtype hygiene (robust joins later)
    if "movement_number_in_trial" in tm.columns:
        tm["movement_number_in_trial"] = pd.to_numeric(
            tm["movement_number_in_trial"], errors="coerce"
        ).astype("Int64")
    if "cue_response_movement_number" in tm.columns:
        tm["cue_response_movement_number"] = pd.to_numeric(
            tm["cue_response_movement_number"], errors="coerce"
        ).astype("Int64")
    if "cue_response" in tm.columns:
        tm["cue_response"] = tm["cue_response"].astype("boolean")
    if "trial" in tm.columns:
        tm["trial"] = pd.to_numeric(tm["trial"], errors="coerce").astype("Int64")

    return tm

def collect_all_movements(
    sessions: Optional[Iterable[str]] = None,
    *,
    progress: bool = True
) -> pd.DataFrame:
    """
    Load each session's intermediates, ensure required movement annotations,
    add a 'session' column, and concatenate into one DataFrame.
    """
    # Default: derive session list from units_with_spikes if not provided
    if sessions is None:
        sessions = getattr(globals().get("units_with_spikes", pd.DataFrame()), "session", pd.Series()).unique()
        sessions = [s for s in sessions if pd.notna(s)]

    all_chunks = []
    for sess in sessions:
        try:
            sdir = find_scratch_session_dir(sess)
            data: Dict[str, Any] = load_intermediate_data(sdir)
            movs   = data["movs"]
            licks  = data["licks"]
            trials = data["trials"]

            tm = _prepare_movements(movs, licks, trials)
            tm = tm.copy()
            tm["session"] = sess  # tag provenance
            all_chunks.append(tm)

            if progress:
                print(f"[ok] {sess}: {len(tm)} movements")

        except Exception as e:
            if progress:
                print(f"[warn] {sess}: skipped due to error -> {e!r}")

    if not all_chunks:
        raise RuntimeError("No movement tables collected. Check sessions / loaders.")

    all_movs = pd.concat(all_chunks, ignore_index=True, copy=False)

    return all_movs


# =========================
# Build + save
# =========================
all_tongue_movements = collect_all_movements()

SAVE_PATH = Path("/results/all_tongue_movements.parquet")
SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
all_tongue_movements.to_parquet(SAVE_PATH)
print(f"Saved {len(all_tongue_movements)} movements to {SAVE_PATH}")
