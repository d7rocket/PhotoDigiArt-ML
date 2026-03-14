"""Project state serialization and deserialization.

Saves/loads the complete Apollo 7 project state to/from JSON files
with the .apollo7 extension. Human-readable format for debuggability.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Supported project file versions
_SUPPORTED_VERSIONS = {"1.0"}


@dataclass
class ProjectState:
    """Complete serializable project state.

    Captures all parameters, references, and cached data needed
    to fully restore an Apollo 7 session.
    """

    version: str = "1.0"
    photo_paths: list[str] = field(default_factory=list)
    sim_params: dict[str, float] = field(default_factory=dict)
    postfx_params: dict[str, Any] = field(default_factory=dict)
    rendering_params: dict[str, float] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    layout_mode: str = "depth_projected"
    multi_photo_mode: str = "stacked"
    depth_exaggeration: float = 4.0
    point_cloud_snapshot: dict | None = None
    cached_features: dict | None = None


def save_project(state: ProjectState, path: str) -> None:
    """Serialize ProjectState to a JSON file.

    Args:
        state: The project state to save.
        path: Output file path (should use .apollo7 extension).
    """
    data = asdict(state)
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Project saved to %s", path)


def load_project(path: str) -> ProjectState:
    """Deserialize ProjectState from a JSON file.

    Validates the version field and warns about missing photo paths
    without crashing.

    Args:
        path: Path to the .apollo7 project file.

    Returns:
        Reconstructed ProjectState.

    Raises:
        ValueError: If the project file version is unsupported.
        FileNotFoundError: If the project file does not exist.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Version validation
    version = data.get("version", "unknown")
    if version not in _SUPPORTED_VERSIONS:
        raise ValueError(
            f"Unsupported project file version: {version}. "
            f"Supported: {_SUPPORTED_VERSIONS}"
        )

    # Warn about missing photo paths
    photo_paths = data.get("photo_paths", [])
    for p in photo_paths:
        if not os.path.exists(p):
            logger.warning("Photo path not found: %s", p)

    state = ProjectState(
        version=data.get("version", "1.0"),
        photo_paths=photo_paths,
        sim_params=data.get("sim_params", {}),
        postfx_params=data.get("postfx_params", {}),
        rendering_params=data.get("rendering_params", {}),
        camera_state=data.get("camera_state", {}),
        layout_mode=data.get("layout_mode", "depth_projected"),
        multi_photo_mode=data.get("multi_photo_mode", "stacked"),
        depth_exaggeration=data.get("depth_exaggeration", 4.0),
        point_cloud_snapshot=data.get("point_cloud_snapshot"),
        cached_features=data.get("cached_features"),
    )

    logger.info("Project loaded from %s", path)
    return state
