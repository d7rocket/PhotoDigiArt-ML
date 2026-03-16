"""Shared collapsible section widget for Apollo 7 panel layout.

Extracted from preset_panel._Section and made public with collapse/expand
toggle support.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
_ACCENT = "#0078FF"
_BG_SECTION = "#242424"
_BORDER = "#3a3a3a"

_ARROW_EXPANDED = "\u25BC"   # Down-pointing triangle
_ARROW_COLLAPSED = "\u25B6"  # Right-pointing triangle


class Section(QtWidgets.QWidget):
    """A collapsible section with a styled header and content area.

    Parameters
    ----------
    title : str
        Section header text.
    collapsed : bool
        If True, the content area starts hidden.
    parent : QWidget | None
        Parent widget.
    """

    def __init__(
        self,
        title: str,
        collapsed: bool = False,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._collapsed = collapsed

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header label (clickable)
        arrow = _ARROW_COLLAPSED if collapsed else _ARROW_EXPANDED
        self._header = QtWidgets.QLabel(f"  {arrow}  {title}")
        self._header.setCursor(QtCore.Qt.PointingHandCursor)
        self._header.setStyleSheet(f"""
            QLabel {{
                background: {_BG_SECTION};
                color: {_ACCENT};
                border: 1px solid {_BORDER};
                border-radius: 4px;
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
                padding: 6px 8px;
                font-weight: 600;
                font-size: 12px;
            }}
        """)
        self._header.mousePressEvent = self._on_header_clicked
        layout.addWidget(self._header)

        # Content container
        self._content = QtWidgets.QWidget()
        self._content.setStyleSheet(f"""
            QWidget {{
                background: {_BG_SECTION};
                border: 1px solid {_BORDER};
                border-top: none;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
        """)
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(10, 8, 10, 8)
        self._content_layout.setSpacing(6)
        layout.addWidget(self._content)

        # Apply initial collapsed state
        self._content.setVisible(not collapsed)

    @property
    def content_layout(self) -> QtWidgets.QVBoxLayout:
        """Layout for adding content widgets."""
        return self._content_layout

    @property
    def collapsed(self) -> bool:
        """Whether the section is currently collapsed."""
        return self._collapsed

    @collapsed.setter
    def collapsed(self, value: bool) -> None:
        if value != self._collapsed:
            self.toggle()

    def toggle(self) -> None:
        """Toggle the collapsed state of the section."""
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        arrow = _ARROW_COLLAPSED if self._collapsed else _ARROW_EXPANDED
        self._header.setText(f"  {arrow}  {self._title}")

    def _on_header_clicked(self, event) -> None:
        """Handle header click to toggle collapse."""
        self.toggle()
