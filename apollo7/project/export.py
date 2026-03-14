"""High-resolution offscreen PNG export.

Renders the current scene at arbitrary resolution using wgpu's
offscreen canvas and saves the result as a PNG with optional
transparent background.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Resolution presets: name -> (width, height)
RESOLUTION_PRESETS: dict[str, tuple[int, int]] = {
    "4K": (3840, 2160),
    "8K": (7680, 4320),
    "Instagram Square": (1080, 1080),
}

# Warning threshold
_HIGH_RES_THRESHOLD = 7680  # 8K


def export_image(
    scene: Any,
    camera: Any,
    width: int,
    height: int,
    output_path: str,
    transparent: bool = False,
) -> None:
    """Render scene at specified resolution and save as PNG.

    Creates an offscreen wgpu canvas, renders the scene to it,
    and saves the resulting frame as a PNG image using Pillow.

    Args:
        scene: pygfx Scene containing the point clouds and background.
        camera: pygfx PerspectiveCamera with current viewpoint.
        width: Output image width in pixels.
        height: Output image height in pixels.
        output_path: File path for the PNG output.
        transparent: If True, remove background and preserve alpha channel.

    Raises:
        ImportError: If required dependencies are not available.
        RuntimeError: If rendering fails.
    """
    import pygfx as gfx
    from PIL import Image
    from wgpu.gui.offscreen import WgpuCanvas

    # Warn about very high resolutions
    if width > _HIGH_RES_THRESHOLD or height > _HIGH_RES_THRESHOLD:
        warnings.warn(
            f"Exporting at {width}x{height} may require significant GPU memory. "
            "Consider reducing resolution if you experience issues.",
            ResourceWarning,
            stacklevel=2,
        )

    # Handle transparent background
    bg_object = None
    if transparent:
        # Find and temporarily remove the Background object
        for child in list(scene.children):
            if isinstance(child, gfx.Background):
                bg_object = child
                scene.remove(child)
                break

    try:
        # Create offscreen canvas and renderer
        canvas = WgpuCanvas(size=(width, height), pixel_ratio=1)
        renderer = gfx.WgpuRenderer(canvas)

        # Render the scene
        canvas.request_draw(lambda: renderer.render(scene, camera))
        frame = np.asarray(canvas.draw())

        # Ensure RGBA format
        if frame.ndim == 3 and frame.shape[2] == 3:
            alpha = np.full((*frame.shape[:2], 1), 255, dtype=np.uint8)
            frame = np.concatenate([frame, alpha], axis=2)

        # Save as PNG
        img = Image.fromarray(frame, "RGBA")
        img.save(output_path, "PNG")
        logger.info("Exported %dx%d image to %s", width, height, output_path)

    finally:
        # Restore background if it was removed
        if bg_object is not None:
            scene.add(bg_object)
