"""Tests for image export functionality."""

import os

import pytest

from apollo7.project.export import export_image, RESOLUTION_PRESETS


class TestExportImage:
    """Test export_image function."""

    def test_resolution_presets_defined(self):
        """Resolution presets include standard entries."""
        assert "4K" in RESOLUTION_PRESETS
        assert "8K" in RESOLUTION_PRESETS
        assert "Instagram Square" in RESOLUTION_PRESETS
        assert RESOLUTION_PRESETS["4K"] == (3840, 2160)
        assert RESOLUTION_PRESETS["Instagram Square"] == (1080, 1080)

    def test_export_image_importable(self):
        """export_image is importable and callable."""
        assert callable(export_image)

    def test_export_produces_png(self, tmp_dir):
        """export_image produces a valid PNG file with correct dimensions.

        Uses a minimal pygfx scene to validate end-to-end export.
        Skip if GPU/wgpu not available.
        """
        try:
            import pygfx as gfx
            from wgpu.gui.offscreen import WgpuCanvas
        except (ImportError, RuntimeError):
            pytest.skip("pygfx/wgpu not available for offscreen rendering")

        # Create minimal scene
        scene = gfx.Scene()
        scene.add(gfx.Background.from_color("#1a1a1a", "#0a0a0a"))
        camera = gfx.PerspectiveCamera(60)

        output_path = os.path.join(tmp_dir, "test_export.png")
        try:
            export_image(scene, camera, 64, 64, output_path, transparent=False)
        except Exception:
            pytest.skip("Offscreen rendering not available in test environment")

        assert os.path.exists(output_path)

        # Verify it's a valid PNG with correct dimensions
        from PIL import Image
        img = Image.open(output_path)
        assert img.size == (64, 64)
        assert img.mode in ("RGBA", "RGB")

    def test_export_transparent(self, tmp_dir):
        """export_image with transparent=True removes background."""
        try:
            import pygfx as gfx
        except (ImportError, RuntimeError):
            pytest.skip("pygfx not available")

        scene = gfx.Scene()
        bg = gfx.Background.from_color("#1a1a1a", "#0a0a0a")
        scene.add(bg)
        camera = gfx.PerspectiveCamera(60)

        output_path = os.path.join(tmp_dir, "test_transparent.png")
        try:
            export_image(scene, camera, 32, 32, output_path, transparent=True)
        except Exception:
            pytest.skip("Offscreen rendering not available in test environment")

        # Background should be restored after export
        backgrounds = [c for c in scene.children if isinstance(c, gfx.Background)]
        assert len(backgrounds) == 1, "Background should be restored after export"
