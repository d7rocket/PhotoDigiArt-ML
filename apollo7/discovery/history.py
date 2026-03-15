"""Proposal history with thumbnail snapshots for non-linear navigation.

Stores parameter snapshots as Proposal objects in a ring buffer,
allowing artists to browse and revisit previous discovery proposals.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Proposal:
    """A single discovery proposal snapshot.

    Attributes:
        params: Serialized SimulationParams as dict.
        postfx_params: Serialized postfx state as dict.
        thumbnail: QPixmap snapshot of viewport (None if not captured).
        timestamp: Unix timestamp when proposal was created.
        dimensions: Dimensional slider values that produced this proposal.
    """

    params: dict[str, Any]
    postfx_params: dict[str, Any] = field(default_factory=dict)
    thumbnail: Any = None  # QPixmap | None (Any to avoid Qt import at module level)
    timestamp: float = field(default_factory=time.time)
    dimensions: dict[str, float] = field(default_factory=dict)


class ProposalHistory:
    """Ring buffer of discovery proposals with thumbnail snapshots.

    Args:
        max_size: Maximum number of proposals to keep (oldest evicted first).
    """

    def __init__(self, max_size: int = 50):
        self._proposals: list[Proposal] = []
        self._max_size = max_size
        self._current_index: int = -1

    @property
    def current_index(self) -> int:
        """Index of the currently active proposal (-1 if empty)."""
        return self._current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        """Set the current proposal index."""
        if self._proposals and 0 <= value < len(self._proposals):
            self._current_index = value

    def add(self, proposal: Proposal) -> None:
        """Add a proposal to the history.

        If at max capacity, the oldest proposal is evicted.
        The current_index is set to the newly added proposal.
        """
        if len(self._proposals) >= self._max_size:
            self._proposals.pop(0)
        self._proposals.append(proposal)
        self._current_index = len(self._proposals) - 1

    def get(self, index: int) -> Proposal:
        """Get a proposal by index.

        Args:
            index: Zero-based index into the history.

        Returns:
            The Proposal at the given index.

        Raises:
            IndexError: If index is out of range.
        """
        return self._proposals[index]

    def get_all(self) -> list[Proposal]:
        """Get all proposals in chronological order."""
        return list(self._proposals)

    def clear(self) -> None:
        """Remove all proposals from history."""
        self._proposals.clear()
        self._current_index = -1
