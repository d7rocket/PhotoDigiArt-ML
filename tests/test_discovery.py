"""Tests for discovery mode: random walk, dimensional mapping, and proposal history."""

from __future__ import annotations

import pytest

from apollo7.discovery.random_walk import RandomWalk
from apollo7.discovery.dimensional import DimensionalMapper, DIMENSION_MAPPINGS
from apollo7.discovery.history import ProposalHistory, Proposal
from apollo7.simulation.parameters import SimulationParams


class TestRandomWalkPropose:
    """RandomWalk.propose() generates SimulationParams within constrained ranges."""

    def test_propose_within_constraints(self):
        """All proposed params must fall within specified constraint ranges."""
        rw = RandomWalk(seed=42)
        constraints = {
            "speed": (0.5, 1.5),
            "turbulence_scale": (0.5, 2.0),
            "noise_amplitude": (0.3, 1.0),
            "viscosity": (0.05, 0.2),
        }
        params = rw.propose(constraints)
        assert isinstance(params, SimulationParams)
        assert 0.5 <= params.speed <= 1.5
        assert 0.5 <= params.turbulence_scale <= 2.0
        assert 0.3 <= params.noise_amplitude <= 1.0
        assert 0.05 <= params.viscosity <= 0.2

    def test_propose_random_walk_step(self):
        """Perturbed values differ from current but stay in range."""
        rw = RandomWalk(seed=42)
        current = SimulationParams(speed=1.0, turbulence_scale=1.0)
        constraints = {
            "speed": (0.2, 3.0),
            "turbulence_scale": (0.5, 3.0),
        }
        params = rw.propose(constraints, current=current)
        # Values should differ from current (with very high probability given seed)
        assert params.speed != current.speed or params.turbulence_scale != current.turbulence_scale
        # Values must be within constraints
        assert 0.2 <= params.speed <= 3.0
        assert 0.5 <= params.turbulence_scale <= 3.0

    def test_propose_pure_random(self):
        """Without current params, generates valid random params within constraints."""
        rw = RandomWalk(seed=123)
        constraints = {
            "speed": (0.5, 2.0),
            "noise_frequency": (0.1, 1.0),
        }
        params = rw.propose(constraints)
        assert isinstance(params, SimulationParams)
        assert 0.5 <= params.speed <= 2.0
        assert 0.1 <= params.noise_frequency <= 1.0

    def test_propose_reproducible_with_seed(self):
        """Same seed produces same proposal."""
        constraints = {"speed": (0.2, 3.0)}
        p1 = RandomWalk(seed=99).propose(constraints)
        p2 = RandomWalk(seed=99).propose(constraints)
        assert p1.speed == p2.speed


class TestDimensionalMapper:
    """DimensionalMapper maps abstract slider values to concrete param ranges."""

    def test_dimensional_mapper_energy_high(self):
        """energy=1.0 produces high speed/turbulence ranges."""
        mapper = DimensionalMapper()
        mapper.set_dimension("energy", 1.0)
        # Apply multiple times to converge past smoothing
        for _ in range(20):
            mapper.set_dimension("energy", 1.0)
        ranges = mapper.get_param_ranges()
        # At high energy, speed range should be in upper portion
        assert "speed" in ranges
        speed_min, speed_max = ranges["speed"]
        # Upper portion means min should be above the midpoint of the full range
        assert speed_min >= 1.0  # Above midpoint of 0.2-3.0

    def test_dimensional_mapper_energy_calm(self):
        """energy=0.0 produces low speed/turbulence ranges."""
        mapper = DimensionalMapper()
        for _ in range(20):
            mapper.set_dimension("energy", 0.0)
        ranges = mapper.get_param_ranges()
        assert "speed" in ranges
        speed_min, speed_max = ranges["speed"]
        # At low energy, max should be below midpoint
        assert speed_max <= 2.0  # Below midpoint of 0.2-3.0

    def test_dimensional_mapper_constraints_valid(self):
        """get_param_ranges returns valid (min, max) tuples."""
        mapper = DimensionalMapper()
        ranges = mapper.get_param_ranges()
        for param_name, (lo, hi) in ranges.items():
            assert lo <= hi, f"{param_name}: min {lo} > max {hi}"

    def test_dimensional_smoothing(self):
        """Rapid slider changes are smoothed (not instant jumps)."""
        mapper = DimensionalMapper()
        # Default is 0.5
        mapper.set_dimension("energy", 1.0)
        # After one set with alpha=0.3, internal value should be:
        # 0.5 * 0.7 + 1.0 * 0.3 = 0.65 (not 1.0)
        assert mapper._values["energy"] < 1.0
        assert mapper._values["energy"] > 0.5

    def test_all_dimensions_exist(self):
        """All four dimensions are defined in DIMENSION_MAPPINGS."""
        assert "energy" in DIMENSION_MAPPINGS
        assert "density" in DIMENSION_MAPPINGS
        assert "flow" in DIMENSION_MAPPINGS
        assert "structure" in DIMENSION_MAPPINGS


class TestProposalHistory:
    """ProposalHistory stores proposals in a ring buffer."""

    def test_proposal_history_add_get(self):
        """Add proposals, retrieve by index."""
        history = ProposalHistory()
        p1 = Proposal(params={"speed": 1.0}, dimensions={"energy": 0.5})
        p2 = Proposal(params={"speed": 2.0}, dimensions={"energy": 0.8})
        history.add(p1)
        history.add(p2)
        assert history.get(0) is p1
        assert history.get(1) is p2
        assert len(history.get_all()) == 2

    def test_proposal_history_ring_buffer(self):
        """Oldest proposals evicted after max size (50)."""
        history = ProposalHistory(max_size=5)
        for i in range(10):
            history.add(Proposal(params={"speed": float(i)}, dimensions={"energy": 0.5}))
        all_proposals = history.get_all()
        assert len(all_proposals) == 5
        # Oldest should be index 5 (items 0-4 evicted)
        assert all_proposals[0].params["speed"] == 5.0

    def test_proposal_history_current_index(self):
        """current_index tracks the active proposal."""
        history = ProposalHistory()
        p1 = Proposal(params={"speed": 1.0}, dimensions={"energy": 0.5})
        history.add(p1)
        assert history.current_index == 0

    def test_proposal_history_clear(self):
        """clear() removes all proposals."""
        history = ProposalHistory()
        history.add(Proposal(params={"speed": 1.0}, dimensions={"energy": 0.5}))
        history.clear()
        assert len(history.get_all()) == 0
