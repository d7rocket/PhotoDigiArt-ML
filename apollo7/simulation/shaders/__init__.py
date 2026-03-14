"""WGSL shader loading and concatenation utilities.

Provides functions to load individual .wgsl shader files from the package
directory and combine them into composite shader modules for compute
pipeline creation.
"""

from __future__ import annotations

from pathlib import Path

_SHADER_DIR = Path(__file__).parent


def load_shader(name: str) -> str:
    """Load a WGSL shader file by name (without extension).

    Args:
        name: Shader name, e.g. "noise", "flow_field", "sph".

    Returns:
        The WGSL source code as a string.

    Raises:
        FileNotFoundError: If the shader file does not exist.
    """
    path = _SHADER_DIR / f"{name}.wgsl"
    if not path.exists():
        raise FileNotFoundError(f"Shader not found: {path}")
    return path.read_text(encoding="utf-8")


def build_combined_shader(*names: str) -> str:
    """Concatenate multiple WGSL shader files into a single module.

    Shaders are concatenated in the order given. Typically "noise"
    should come first since other shaders depend on its functions.

    Duplicate struct/binding definitions are handled by the caller
    ensuring only compatible shaders are combined (e.g., noise +
    flow_field, but NOT integrate + flow_field since both define
    entry points with conflicting bindings).

    Args:
        *names: Shader names to concatenate (without .wgsl extension).

    Returns:
        Combined WGSL source code.

    Raises:
        FileNotFoundError: If any shader file does not exist.
    """
    parts = []
    for name in names:
        source = load_shader(name)
        parts.append(f"// === {name}.wgsl ===\n")
        parts.append(source)
        parts.append("\n\n")
    return "".join(parts)
