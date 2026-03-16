"""Claude AI suggestion panel with state machine.

Provides an interactive panel for Claude-driven creative direction:
- Analyze photos to get AI-suggested sculpture parameters
- Display suggestion cards with rationale and parameter chips
- Apply suggestions via CrossfadeEngine for smooth transitions
- Iterate with direction buttons (More Fluid, More Structured, etc.)

State machine: IDLE -> LOADING -> SUGGESTION -> APPLIED -> (LOADING for refinement)
Error handling: ERROR state with retry capability.
"""

from __future__ import annotations

import logging
from enum import Enum, auto

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Signal

from apollo7.api.enrichment import EnrichmentService, EnrichmentWorker
from apollo7.api.models import SculptureParams
from apollo7.gui.theme import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_PRESSED,
    BG_PANEL,
    BG_WIDGET,
    BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

logger = logging.getLogger(__name__)


class ClaudeState(Enum):
    """States for the Claude suggestion panel."""

    IDLE = auto()
    LOADING = auto()
    SUGGESTION = auto()
    APPLIED = auto()
    ERROR = auto()


# Friendly display names for SculptureParams fields
_CHIP_LABELS: dict[str, str] = {
    "solver_iterations": "Cohesion",
    "home_strength": "Home",
    "noise_amplitude": "Flow",
    "breathing_rate": "Breathing",
    "point_size": "Size",
    "opacity": "Opacity",
}


class ClaudePanel(QtWidgets.QWidget):
    """Claude AI suggestion panel with state machine and suggestion card UI.

    Signals:
        apply_requested: Emitted with param dict when user clicks Apply.
    """

    apply_requested = Signal(dict)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self._state = ClaudeState.IDLE
        self._current_suggestion: SculptureParams | None = None
        self._current_image_path: str | None = None
        self._enrichment_service: EnrichmentService | None = None
        self._last_mode: str = "suggest_params"
        self._last_direction: str | None = None

        self._build_ui()
        self.set_state(ClaudeState.IDLE)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build all UI elements for every state."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # --- IDLE state elements ---
        self._lbl_empty = QtWidgets.QLabel(
            "Analyze your photo to get AI-suggested sculpture parameters"
        )
        self._lbl_empty.setWordWrap(True)
        self._lbl_empty.setAlignment(QtCore.Qt.AlignCenter)
        self._lbl_empty.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; padding: 8px;"
        )
        layout.addWidget(self._lbl_empty)

        self._btn_analyze = QtWidgets.QPushButton("Analyze with Claude")
        self._btn_analyze.setObjectName("btn-analyze")
        self._btn_analyze.setStyleSheet(f"""
            QPushButton#btn-analyze {{
                background-color: {ACCENT};
                color: #ffffff;
                font-weight: 600;
                font-size: 15px;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton#btn-analyze:hover {{
                background-color: {ACCENT_HOVER};
            }}
            QPushButton#btn-analyze:pressed {{
                background-color: {ACCENT_PRESSED};
            }}
        """)
        self._btn_analyze.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self._btn_analyze)

        # --- LOADING state elements ---
        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: {BG_WIDGET};
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self._progress)

        self._lbl_loading = QtWidgets.QLabel("Analyzing your photo...")
        self._lbl_loading.setAlignment(QtCore.Qt.AlignCenter)
        self._lbl_loading.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px;"
        )
        layout.addWidget(self._lbl_loading)

        # --- SUGGESTION state elements (card) ---
        self._card = QtWidgets.QWidget()
        self._card.setStyleSheet(f"""
            QWidget#suggestion-card {{
                background-color: {BG_PANEL};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
        """)
        self._card.setObjectName("suggestion-card")
        card_layout = QtWidgets.QVBoxLayout(self._card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        self._lbl_rationale = QtWidgets.QLabel()
        self._lbl_rationale.setWordWrap(True)
        self._lbl_rationale.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 16px; line-height: 1.5;"
        )
        card_layout.addWidget(self._lbl_rationale)

        # Chips container
        self._chips_container = QtWidgets.QWidget()
        self._chips_layout = _FlowLayout(self._chips_container, margin=0, spacing=6)
        card_layout.addWidget(self._chips_container)

        self._btn_apply = QtWidgets.QPushButton("Apply to Sculpture")
        self._btn_apply.setObjectName("btn-apply-suggestion")
        self._btn_apply.setStyleSheet(f"""
            QPushButton#btn-apply-suggestion {{
                background-color: {ACCENT};
                color: #ffffff;
                font-weight: 600;
                font-size: 15px;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton#btn-apply-suggestion:hover {{
                background-color: {ACCENT_HOVER};
            }}
            QPushButton#btn-apply-suggestion:pressed {{
                background-color: {ACCENT_PRESSED};
            }}
        """)
        self._btn_apply.clicked.connect(self._on_apply_clicked)
        card_layout.addWidget(self._btn_apply)

        layout.addWidget(self._card)

        # --- APPLIED state elements (direction buttons) ---
        self._direction_container = QtWidgets.QWidget()
        dir_layout = QtWidgets.QVBoxLayout(self._direction_container)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(8)

        dir_grid = QtWidgets.QGridLayout()
        dir_grid.setSpacing(8)

        dir_btn_style = f"""
            QPushButton {{
                background-color: {BG_WIDGET};
                border: 1px solid {BORDER};
                border-radius: 4px;
                font-size: 13px;
                color: {TEXT_PRIMARY};
                padding: 8px;
            }}
            QPushButton:hover {{
                border-color: {ACCENT};
            }}
        """

        self._btn_more_fluid = QtWidgets.QPushButton("More Fluid")
        self._btn_more_fluid.setStyleSheet(dir_btn_style)
        self._btn_more_fluid.clicked.connect(
            lambda: self._on_direction_clicked("more fluid")
        )
        dir_grid.addWidget(self._btn_more_fluid, 0, 0)

        self._btn_more_structured = QtWidgets.QPushButton("More Structured")
        self._btn_more_structured.setStyleSheet(dir_btn_style)
        self._btn_more_structured.clicked.connect(
            lambda: self._on_direction_clicked("more structured")
        )
        dir_grid.addWidget(self._btn_more_structured, 0, 1)

        self._btn_more_vibrant = QtWidgets.QPushButton("More Vibrant")
        self._btn_more_vibrant.setStyleSheet(dir_btn_style)
        self._btn_more_vibrant.clicked.connect(
            lambda: self._on_direction_clicked("more vibrant")
        )
        dir_grid.addWidget(self._btn_more_vibrant, 1, 0)

        self._btn_more_subtle = QtWidgets.QPushButton("More Subtle")
        self._btn_more_subtle.setStyleSheet(dir_btn_style)
        self._btn_more_subtle.clicked.connect(
            lambda: self._on_direction_clicked("more subtle")
        )
        dir_grid.addWidget(self._btn_more_subtle, 1, 1)

        dir_layout.addLayout(dir_grid)

        # Footer row: Start Over / Keep This
        footer = QtWidgets.QHBoxLayout()
        footer.setSpacing(8)

        self._btn_start_over = QtWidgets.QPushButton("Start Over")
        self._btn_start_over.setStyleSheet(
            f"background: transparent; color: {TEXT_SECONDARY}; border: none; "
            f"font-size: 13px; padding: 4px 8px;"
        )
        self._btn_start_over.clicked.connect(self._on_start_over_clicked)
        footer.addWidget(self._btn_start_over)

        footer.addStretch()

        self._btn_keep = QtWidgets.QPushButton("Keep This")
        self._btn_keep.setStyleSheet(
            f"background: transparent; color: {TEXT_SECONDARY}; border: none; "
            f"font-size: 13px; padding: 4px 8px;"
        )
        self._btn_keep.clicked.connect(self._on_keep_clicked)
        footer.addWidget(self._btn_keep)

        dir_layout.addLayout(footer)
        layout.addWidget(self._direction_container)

        # --- ERROR state elements ---
        self._lbl_error = QtWidgets.QLabel()
        self._lbl_error.setWordWrap(True)
        self._lbl_error.setStyleSheet(
            "color: #E53935; font-size: 13px; padding: 8px;"
        )
        layout.addWidget(self._lbl_error)

        self._btn_retry = QtWidgets.QPushButton("Try Again")
        self._btn_retry.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_WIDGET};
                border: 1px solid {BORDER};
                border-radius: 4px;
                font-size: 13px;
                color: {TEXT_PRIMARY};
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                border-color: {ACCENT};
            }}
        """)
        self._btn_retry.clicked.connect(self._on_retry_clicked)
        layout.addWidget(self._btn_retry)

        layout.addStretch(1)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def set_state(self, state: ClaudeState) -> None:
        """Transition to a new state, showing/hiding appropriate elements."""
        self._state = state

        # Hide everything
        self._lbl_empty.setVisible(False)
        self._btn_analyze.setVisible(False)
        self._progress.setVisible(False)
        self._lbl_loading.setVisible(False)
        self._card.setVisible(False)
        self._direction_container.setVisible(False)
        self._lbl_error.setVisible(False)
        self._btn_retry.setVisible(False)

        # Show elements for current state
        if state == ClaudeState.IDLE:
            self._lbl_empty.setVisible(True)
            self._btn_analyze.setVisible(True)
        elif state == ClaudeState.LOADING:
            self._progress.setVisible(True)
            self._lbl_loading.setVisible(True)
        elif state == ClaudeState.SUGGESTION:
            self._card.setVisible(True)
            # Hide apply button only if already applied
            self._btn_apply.setVisible(True)
        elif state == ClaudeState.APPLIED:
            self._card.setVisible(True)
            self._btn_apply.setVisible(False)
            self._direction_container.setVisible(True)
        elif state == ClaudeState.ERROR:
            self._lbl_error.setVisible(True)
            self._btn_retry.setVisible(True)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def set_enrichment_service(self, service: EnrichmentService) -> None:
        """Set the enrichment service for API calls."""
        self._enrichment_service = service

    def set_image_path(self, path: str) -> None:
        """Set the current image path for analysis."""
        self._current_image_path = path

    def update_empty_state(self, has_photo: bool, has_api_key: bool) -> None:
        """Update the idle state text based on current context."""
        if not has_photo:
            self._lbl_empty.setText(
                "Load a photo first to analyze with Claude"
            )
            self._btn_analyze.setEnabled(False)
        elif not has_api_key:
            self._lbl_empty.setText(
                "API key required. Go to Settings to add your Anthropic key."
            )
            self._btn_analyze.setEnabled(False)
        else:
            self._lbl_empty.setText(
                "Analyze your photo to get AI-suggested sculpture parameters"
            )
            self._btn_analyze.setEnabled(True)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_analyze_clicked(self) -> None:
        """Start analysis when Analyze button is clicked."""
        if not self._current_image_path or not self._enrichment_service:
            return

        self._last_mode = "suggest_params"
        self.set_state(ClaudeState.LOADING)
        self._start_worker(mode="suggest_params")

    def _on_suggestion_received(self, params: object) -> None:
        """Handle successful suggestion from background worker."""
        if params is None:
            self._on_error(
                "Claude returned an unexpected response. Try again or start over."
            )
            return

        if not isinstance(params, SculptureParams):
            self._on_error(
                "Claude returned an unexpected response. Try again or start over."
            )
            return

        self._current_suggestion = params
        self._populate_card(params)
        self.set_state(ClaudeState.SUGGESTION)

    def _on_apply_clicked(self) -> None:
        """Apply the current suggestion to the sculpture."""
        if self._current_suggestion is None:
            return

        param_dict = self._current_suggestion.to_param_dict()
        self.apply_requested.emit(param_dict)
        self.set_state(ClaudeState.APPLIED)

    def _on_direction_clicked(self, direction: str) -> None:
        """Request a refinement in the given direction."""
        if not self._current_image_path or not self._enrichment_service:
            return
        if self._current_suggestion is None:
            return

        self._last_mode = "refine_params"
        self._last_direction = direction
        self.set_state(ClaudeState.LOADING)
        self._start_worker(
            mode="refine_params",
            current_params=self._current_suggestion.to_param_dict(),
            direction=direction,
        )

    def _on_keep_clicked(self) -> None:
        """Accept current parameters and return to idle."""
        self._current_suggestion = None
        self.set_state(ClaudeState.IDLE)

    def _on_start_over_clicked(self) -> None:
        """Clear suggestion and return to idle."""
        self._current_suggestion = None
        self.set_state(ClaudeState.IDLE)

    def _on_error(self, msg: str) -> None:
        """Show error state with message."""
        self._lbl_error.setText(msg)
        self.set_state(ClaudeState.ERROR)

    def _on_retry_clicked(self) -> None:
        """Retry the last request."""
        self.set_state(ClaudeState.LOADING)
        if self._last_mode == "refine_params" and self._current_suggestion:
            self._start_worker(
                mode="refine_params",
                current_params=self._current_suggestion.to_param_dict(),
                direction=self._last_direction or "",
            )
        else:
            self._start_worker(mode="suggest_params")

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    def _start_worker(
        self,
        mode: str = "suggest_params",
        current_params: dict | None = None,
        direction: str | None = None,
    ) -> None:
        """Create and start an EnrichmentWorker in the thread pool."""
        if not self._enrichment_service or not self._current_image_path:
            self._on_error(
                "Could not reach Claude. Check your API key and internet connection, then try again."
            )
            return

        worker = EnrichmentWorker(
            service=self._enrichment_service,
            image_path=self._current_image_path,
            mode=mode,
            current_params=current_params,
            direction=direction,
        )
        worker.signals.params_suggested.connect(self._on_suggestion_received)
        worker.signals.error.connect(self._on_worker_error)
        QtCore.QThreadPool.globalInstance().start(worker)

    def _on_worker_error(self, msg: str) -> None:
        """Handle worker error."""
        logger.warning("Claude API error: %s", msg)
        self._on_error(
            "Could not reach Claude. Check your API key and internet connection, then try again."
        )

    # ------------------------------------------------------------------
    # Card population
    # ------------------------------------------------------------------

    def _populate_card(self, params: SculptureParams) -> None:
        """Populate the suggestion card with rationale and parameter chips."""
        self._lbl_rationale.setText(params.rationale)

        # Clear existing chips
        while self._chips_layout.count():
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create chips for each parameter
        param_dict = params.to_param_dict()
        for key, value in param_dict.items():
            label = _CHIP_LABELS.get(key, key)
            # Format value: int for solver_iterations, 1 decimal for floats
            if key == "solver_iterations":
                display_value = str(int(value))
            else:
                display_value = f"{value:.1f}"
            chip = self._create_chip(label, display_value)
            self._chips_layout.addWidget(chip)

    def _create_chip(self, label: str, value: str) -> QtWidgets.QLabel:
        """Create a parameter chip label."""
        chip = QtWidgets.QLabel(f"{label}: {value}")
        chip.setStyleSheet(f"""
            background: {BG_WIDGET}; border: 1px solid {BORDER};
            border-radius: 12px; padding: 4px 8px;
            font-size: 11px; color: {TEXT_PRIMARY};
        """)
        return chip


class _FlowLayout(QtWidgets.QLayout):
    """Simple flow layout that wraps widgets horizontally.

    Widgets are placed left-to-right, wrapping to the next line when
    the available width is exceeded. Used for parameter chips.
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        margin: int = 0,
        spacing: int = 6,
    ) -> None:
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items: list[QtWidgets.QLayoutItem] = []

    def addItem(self, item: QtWidgets.QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QtWidgets.QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QtWidgets.QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> QtCore.Qt.Orientation:  # noqa: N802
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QtCore.QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QtCore.QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QtCore.QSize:  # noqa: N802
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QtCore.QRect, test_only: bool) -> int:
        """Lay out items in flowing rows."""
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        row_height = 0

        for item in self._items:
            item_size = item.sizeHint()
            next_x = x + item_size.width() + self._spacing

            if next_x - self._spacing > effective.right() and row_height > 0:
                x = effective.x()
                y += row_height + self._spacing
                next_x = x + item_size.width() + self._spacing
                row_height = 0

            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item_size))

            x = next_x
            row_height = max(row_height, item_size.height())

        return y + row_height - rect.y() + m.bottom()
