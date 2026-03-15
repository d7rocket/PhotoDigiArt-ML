"""Connection data model for feature-to-parameter mapping.

MappingConnection represents a single wire from a feature output to a
parameter input. MappingGraph stores the full set of connections.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MappingConnection:
    """A single mapping wire from feature source to parameter target."""

    source_feature: str
    source_key: str
    target_param: str
    strength: float = 1.0

    def to_dict(self) -> dict:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, d: dict) -> MappingConnection:
        raise NotImplementedError


class MappingGraph:
    """Collection of mapping connections with query and persistence."""

    def __init__(self) -> None:
        self._connections: list[MappingConnection] = []

    def add_connection(self, conn: MappingConnection) -> None:
        raise NotImplementedError

    def remove_connection(self, source_feature: str, source_key: str, target_param: str) -> None:
        raise NotImplementedError

    def get_connections(self) -> list[MappingConnection]:
        raise NotImplementedError

    def get_connections_for_target(self, target_param: str) -> list[MappingConnection]:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, d: dict) -> MappingGraph:
        raise NotImplementedError
