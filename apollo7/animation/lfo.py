"""LFO, noise, and envelope generators for parameter animation.

Each generator implements evaluate(time) -> float, producing
time-varying values that can be routed to simulation parameters
via AnimationBinding.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class LFO:
    """Low-frequency oscillator with selectable waveform.

    Produces periodic signals at the given frequency, scaled by
    amplitude and shifted by offset.

    Args:
        frequency: Oscillation rate in Hz.
        amplitude: Peak deviation from offset.
        offset: DC offset added to the waveform.
        waveform: One of 'sine', 'triangle', 'square', 'sawtooth'.
    """

    frequency: float = 1.0
    amplitude: float = 1.0
    offset: float = 0.0
    waveform: str = "sine"

    def evaluate(self, time: float) -> float:
        """Evaluate the LFO at the given time.

        Args:
            time: Current time in seconds.

        Returns:
            Float value in [-amplitude + offset, +amplitude + offset].
        """
        if self.waveform == "sine":
            raw = math.sin(2.0 * math.pi * self.frequency * time)
        elif self.waveform == "triangle":
            # Triangle: linearly ramps between -1 and 1
            phase = (time * self.frequency) % 1.0
            raw = 2.0 * abs(2.0 * phase - 1.0) - 1.0
        elif self.waveform == "square":
            raw = 1.0 if math.sin(2.0 * math.pi * self.frequency * time) >= 0 else -1.0
        elif self.waveform == "sawtooth":
            phase = (time * self.frequency) % 1.0
            raw = 2.0 * phase - 1.0
        else:
            raise ValueError(f"Unknown waveform: {self.waveform}")

        return raw * self.amplitude + self.offset


@dataclass
class NoiseGenerator:
    """Deterministic noise generator with smooth interpolation.

    Produces Perlin-like noise using hash-based random values at integer
    time steps with linear interpolation for smoothness.

    Args:
        frequency: Rate of noise variation (higher = faster change).
        amplitude: Peak output magnitude.
        seed: Random seed for deterministic output.
    """

    frequency: float = 1.0
    amplitude: float = 1.0
    seed: int = 0

    def _hash(self, n: int) -> float:
        """Deterministic hash producing a value in [-1, 1]."""
        # Simple integer hash based on seed
        x = (n * 374761393 + self.seed * 668265263) & 0xFFFFFFFF
        x = ((x ^ (x >> 13)) * 1274126177) & 0xFFFFFFFF
        x = (x ^ (x >> 16)) & 0xFFFFFFFF
        return (x / 2147483648.0) - 1.0  # Map to [-1, 1]

    def evaluate(self, time: float) -> float:
        """Evaluate noise at the given time.

        Uses linear interpolation between hashed integer time steps
        for smooth output.

        Args:
            time: Current time in seconds.

        Returns:
            Float value in [-amplitude, +amplitude].
        """
        t = time * self.frequency
        t0 = int(math.floor(t))
        t1 = t0 + 1
        frac = t - t0

        # Smoothstep for smoother interpolation
        frac = frac * frac * (3.0 - 2.0 * frac)

        v0 = self._hash(t0)
        v1 = self._hash(t1)

        raw = v0 + (v1 - v0) * frac
        return raw * self.amplitude


@dataclass
class Envelope:
    """Attack-sustain-release envelope generator.

    Produces a shape that ramps from 0 to peak during attack,
    holds at peak during sustain, and decays back to 0 during release.

    Args:
        attack: Attack duration in seconds.
        sustain: Sustain duration in seconds.
        release: Release duration in seconds.
        peak: Peak amplitude (reached at end of attack).
    """

    attack: float = 1.0
    sustain: float = 1.0
    release: float = 1.0
    peak: float = 1.0

    def evaluate(self, time: float) -> float:
        """Evaluate the envelope at the given time.

        Args:
            time: Current time in seconds (0 = envelope start).

        Returns:
            Float value in [0, peak].
        """
        if time < 0:
            return 0.0

        if time < self.attack:
            # Attack phase: linear ramp from 0 to peak
            if self.attack == 0:
                return self.peak
            return (time / self.attack) * self.peak

        if time < self.attack + self.sustain:
            # Sustain phase: hold at peak
            return self.peak

        release_start = self.attack + self.sustain
        if time < release_start + self.release:
            # Release phase: linear decay from peak to 0
            if self.release == 0:
                return 0.0
            elapsed = time - release_start
            return self.peak * (1.0 - elapsed / self.release)

        # After release: silent
        return 0.0
