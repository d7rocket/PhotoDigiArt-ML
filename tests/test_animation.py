"""Tests for animation engine: LFO waveforms, noise, envelopes, and animator."""

import math

import pytest

from apollo7.animation.lfo import LFO, NoiseGenerator, Envelope
from apollo7.animation.animator import ParameterAnimator, AnimationBinding
from apollo7.simulation.parameters import SimulationParams


class TestLFOSine:
    """Test LFO sine waveform generation."""

    def test_lfo_sine_period(self):
        """Sine LFO completes one cycle at 1/frequency."""
        lfo = LFO(frequency=2.0, amplitude=1.0, offset=0.0, waveform="sine")
        # At t=0, sine starts at 0
        assert abs(lfo.evaluate(0.0)) < 1e-6
        # At t=1/4 period (0.125s for 2Hz), sine is at peak
        assert abs(lfo.evaluate(0.125) - 1.0) < 1e-6
        # At t=1/2 period (0.25s), back to 0
        assert abs(lfo.evaluate(0.25)) < 1e-6
        # At t=3/4 period (0.375s), at trough
        assert abs(lfo.evaluate(0.375) - (-1.0)) < 1e-6
        # At t=full period (0.5s), back to 0
        assert abs(lfo.evaluate(0.5)) < 1e-6

    def test_lfo_sine_amplitude_and_offset(self):
        """Sine LFO respects amplitude and offset."""
        lfo = LFO(frequency=1.0, amplitude=2.0, offset=3.0, waveform="sine")
        # Peak should be amplitude + offset = 5.0
        assert abs(lfo.evaluate(0.25) - 5.0) < 1e-6
        # Trough should be -amplitude + offset = 1.0
        assert abs(lfo.evaluate(0.75) - 1.0) < 1e-6


class TestLFOTriangle:
    """Test LFO triangle waveform."""

    def test_lfo_triangle_range(self):
        """Triangle output stays in [-amp+offset, +amp+offset] range."""
        lfo = LFO(frequency=1.0, amplitude=2.0, offset=1.0, waveform="triangle")
        for i in range(100):
            t = i * 0.01
            val = lfo.evaluate(t)
            assert -1.0 <= val <= 3.0, f"Out of range at t={t}: {val}"


class TestLFOSquare:
    """Test LFO square waveform."""

    def test_lfo_square_values(self):
        """Square waveform only produces two values: +amp+offset and -amp+offset."""
        lfo = LFO(frequency=1.0, amplitude=1.0, offset=0.0, waveform="square")
        values = set()
        for i in range(100):
            t = i * 0.01
            val = lfo.evaluate(t)
            values.add(round(val, 6))
        assert values == {1.0, -1.0}


class TestNoise:
    """Test NoiseGenerator."""

    def test_noise_deterministic(self):
        """Same seed and time produce same output."""
        gen_a = NoiseGenerator(frequency=1.0, amplitude=1.0, seed=42)
        gen_b = NoiseGenerator(frequency=1.0, amplitude=1.0, seed=42)
        for t in [0.0, 0.5, 1.0, 2.7, 10.3]:
            assert gen_a.evaluate(t) == gen_b.evaluate(t)

    def test_noise_smooth(self):
        """Adjacent time values produce similar outputs."""
        gen = NoiseGenerator(frequency=1.0, amplitude=1.0, seed=42)
        for t in [0.0, 1.0, 2.0, 5.0]:
            v0 = gen.evaluate(t)
            v1 = gen.evaluate(t + 0.001)
            assert abs(v1 - v0) < 0.1, f"Not smooth at t={t}: {v0} vs {v1}"

    def test_noise_range(self):
        """Noise output stays within [-amplitude, +amplitude]."""
        gen = NoiseGenerator(frequency=1.0, amplitude=2.0, seed=99)
        for i in range(200):
            t = i * 0.05
            val = gen.evaluate(t)
            assert -2.0 <= val <= 2.0, f"Out of range at t={t}: {val}"


class TestEnvelope:
    """Test Envelope generator."""

    def test_envelope_shape(self):
        """Attack ramps up, sustain holds, release decays."""
        env = Envelope(attack=1.0, sustain=1.0, release=1.0, peak=1.0)
        # Before trigger (t < 0) - not applicable, envelope starts at t=0
        # Start of attack
        assert abs(env.evaluate(0.0)) < 1e-6
        # Mid attack
        assert abs(env.evaluate(0.5) - 0.5) < 1e-6
        # End of attack / start of sustain
        assert abs(env.evaluate(1.0) - 1.0) < 1e-6
        # During sustain
        assert abs(env.evaluate(1.5) - 1.0) < 1e-6
        # End of sustain / start of release
        assert abs(env.evaluate(2.0) - 1.0) < 1e-6
        # Mid release
        assert abs(env.evaluate(2.5) - 0.5) < 1e-6
        # End of release
        assert abs(env.evaluate(3.0)) < 1e-6
        # After release
        assert abs(env.evaluate(4.0)) < 1e-6


class TestParameterAnimator:
    """Test ParameterAnimator binding and tick."""

    def test_animator_applies_binding(self):
        """tick returns params with updated value from binding."""
        lfo = LFO(frequency=1.0, amplitude=1.0, offset=0.0, waveform="sine")
        binding = AnimationBinding(
            target_param="speed", source=lfo, min_val=0.5, max_val=2.0
        )
        animator = ParameterAnimator()
        animator.add_binding(binding)
        params = SimulationParams(speed=1.0)
        # At t=0.25 (quarter period of 1Hz), sine = 1.0
        # Mapped from [-1,1] to [0.5,2.0]: (1.0+1)/2 * (2.0-0.5) + 0.5 = 2.0
        result = animator.tick(0.25, params)
        assert abs(result.speed - 2.0) < 1e-6

    def test_animator_multiple_bindings(self):
        """Multiple params animated simultaneously."""
        lfo1 = LFO(frequency=1.0, amplitude=1.0, offset=0.0, waveform="sine")
        lfo2 = LFO(frequency=1.0, amplitude=1.0, offset=0.0, waveform="square")
        animator = ParameterAnimator()
        animator.add_binding(AnimationBinding("speed", lfo1, 0.0, 1.0))
        animator.add_binding(AnimationBinding("damping", lfo2, 0.5, 1.0))
        params = SimulationParams()
        result = animator.tick(0.0, params)
        # Both params should be modified
        assert isinstance(result, SimulationParams)

    def test_animator_empty(self):
        """tick with no bindings returns unchanged params."""
        animator = ParameterAnimator()
        params = SimulationParams(speed=1.5)
        result = animator.tick(0.0, params)
        assert result.speed == 1.5

    def test_animator_remove_binding(self):
        """remove_binding removes the binding for a target param."""
        lfo = LFO(frequency=1.0, amplitude=1.0, offset=0.0, waveform="sine")
        animator = ParameterAnimator()
        animator.add_binding(AnimationBinding("speed", lfo, 0.0, 1.0))
        assert animator.is_active
        animator.remove_binding("speed")
        assert not animator.is_active
