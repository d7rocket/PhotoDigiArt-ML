"""Tests for project save/load functionality."""

import json
import os

import numpy as np
import pytest

from apollo7.project.save_load import ProjectState, save_project, load_project


class TestProjectState:
    """Test ProjectState dataclass serialization."""

    def _make_state(self, photo_paths=None) -> ProjectState:
        """Create a sample ProjectState for testing."""
        return ProjectState(
            photo_paths=photo_paths or ["/path/to/photo1.jpg", "/path/to/photo2.png"],
            sim_params={"noise_frequency": 0.5, "noise_amplitude": 1.0, "speed": 2.0},
            postfx_params={"bloom_strength": 0.04, "dof_enabled": True},
            rendering_params={"point_size": 3.0, "opacity": 0.8, "depth_exaggeration": 5.0},
            camera_state={"position": [0.0, 5.0, 10.0], "rotation": [0.1, 0.2, 0.0, 1.0]},
            layout_mode="depth_projected",
            multi_photo_mode="stacked",
            depth_exaggeration=5.0,
            point_cloud_snapshot={
                "positions": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
                "colors": [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0]],
            },
            cached_features={"photo1": {"color": {"dominant": [255, 0, 0]}}},
        )

    def test_roundtrip_save_load(self, tmp_dir):
        """ProjectState roundtrips through JSON: save then load produces identical state."""
        state = self._make_state()
        path = os.path.join(tmp_dir, "test_project.apollo7")

        save_project(state, path)
        loaded = load_project(path)

        assert loaded.version == state.version
        assert loaded.photo_paths == state.photo_paths
        assert loaded.sim_params == state.sim_params
        assert loaded.postfx_params == state.postfx_params
        assert loaded.rendering_params == state.rendering_params
        assert loaded.camera_state == state.camera_state
        assert loaded.layout_mode == state.layout_mode
        assert loaded.multi_photo_mode == state.multi_photo_mode
        assert loaded.depth_exaggeration == state.depth_exaggeration
        assert loaded.point_cloud_snapshot == state.point_cloud_snapshot
        assert loaded.cached_features == state.cached_features

    def test_file_is_valid_json(self, tmp_dir):
        """Saved file is human-readable JSON."""
        state = self._make_state()
        path = os.path.join(tmp_dir, "test.apollo7")
        save_project(state, path)

        with open(path, "r") as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert "sim_params" in data

    def test_missing_photo_paths_warns_no_crash(self, tmp_dir, caplog):
        """Missing photo paths in loaded project produce warnings, not crashes."""
        state = self._make_state(
            photo_paths=["/nonexistent/path/photo.jpg", "/also/missing.png"]
        )
        path = os.path.join(tmp_dir, "missing_photos.apollo7")
        save_project(state, path)

        import logging

        with caplog.at_level(logging.WARNING):
            loaded = load_project(path)

        # Should still load successfully
        assert loaded.photo_paths == state.photo_paths
        # Should have logged warnings about missing paths
        assert any("missing" in r.message.lower() or "not found" in r.message.lower()
                    for r in caplog.records)

    def test_version_validation(self, tmp_dir):
        """Invalid version in project file raises an error."""
        path = os.path.join(tmp_dir, "bad_version.apollo7")
        with open(path, "w") as f:
            json.dump({"version": "99.0", "photo_paths": []}, f)

        with pytest.raises((ValueError, KeyError)):
            load_project(path)

    def test_numpy_array_roundtrip(self, tmp_dir):
        """Numpy arrays in point cloud snapshot survive serialization."""
        state = self._make_state()
        # Use numpy-like nested lists (the save function should handle them)
        state.point_cloud_snapshot = {
            "positions": np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]).tolist(),
            "colors": np.array([[1.0, 0.0, 0.0, 1.0]]).tolist(),
        }
        path = os.path.join(tmp_dir, "numpy_test.apollo7")
        save_project(state, path)
        loaded = load_project(path)

        assert loaded.point_cloud_snapshot["positions"] == state.point_cloud_snapshot["positions"]
