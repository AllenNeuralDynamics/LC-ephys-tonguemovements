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

The list of input data assets is obtained from the Code Ocean API (via the
``codeocean`` client) so that every asset currently attached to this computation
is recorded as an input.
"""

from __future__ import annotations

import os
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
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", "/results"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
OUTPUT_FILE = RESULTS_DIR / "all_tongue_movements.parquet"

EXPERIMENTERS = ["Matthew Becker"]
PROJECT_NAME = "Discovery-Neuromodulator circuit dynamics during foraging - Subproject 1 Electrophysiological Recordings from NM Neurons During Behavior"
MODALITIES = [ds.Modality.BEHAVIOR, ds.Modality.ECEPHYS]

# Script (relative to the capsule root) that produced the output.
RUN_SCRIPT = "code/build_all_tongue_movements.py"
REPO_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Code Ocean helpers
# --------------------------------------------------------------------------- #
def _get_token() -> str | None:
    """Return a Code Ocean API token from the usual secret env-var names."""
    for name in (
        "CODEOCEAN_TOKEN",
        "CODEOCEAN_API_TOKEN",
        "CUSTOM_KEY",
        "API_SECRET",
    ):
        token = os.environ.get(name)
        if token:
            return token
    return None


def get_attached_asset_names() -> list[str]:
    """Return the names of every data asset attached to this computation.

    Uses the Code Ocean client to look up the current computation
    (``CO_COMPUTATION_ID``) and resolve each attached asset id to its
    registered name. Falls back to the mounted folder names under ``/data`` when
    the API cannot be reached (e.g. no token available outside the capsule).
    """
    domain = os.environ.get("CODEOCEAN_DOMAIN", DEFAULT_DOMAIN)
    token = _get_token()
    computation_id = os.environ.get("CO_COMPUTATION_ID")

    if CodeOcean is not None and token and computation_id:
        client = CodeOcean(domain=domain, token=token)
        computation = client.computations.get_computation(computation_id)
        names: list[str] = []
        for input_asset in computation.data_assets or []:
            asset = client.data_assets.get_data_asset(input_asset.id)
            names.append(asset.name)
        if names:
            return sorted(set(names))
        print("[warn] Computation reported no attached data assets.")

    # Fallback: use the folder names of the mounted assets under /data.
    print(
        "[warn] Falling back to /data mount folder names (Code Ocean API"
        " unavailable or no token/computation id set)."  # noqa: ISC001
    )
    if DATA_DIR.is_dir():
        return sorted(
            p.name for p in DATA_DIR.iterdir() if not p.name.startswith(".")
        )
    return []


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
def build_processing(asset_names: list[str]) -> ps.Processing:
    """Assemble a ``Processing`` object for the tongue-movements analysis."""
    domain = os.environ.get("CODEOCEAN_DOMAIN", DEFAULT_DOMAIN)
    capsule_id = os.environ.get("CO_CAPSULE_ID")
    capsule_url = f"{domain}/capsule/{capsule_id}" if capsule_id else domain
    version = os.environ.get("CO_CAPSULE_VERSION")

    # End time = when the output file was written; start time falls back to the
    # same instant when no separate start is known.
    if OUTPUT_FILE.exists():
        end_time = datetime.fromtimestamp(
            OUTPUT_FILE.stat().st_mtime, tz=timezone.utc
        )
    else:
        end_time = datetime.now(timezone.utc)
    start_env = os.environ.get("PROCESS_START_DATE_TIME")
    start_time = datetime.fromisoformat(start_env) if start_env else end_time

    code = ps.Code(
        name=CAPSULE_NAME,
        url=capsule_url,
        version=version or "1.0",
        commit_hash=get_commit_hash(),
        run_script=RUN_SCRIPT,
        input_data=[ps.DataAsset(name=name) for name in asset_names],
    )

    data_process = ps.DataProcess(
        name="build_all_tongue_movements",
        stage=ps.ProcessStage.ANALYSIS,
        process_type=ps.ProcessName.ANALYSIS,
        experimenters=EXPERIMENTERS,
        start_date_time=start_time,
        end_date_time=end_time,
        output_path=OUTPUT_FILE.name,
        code=code,
        notes=(
            "Collected and annotated tongue movements across sessions and saved "
            "the combined movements table to all_tongue_movements.parquet. "
            "Input data assets were read from the attached Code Ocean assets."
        ),
    )

    return ps.Processing(data_processes=[data_process])


# --------------------------------------------------------------------------- #
# Build the data description metadata
# --------------------------------------------------------------------------- #
def build_data_description(asset_names: list[str]) -> ds.DataDescription:
    """Assemble a ``DataDescription`` for the derived tongue-movements asset."""
    if OUTPUT_FILE.exists():
        creation_time = datetime.fromtimestamp(
            OUTPUT_FILE.stat().st_mtime, tz=timezone.utc
        )
    else:
        creation_time = datetime.now(timezone.utc)

    name = ds.build_data_name(CAPSULE_NAME, creation_time)

    return ds.DataDescription(
        name=name,
        source_data=asset_names,
        creation_time=creation_time,
        institution=ds.Organization.AIND,
        data_level=ds.DataLevel.DERIVED,
        investigators=[ds.Person(name=e) for e in EXPERIMENTERS],
        project_name=PROJECT_NAME,
        modalities=MODALITIES,
        license=ds.License.CC_BY_40,
        funding_source=[ds.Funding(funder=ds.Organization.AI)],
        data_summary=(
            "Combined tongue-movement kinematics annotated across dynamic "
            "foraging sessions, related to spiking of LC neurons."
        ),
    )


def main() -> None:
    asset_names = get_attached_asset_names()
    print(f"Recording {len(asset_names)} attached data asset(s) as inputs:")
    for name in asset_names:
        print(f"  - {name}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    processing = build_processing(asset_names)
    processing.write_standard_file(str(RESULTS_DIR))
    print(f"Wrote {RESULTS_DIR / 'processing.json'}")

    data_description = build_data_description(asset_names)
    data_description.write_standard_file(str(RESULTS_DIR))
    print(f"Wrote {RESULTS_DIR / 'data_description.json'}")


if __name__ == "__main__":
    main()
