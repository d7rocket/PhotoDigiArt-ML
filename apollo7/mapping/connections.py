"""Connection data model for feature-to-parameter mapping.

MappingConnection represents a single wire from a feature output to a
parameter input. MappingGraph stores the full set of connections.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MappingConnection:
    """A single mapping wire from feature source to parameter target.

    Attributes:
        source_feature: Extractor name (e.g. 'semantic', 'color', 'depth', 'edge').
        source_key: Dot-path into ExtractionResult.data (e.g. 'mood_tags.serene').
        target_param: SimulationParams field name (e.g. 'speed', 'turbulence_scale').
        strength: Scale factor applied to the normalized feature value.
            Can be negative for inverse mapping.
    """

    source_feature: str
    source_key: str
    target_param: str
    strength: float = 1.0

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "source_feature": self.source_feature,
            "source_key": self.source_key,
            "target_param": self.target_param,
            "strength": self.strength,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MappingConnection:
        """Deserialize from a dict."""
        return cls(
            source_feature=d["source_feature"],
            source_key=d["source_key"],
            target_param=d["target_param"],
            strength=d.get("strength", 1.0),
        )


class MappingGraph:
    """Collection of mapping connections with query and persistence.

    Stores a list of MappingConnection instances and provides methods
    for adding, removing, querying, and serializing them.
    """

    def __init__(self) -> None:
        self._connections: list[MappingConnection] = []

    def add_connection(self, conn: MappingConnection) -> None:
        """Add a connection to the graph."""
        self._connections.append(conn)

    def remove_connection(
        self, source_feature: str, source_key: str, target_param: str
    ) -> None:
        """Remove a connection matching the given source and target."""
        self._connections = [
            c
            for c in self._connections
            if not (
                c.source_feature == source_feature
                and c.source_key == source_key
                and c.target_param == target_param
            )
        ]

    def get_connections(self) -> list[MappingConnection]:
        """Return all connections."""
        return list(self._connections)

    def get_connections_for_target(
        self, target_param: str
    ) -> list[MappingConnection]:
        """Return connections targeting a specific parameter."""
        return [c for c in self._connections if c.target_param == target_param]

    def clear(self) -> None:
        """Remove all connections."""
        self._connections.clear()

    def to_dict(self) -> dict:
        """Serialize the graph to a JSON-compatible dict."""
        return {
            "connections": [c.to_dict() for c in self._connections],
        }

    @classmethod
    def from_dict(cls, d: dict) -> MappingGraph:
        """Deserialize a graph from a dict."""
        graph = cls()
        for cd in d.get("connections", []):
            graph.add_connection(MappingConnection.from_dict(cd))
        return graph
