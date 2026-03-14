"""Smoke tests for GPU/rendering provider availability."""


def test_onnxruntime_providers_available():
    """ONNX Runtime loads and reports available providers."""
    import onnxruntime as ort

    providers = ort.get_available_providers()
    assert isinstance(providers, list)
    assert len(providers) > 0, "No execution providers found"


def test_pygfx_importable():
    """pygfx imports without error."""
    import pygfx as gfx  # noqa: F401


def test_wgpu_importable():
    """wgpu imports without error."""
    import wgpu  # noqa: F401
