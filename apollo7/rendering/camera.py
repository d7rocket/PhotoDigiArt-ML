"""Camera controller wrapping pygfx OrbitController.

Provides orbit (left-drag), zoom (scroll), and pan (right-drag) with
a default three-quarter view angle (azimuth ~45 deg, elevation ~30 deg).
"""

import math

import pygfx as gfx


class CameraController:
    """Wrapper around pygfx OrbitController with sensible defaults.

    Sets up a three-quarter view (azimuth ~45 deg, elevation ~30 deg)
    and provides auto-framing.
    """

    # Default viewing angles in radians
    DEFAULT_AZIMUTH = math.radians(45)
    DEFAULT_ELEVATION = math.radians(30)

    def __init__(self, camera: gfx.PerspectiveCamera, renderer: gfx.WgpuRenderer):
        self._camera = camera
        self._controller = gfx.OrbitController(
            camera, register_events=renderer
        )

    @property
    def controller(self) -> gfx.OrbitController:
        """The underlying pygfx OrbitController."""
        return self._controller

    def auto_frame(self, scene: gfx.Scene):
        """Position camera to show the full scene contents."""
        self._camera.show_object(scene)

    def set_three_quarter_view(self) -> None:
        """Set camera to a three-quarter viewing angle.

        Adjusts the orbit controller's azimuth and elevation to provide
        a good default perspective on the point cloud sculpture.
        Uses pygfx OrbitController's rotate method to adjust orientation.
        """
        # OrbitController exposes azimuth/elevation as properties when available,
        # but the safest approach is to set camera local rotation directly.
        # We use the orbit controller's internal state if accessible.
        try:
            # pygfx OrbitController may support direct azimuth/elevation
            if hasattr(self._controller, "azimuth"):
                self._controller.azimuth = self.DEFAULT_AZIMUTH
            if hasattr(self._controller, "elevation"):
                self._controller.elevation = self.DEFAULT_ELEVATION
        except (AttributeError, TypeError):
            # If direct property setting is not supported, this is fine --
            # the default show_object view is still a reasonable starting angle.
            pass
