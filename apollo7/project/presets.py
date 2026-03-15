"""Preset management for simulation and post-processing parameters.

Presets are stored as JSON files organized by category subdirectories
under the presets directory (default: ~/.apollo7/presets/).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default categories shipped with the application
DEFAULT_CATEGORIES = ["Organic", "Geometric", "Chaotic", "Calm", "Custom"]

# Built-in presets demonstrating different parameter combinations
_BUILTIN_PRESETS: dict[str, dict[str, dict]] = {
    "Organic": {
        "Flowing Water": {
            "sim_params": {
                "noise_frequency": 0.3,
                "noise_amplitude": 1.5,
                "noise_octaves": 6,
                "turbulence_scale": 1.2,
                "viscosity": 0.3,
                "speed": 0.8,
                "damping": 0.95,
            },
            "postfx_params": {
                "bloom_strength": 0.06,
                "trail_length": 0.7,
            },
        },
        "Breathing Cloud": {
            "sim_params": {
                "noise_frequency": 0.15,
                "noise_amplitude": 0.8,
                "noise_octaves": 3,
                "turbulence_scale": 2.0,
                "attraction_strength": 0.7,
                "speed": 0.5,
                "damping": 0.98,
            },
            "postfx_params": {
                "bloom_strength": 0.1,
            },
        },
    },
    "Geometric": {
        "Crystal Grid": {
            "sim_params": {
                "noise_frequency": 1.5,
                "noise_amplitude": 0.3,
                "noise_octaves": 2,
                "turbulence_scale": 0.5,
                "repulsion_strength": 0.8,
                "repulsion_radius": 0.15,
                "speed": 1.0,
                "damping": 0.99,
            },
            "postfx_params": {
                "bloom_strength": 0.03,
                "ssao_intensity": 1.5,
            },
        },
    },
    "Chaotic": {
        "Storm": {
            "sim_params": {
                "noise_frequency": 2.0,
                "noise_amplitude": 2.5,
                "noise_octaves": 8,
                "turbulence_scale": 3.0,
                "speed": 3.0,
                "damping": 0.9,
                "gravity": [0.0, -0.5, 0.0],
            },
            "postfx_params": {
                "bloom_strength": 0.15,
                "trail_length": 0.9,
            },
        },
    },
    "Calm": {
        "Zen Garden": {
            "sim_params": {
                "noise_frequency": 0.1,
                "noise_amplitude": 0.3,
                "noise_octaves": 2,
                "turbulence_scale": 0.5,
                "speed": 0.2,
                "damping": 0.995,
                "attraction_strength": 0.3,
            },
            "postfx_params": {
                "bloom_strength": 0.02,
                "dof_aperture": 1.5,
            },
        },
    },
}


def lerp_presets(preset_a: dict, preset_b: dict, t: float) -> dict:
    """Interpolate between two presets at position t.

    Linearly interpolates numeric parameters, component-wise interpolates
    list/tuple values, and snaps non-numeric values at t=0.5.

    Args:
        preset_a: First preset dict with 'sim_params' and 'postfx_params'.
        preset_b: Second preset dict with 'sim_params' and 'postfx_params'.
        t: Interpolation position, clamped to [0, 1].
           0.0 = fully preset_a, 1.0 = fully preset_b.

    Returns:
        Interpolated preset dict with same structure.
    """
    t = max(0.0, min(1.0, t))
    result: dict[str, Any] = {}

    for section in ("sim_params", "postfx_params"):
        dict_a = preset_a.get(section, {})
        dict_b = preset_b.get(section, {})
        all_keys = set(dict_a.keys()) | set(dict_b.keys())
        merged: dict[str, Any] = {}

        for key in all_keys:
            va = dict_a.get(key)
            vb = dict_b.get(key)

            # Both present
            if va is not None and vb is not None:
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                    merged[key] = va + (vb - va) * t
                elif isinstance(va, (list, tuple)) and isinstance(vb, (list, tuple)):
                    merged[key] = [
                        a_i + (b_i - a_i) * t
                        for a_i, b_i in zip(va, vb)
                    ]
                else:
                    # Non-numeric: snap at t=0.5
                    merged[key] = va if t < 0.5 else vb
            elif va is not None:
                # Key only in A: lerp with 0.0 default
                if isinstance(va, (int, float)):
                    merged[key] = va + (0.0 - va) * t
                elif isinstance(va, (list, tuple)):
                    merged[key] = [a_i * (1.0 - t) for a_i in va]
                else:
                    merged[key] = va if t < 0.5 else None
            else:
                # Key only in B: lerp from 0.0 default
                if isinstance(vb, (int, float)):
                    merged[key] = 0.0 + (vb - 0.0) * t
                elif isinstance(vb, (list, tuple)):
                    merged[key] = [b_i * t for b_i in vb]
                else:
                    merged[key] = None if t < 0.5 else vb

        # Remove None values from snapped non-numeric
        merged = {k: v for k, v in merged.items() if v is not None}
        result[section] = merged

    return result


class PresetManager:
    """Manages named parameter presets organized by category.

    Presets are stored as individual JSON files in category
    subdirectories under the presets root directory.
    """

    def __init__(self, presets_dir: str | Path | None = None) -> None:
        """Initialize preset manager.

        Args:
            presets_dir: Root directory for presets.
                         Defaults to ~/.apollo7/presets/.
        """
        if presets_dir is None:
            presets_dir = Path.home() / ".apollo7" / "presets"
        self._presets_dir = Path(presets_dir)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        """Create default category directories and ship built-in presets."""
        for category in DEFAULT_CATEGORIES:
            cat_dir = self._presets_dir / category
            cat_dir.mkdir(parents=True, exist_ok=True)

        # Write built-in presets if they don't exist
        for category, presets in _BUILTIN_PRESETS.items():
            cat_dir = self._presets_dir / category
            for name, data in presets.items():
                preset_file = cat_dir / f"{name}.json"
                if not preset_file.exists():
                    with open(preset_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)

    def save_preset(
        self,
        name: str,
        category: str,
        sim_params: dict[str, Any],
        postfx_params: dict[str, Any],
    ) -> Path:
        """Save a preset as a JSON file in the category subfolder.

        Args:
            name: Preset name (used as filename).
            category: Category subdirectory name.
            sim_params: Simulation parameter values.
            postfx_params: Post-processing parameter values.

        Returns:
            Path to the created preset file.
        """
        cat_dir = self._presets_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        preset_file = cat_dir / f"{name}.json"
        data = {
            "sim_params": sim_params,
            "postfx_params": postfx_params,
        }
        with open(preset_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info("Preset saved: %s/%s", category, name)
        return preset_file

    def load_preset(self, name: str, category: str) -> dict[str, Any]:
        """Load a preset and return its parameters.

        Args:
            name: Preset name.
            category: Category subdirectory name.

        Returns:
            Dict with 'sim_params' and 'postfx_params' keys.

        Raises:
            FileNotFoundError: If the preset file does not exist.
        """
        preset_file = self._presets_dir / category / f"{name}.json"
        with open(preset_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def list_presets(self) -> dict[str, list[str]]:
        """Return all presets grouped by category.

        Returns:
            Dict mapping category name to list of preset names.
        """
        result: dict[str, list[str]] = {}
        if not self._presets_dir.exists():
            return result

        for cat_dir in sorted(self._presets_dir.iterdir()):
            if not cat_dir.is_dir():
                continue
            presets = []
            for f in sorted(cat_dir.iterdir()):
                if f.suffix == ".json":
                    presets.append(f.stem)
            if presets:
                result[cat_dir.name] = presets
        return result

    def delete_preset(self, name: str, category: str) -> bool:
        """Delete a preset file.

        Args:
            name: Preset name.
            category: Category subdirectory name.

        Returns:
            True if the preset was deleted, False if it didn't exist.
        """
        preset_file = self._presets_dir / category / f"{name}.json"
        if preset_file.exists():
            preset_file.unlink()
            logger.info("Preset deleted: %s/%s", category, name)
            return True
        return False

    def get_categories(self) -> list[str]:
        """List all category subdirectory names.

        Returns:
            Sorted list of category names.
        """
        if not self._presets_dir.exists():
            return []
        return sorted(
            d.name for d in self._presets_dir.iterdir() if d.is_dir()
        )
