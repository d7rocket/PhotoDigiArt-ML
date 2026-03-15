"""Tests for CrossfadeEngine ease-out interpolation.

Covers:
- Ease-out curve behavior (fast start, slow finish)
- QTimer stops when idle (no CPU waste)
- Multiple concurrent transitions
- Retarget mid-transition
- Discrete param passthrough (solver_iterations snaps instantly)
"""

from __future__ import annotations

import pytest


def test_ease_out_interpolation():
    """After set_target(name, target=1.0, current=0.0), calling _tick()
    repeatedly produces values following ease-out curve (fast start, slow
    finish), eventually reaching target."""
    from apollo7.rendering.crossfade import CrossfadeEngine

    applied: dict[str, list[float]] = {}

    def apply_fn(name: str, value: float):
        applied.setdefault(name, []).append(value)

    engine = CrossfadeEngine(apply_fn)
    engine.set_target("home_strength", 1.0, 0.0)

    # Tick enough times to complete the transition
    for _ in range(100):
        engine._tick()

    values = applied["home_strength"]
    assert len(values) > 0, "Should have applied values during transition"

    # Final value should be at or very near target
    assert abs(values[-1] - 1.0) < 0.01, (
        f"Final value should be ~1.0, got {values[-1]}"
    )

    # Ease-out: first step should be larger than last step (fast start, slow finish)
    if len(values) >= 3:
        first_step = values[0] - 0.0  # from start=0.0 to first applied
        # Find a late step (before convergence)
        mid_idx = len(values) // 2
        late_step = values[mid_idx] - values[mid_idx - 1]
        assert first_step > late_step, (
            f"Ease-out should decelerate: first_step={first_step} should be > late_step={late_step}"
        )


def test_timer_stops_when_idle():
    """After all transitions complete, QTimer is stopped (not wasting CPU)."""
    from apollo7.rendering.crossfade import CrossfadeEngine

    def apply_fn(name: str, value: float):
        pass

    engine = CrossfadeEngine(apply_fn)
    engine.set_target("home_strength", 1.0, 0.0)

    # Timer should be active
    assert engine._timer.isActive(), "Timer should be active during transition"

    # Tick until complete
    for _ in range(100):
        engine._tick()

    # Timer should be stopped after all transitions complete
    assert not engine._timer.isActive(), "Timer should stop when no active transitions"


def test_multiple_concurrent():
    """Can have transitions for multiple params running simultaneously, each independent."""
    from apollo7.rendering.crossfade import CrossfadeEngine

    applied: dict[str, list[float]] = {}

    def apply_fn(name: str, value: float):
        applied.setdefault(name, []).append(value)

    engine = CrossfadeEngine(apply_fn)
    engine.set_target("home_strength", 10.0, 0.0)
    engine.set_target("noise_amplitude", 5.0, 2.0)

    # Tick to completion
    for _ in range(100):
        engine._tick()

    assert "home_strength" in applied, "home_strength should have values"
    assert "noise_amplitude" in applied, "noise_amplitude should have values"

    # Both should reach their targets
    assert abs(applied["home_strength"][-1] - 10.0) < 0.1
    assert abs(applied["noise_amplitude"][-1] - 5.0) < 0.1


def test_retarget_mid_transition():
    """Calling set_target again mid-transition smoothly redirects toward new
    target from current position."""
    from apollo7.rendering.crossfade import CrossfadeEngine

    applied: dict[str, list[float]] = {}

    def apply_fn(name: str, value: float):
        applied.setdefault(name, []).append(value)

    engine = CrossfadeEngine(apply_fn)
    engine.set_target("home_strength", 10.0, 0.0)

    # Tick a few times to get partway through
    for _ in range(5):
        engine._tick()

    mid_value = applied["home_strength"][-1]
    assert 0.0 < mid_value < 10.0, "Should be partway through transition"

    # Retarget to a different value
    engine.set_target("home_strength", 3.0, mid_value)

    # Tick to completion
    for _ in range(100):
        engine._tick()

    final = applied["home_strength"][-1]
    assert abs(final - 3.0) < 0.1, (
        f"After retarget, final value should be ~3.0, got {final}"
    )


def test_discrete_passthrough():
    """Discrete params (solver_iterations) are applied immediately without transition."""
    from apollo7.rendering.crossfade import CrossfadeEngine

    applied: dict[str, list[float]] = {}

    def apply_fn(name: str, value: float):
        applied.setdefault(name, []).append(value)

    engine = CrossfadeEngine(apply_fn)
    engine.set_target("solver_iterations", 4.0, 2.0)

    # Should be applied immediately, not via transition
    assert "solver_iterations" in applied, "Discrete param should be applied immediately"
    assert applied["solver_iterations"] == [4.0], (
        f"Discrete param should have single immediate value, got {applied['solver_iterations']}"
    )

    # No active transitions should exist for it
    assert "solver_iterations" not in engine._active, (
        "Discrete param should not create a transition"
    )
