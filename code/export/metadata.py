#!/usr/bin/env -S uv run --python 3.11 --script
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#     "aind-data-schema>=2,<3",
#     "codeocean>=0.16",
# ]
# ///
"""Write processing metadata for the ``build_all_tongue_movements.py`` output.

This is a *standalone* script: it declares its own dependencies (PEP 723 inline
metadata) so it can be run in an isolated ``uv`` environment without touching the
capsule's main conda environment::

    uv run --python 3.11 --script code/metadata.py

or, because the shebang above forwards to ``uv``::

    ./code/metadata.py

It produces ``/results/processing.json`` describing the analysis that generated
``/results/all_tongue_movements.parquet``, following the recipe at
https://docs.allenneuraldynamics.org/en/latest/explore_analyze/create_processing_metadata.html

"""

from __future__ import annotations

import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import aind_data_schema.core.data_description as ds
import aind_data_schema.core.processing as ps

try:
    from codeocean import CodeOcean
except ImportError:  # pragma: no cover - codeocean is declared as a dependency
    CodeOcean = None


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
CAPSULE_NAME = "LC-ephys-tonguemovements"
DEFAULT_DOMAIN = "https://codeocean.allenneuraldynamics.org"

# Result / data mount points (overridable for running outside the capsule).
BASE = Path("/root/capsule/data/keypoint_tracking_bottomview_LCrecordings_20260403")
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", "/results"))

EXPERIMENTERS = ["Matthew Becker"]

# Script (relative to the capsule root) that produced the output.
RUN_SCRIPT = "code/export/build_all_tongue_movements.py"
REPO_DIR = Path(__file__).resolve().parent.parent




def get_commit_hash() -> str | None:
    """Return the current git commit hash of the capsule, if available.

    Prefers the Code Ocean ``CO_COMMIT_HASH`` env var (set for reproducible
    runs); otherwise falls back to ``git rev-parse HEAD``.
    """
    env_hash = os.environ.get("CO_COMMIT_HASH") or os.environ.get("GIT_COMMIT")
    if env_hash:
        return env_hash
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[warn] Could not determine git commit hash: {exc}")
        return None


# --------------------------------------------------------------------------- #
# Build the processing metadata
# --------------------------------------------------------------------------- #
def build_processing() -> ps.Processing:
    """Assemble a ``Processing`` object for the tongue-movements analysis."""
    capsule_url = "https://github.com/AllenNeuralDynamics/LC-ephys-tonguemovements.git"
    end_time = datetime.now(timezone.utc)
    start_env = os.environ.get("PROCESS_START_DATE_TIME")
    start_time = datetime.fromisoformat(start_env) if start_env else end_time

    code = ps.Code(
        name=CAPSULE_NAME,
        url=capsule_url,
        commit_hash=get_commit_hash(),
        run_script=RUN_SCRIPT,
    )

    data_process = ps.DataProcess(
        name="build_all_tongue_movements",
        stage=ps.ProcessStage.ANALYSIS,
        process_type=ps.ProcessName.ANALYSIS,
        experimenters=EXPERIMENTERS,
        start_date_time=start_time,
        end_date_time=end_time,
        code=code,
        notes=(
            "Collected and annotated tongue movements across sessions and saved "
            "the combined movements table to all_tongue_movements.parquet. "
            "Input data assets were read from the attached Code Ocean assets."
        ),
    )

    return ps.Processing(data_processes=[data_process])


def main() -> None:

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    processing = ps.Processing.model_validate_json((BASE / "processing.json").read_text())
    processing = processing + build_processing()
    processing.write_standard_file(RESULTS_DIR)
    print(f"Wrote {RESULTS_DIR / 'processing.json'}")

    data_description = ds.DataDescription.model_validate_json((BASE / "data_description.json").read_text())
    data_description.source_data = ["keypoint-tracking-bottomview-LCrecordings_2026-04-03_18-07-14"]
    data_description.write_standard_file(RESULTS_DIR)
    print(f"Wrote {RESULTS_DIR / 'data_description.json'}")


if __name__ == "__main__":
    main()
