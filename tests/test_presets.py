"""Tests for preset manager functionality."""

import os

import pytest

from apollo7.project.presets import PresetManager


class TestPresetManager:
    """Test PresetManager save/load/list/delete."""

    @pytest.fixture
    def manager(self, tmp_dir):
        """Create a PresetManager with a temp directory."""
        return PresetManager(presets_dir=tmp_dir)

    def test_save_creates_file(self, manager, tmp_dir):
        """Preset save creates a JSON file in category subfolder."""
        sim_params = {"noise_frequency": 0.5, "speed": 2.0}
        postfx_params = {"bloom_strength": 0.1}

        result_path = manager.save_preset(
            "My Preset", "Organic", sim_params, postfx_params
        )

        assert os.path.exists(result_path)
        assert "Organic" in str(result_path)
        assert result_path.name == "My Preset.json"

    def test_load_returns_params(self, manager):
        """Preset load returns sim_params and postfx_params dict."""
        sim_params = {"noise_frequency": 0.5}
        postfx_params = {"bloom_strength": 0.1}
        manager.save_preset("Test", "Geometric", sim_params, postfx_params)

        loaded = manager.load_preset("Test", "Geometric")

        assert loaded["sim_params"] == sim_params
        assert loaded["postfx_params"] == postfx_params

    def test_list_grouped_by_category(self, manager):
        """Preset list returns presets grouped by category."""
        manager.save_preset("A", "Organic", {"a": 1}, {})
        manager.save_preset("B", "Organic", {"b": 2}, {})
        manager.save_preset("C", "Geometric", {"c": 3}, {})

        listing = manager.list_presets()

        assert "Organic" in listing
        assert "Geometric" in listing
        # User presets plus built-in presets
        assert "A" in listing["Organic"]
        assert "B" in listing["Organic"]
        assert "C" in listing["Geometric"]

    def test_delete_removes_file(self, manager):
        """Preset delete removes the file and returns True."""
        manager.save_preset("ToDelete", "Custom", {"x": 1}, {})
        assert manager.delete_preset("ToDelete", "Custom") is True

        # Should not appear in listing anymore
        listing = manager.list_presets()
        assert "ToDelete" not in listing.get("Custom", [])

    def test_delete_nonexistent_returns_false(self, manager):
        """Deleting a nonexistent preset returns False."""
        assert manager.delete_preset("NoSuch", "NoCategory") is False

    def test_get_categories(self, manager):
        """get_categories returns list of category subdirectory names."""
        manager.save_preset("A", "Organic", {}, {})
        manager.save_preset("B", "Chaotic", {}, {})

        cats = manager.get_categories()
        assert "Organic" in cats
        assert "Chaotic" in cats

    def test_category_auto_creation(self, manager, tmp_dir):
        """Saving a preset in a new category creates the directory."""
        manager.save_preset("New", "BrandNew", {"x": 1}, {})
        assert os.path.isdir(os.path.join(tmp_dir, "BrandNew"))
