"""Camera controller wrapping pygfx OrbitController.

Provides orbit (left-drag), zoom (scroll), and pan (right-drag) with
a default three-quarter view angle.
"""

import pygfx as gfx


class CameraController:
    """Wrapper around pygfx OrbitController with sensible defaults.

    Sets up a three-quarter view (azimuth ~45 deg, elevation ~30 deg)
    and provides auto-framing.
    """

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
