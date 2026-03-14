"""3D viewport widget embedding pygfx in PySide6 via rendercanvas.

Renders point clouds with PointsGaussianBlobMaterial for soft Gaussian
blob particles. Provides orbit/zoom/pan via OrbitController.
"""

import logging

import numpy as np
from PySide6 import QtWidgets
from rendercanvas.qt import QRenderWidget
import pygfx as gfx

from apollo7.config.settings import BG_COLOR_BOTTOM, BG_COLOR_TOP
from apollo7.rendering.camera import CameraController

logger = logging.getLogger(__name__)

# Additive blending validation (RENDER-03):
# pygfx PointsGaussianBlobMaterial does NOT expose a blend_mode parameter
# or property. Neither does gfx.Points or the renderer. The workaround
# is to set per-vertex alpha < 1.0 (e.g. 0.7) combined with the Gaussian
# blob falloff. When points overlap, their colors accumulate through the
# alpha compositing, producing a soft additive-like glow effect.
# This achieves the visual goal for Phase 1. If true additive blending
# is needed later, a custom WGSL shader via register_wgpu_render_function
# would be required.
BLEND_MODE_AVAILABLE: bool = False
"""True if pygfx natively supports additive blend_mode on the material.
False means we use the alpha-falloff workaround for soft overlap."""

# Alpha value for soft overlap workaround
_BLEND_ALPHA: float = 0.7


class ViewportWidget(QtWidgets.QWidget):
    """PySide6 widget containing a pygfx 3D viewport.

    On init, generates 10,000 test points in a sphere to prove the
    viewport integration works immediately.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Embedded render canvas
        self._canvas = QRenderWidget(self, update_mode="continuous")
        layout.addWidget(self._canvas)

        # pygfx core objects
        self._renderer = gfx.WgpuRenderer(self._canvas)
        self._scene = gfx.Scene()
        self._camera = gfx.PerspectiveCamera(60)

        # Dark gradient background
        self._scene.add(gfx.Background.from_color(BG_COLOR_TOP, BG_COLOR_BOTTOM))

        # Camera controller (orbit/zoom/pan)
        self._camera_controller = CameraController(
            self._camera, self._renderer
        )

        # Track point cloud objects for clear_points()
        self._point_objects: list[gfx.Points] = []

        # Log blending approach
        if BLEND_MODE_AVAILABLE:
            logger.info("Blending: additive via blend_mode")
        else:
            logger.info(
                "Blending: soft overlap via alpha falloff workaround "
                f"(alpha={_BLEND_ALPHA})"
            )

        # Generate test data to prove viewport works on launch
        self._add_test_points()

        # Start render loop
        self._canvas.request_draw(self._animate)

    def _animate(self):
        """Called each frame to render the scene."""
        self._renderer.render(self._scene, self._camera)

    def add_points(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        sizes: np.ndarray,
    ) -> gfx.Points:
        """Add a point cloud to the scene.

        Args:
            positions: (N, 3) float32 array of XYZ positions.
            colors: (N, 4) float32 array of RGBA colors.
            sizes: (N,) float32 array of per-point sizes.

        Returns:
            The created gfx.Points object.
        """
        geometry = gfx.Geometry(
            positions=positions.astype(np.float32),
            colors=colors.astype(np.float32),
            sizes=sizes.astype(np.float32),
        )
        material = gfx.PointsGaussianBlobMaterial(
            color_mode="vertex",
            size_mode="vertex",
        )
        points = gfx.Points(geometry, material)
        self._scene.add(points)
        self._point_objects.append(points)
        return points

    def clear_points(self):
        """Remove all point cloud objects from the scene."""
        for pts in self._point_objects:
            self._scene.remove(pts)
        self._point_objects.clear()

    def auto_frame(self):
        """Position camera to show the entire scene."""
        self._camera.show_object(self._scene)

    def _add_test_points(self):
        """Generate 10,000 random points in a sphere for startup test."""
        rng = np.random.default_rng(42)
        n = 10_000

        # Random points on/in a unit sphere using rejection sampling
        raw = rng.standard_normal((n * 2, 3)).astype(np.float32)
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        normalized = raw / norms
        # Scale by random radius for volume fill
        radii = rng.uniform(0.1, 1.0, size=(n * 2, 1)).astype(np.float32)
        sphere_pts = normalized * radii
        # Take first n points
        positions = sphere_pts[:n]

        # Random RGB colors with alpha for soft overlap
        rgb = rng.uniform(0.2, 1.0, size=(n, 3)).astype(np.float32)
        alpha = np.full((n, 1), _BLEND_ALPHA, dtype=np.float32)
        colors = np.concatenate([rgb, alpha], axis=1)

        # Uniform sizes
        sizes = np.full(n, 2.0, dtype=np.float32)

        self.add_points(positions, colors, sizes)
        self.auto_frame()
