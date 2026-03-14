"""QUndoCommand subclasses for parameter changes with slider debouncing.

Provides ParameterChangeCommand (merges consecutive same-parameter changes)
and ResetSectionCommand (batch reset of all params in a section).
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QUndoCommand

# Base merge ID -- each unique parameter gets _BASE + offset
_BASE_MERGE_ID = 1000


class ParameterChangeCommand(QUndoCommand):
    """Undoable command for a single parameter value change.

    Consecutive changes to the same parameter (identified by merge_id_offset)
    automatically merge via mergeWith(), collapsing rapid slider drags into
    a single undo entry.

    Args:
        param_name: Name of the parameter being changed.
        old_value: Value before the change.
        new_value: Value after the change.
        apply_fn: Callback ``(param_name, value) -> None`` that applies the value.
        merge_id_offset: Unique offset per parameter (0 for point_size, 1 for
            opacity, etc.) so only same-parameter commands merge.
    """

    def __init__(
        self,
        param_name: str,
        old_value: float,
        new_value: float,
        apply_fn: Callable[[str, float], None],
        merge_id_offset: int = 0,
    ) -> None:
        super().__init__(f"Change {param_name}")
        self._param_name = param_name
        self._old = old_value
        self._new = new_value
        self._apply_fn = apply_fn
        self._merge_id_offset = merge_id_offset

    def id(self) -> int:
        """Return merge ID. Commands with the same id() can merge."""
        return _BASE_MERGE_ID + self._merge_id_offset

    def redo(self) -> None:
        """Apply the new value."""
        self._apply_fn(self._param_name, self._new)

    def undo(self) -> None:
        """Revert to the old value."""
        self._apply_fn(self._param_name, self._old)

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Merge consecutive same-parameter changes into one entry.

        After merging, this command's new_value becomes other's new_value,
        while old_value stays as the original (pre-drag) value.
        """
        if not isinstance(other, ParameterChangeCommand):
            return False
        if other.id() != self.id():
            return False
        self._new = other._new
        return True


class ResetSectionCommand(QUndoCommand):
    """Undoable command that resets all parameters in a section to defaults.

    Args:
        params: Dict mapping param_name to (old_value, default_value) tuples.
        apply_fn: Callback ``(param_name, value) -> None`` that applies the value.
    """

    def __init__(
        self,
        params: dict[str, tuple[float, float]],
        apply_fn: Callable[[str, float], None],
    ) -> None:
        super().__init__("Reset section")
        self._params = dict(params)  # {name: (old_val, default_val)}
        self._apply_fn = apply_fn

    def id(self) -> int:
        """Return -1 to prevent merging."""
        return -1

    def redo(self) -> None:
        """Apply default values for all parameters."""
        for name, (_, default) in self._params.items():
            self._apply_fn(name, default)

    def undo(self) -> None:
        """Restore old values for all parameters."""
        for name, (old, _) in self._params.items():
            self._apply_fn(name, old)
