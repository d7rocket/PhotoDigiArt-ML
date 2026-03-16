"""Apollo 7 dark theme -- qt-material base with custom QSS overrides.

Uses qt-material dark_blue.xml as the foundation, then layers Apollo 7's
electric blue (#0078FF) accent color and custom widget styles on top.
"""

from __future__ import annotations

from PySide6 import QtWidgets

# ---------------------------------------------------------------------------
# Color constants (exported for use by other modules)
# ---------------------------------------------------------------------------
ACCENT = "#0078FF"
ACCENT_HOVER = "#339BFF"
ACCENT_PRESSED = "#005FCC"
BG_DARK = "#1a1a1a"
BG_PANEL = "#242424"
BG_WIDGET = "#2d2d2d"
BG_INPUT = "#1e1e1e"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#808080"
TEXT_DISABLED = "#555555"
BORDER = "#3a3a3a"


def setup_theme(app: QtWidgets.QApplication) -> None:
    """Apply qt-material dark theme with Apollo 7 custom overrides."""
    from qt_material import apply_stylesheet

    # Apply base dark Material theme
    apply_stylesheet(app, theme="dark_blue.xml")

    # Read current stylesheet set by qt-material
    existing = app.styleSheet()

    # Custom QSS overrides preserving all existing objectName selectors
    custom_qss = f"""
    /* === Splitter Handles === */
    QSplitter::handle {{
        background-color: {BORDER};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}
    QSplitter::handle:hover {{
        background-color: {ACCENT};
    }}

    /* === Slider === */
    QSlider::groove:horizontal {{
        background-color: {BG_WIDGET};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background-color: {ACCENT};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background-color: {ACCENT_HOVER};
    }}
    QSlider::sub-page:horizontal {{
        background-color: {ACCENT};
        border-radius: 2px;
    }}

    /* === Simulation Panel === */
    QPushButton#btn-simulate {{
        background-color: {ACCENT};
        color: #ffffff;
        font-weight: 600;
        font-size: 15px;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
    }}
    QPushButton#btn-simulate:hover {{
        background-color: {ACCENT_HOVER};
    }}
    QPushButton#btn-simulate:pressed {{
        background-color: {ACCENT_PRESSED};
    }}
    QPushButton#btn-simulate:disabled {{
        background-color: {BG_PANEL};
        color: {TEXT_DISABLED};
    }}

    /* === FPS Counter === */
    QLabel#fps-counter {{
        background-color: rgba(0, 0, 0, 150);
        color: #ffffff;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 11px;
        padding: 3px 6px;
        border-radius: 3px;
    }}

    /* === Panel Title === */
    QLabel#panel-title {{
        color: {TEXT_PRIMARY};
        font-size: 15px;
        font-weight: 600;
        padding: 8px 12px;
    }}

    /* === Reset Buttons === */
    QPushButton#btn-reset-section {{
        background-color: transparent;
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        border-radius: 3px;
        padding: 3px 8px;
        font-size: 11px;
    }}
    QPushButton#btn-reset-section:hover {{
        color: {TEXT_PRIMARY};
        border-color: {ACCENT};
    }}

    QPushButton#btn-reset-all {{
        background-color: transparent;
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 5px 12px;
        font-weight: 500;
    }}
    QPushButton#btn-reset-all:hover {{
        color: {TEXT_PRIMARY};
        border-color: {ACCENT};
    }}

    QPushButton#btn-reset-all-postfx {{
        background-color: transparent;
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 5px 12px;
        font-weight: 500;
    }}
    QPushButton#btn-reset-all-postfx:hover {{
        color: {TEXT_PRIMARY};
        border-color: {ACCENT};
    }}

    /* === Panel Backgrounds === */
    QWidget#feature-viewer {{
        background-color: {BG_DARK};
        border-top: 1px solid {BORDER};
    }}
    QWidget#export-panel {{
        background-color: {BG_DARK};
    }}
    QWidget#preset-panel {{
        background-color: {BG_DARK};
    }}
    QWidget#postfx-panel {{
        background-color: {BG_DARK};
    }}

    /* === Tab Widget === */
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        background-color: {BG_PANEL};
    }}
    QTabBar::tab {{
        background-color: {BG_WIDGET};
        color: {TEXT_SECONDARY};
        padding: 6px 16px;
        border: 1px solid {BORDER};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background-color: {BG_PANEL};
        color: {ACCENT};
        border-bottom: 2px solid {ACCENT};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {BG_PANEL};
        color: {TEXT_PRIMARY};
    }}

    /* === Tooltip === */
    QToolTip {{
        background-color: {BG_WIDGET};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
    }}

    /* === Menu Bar === */
    QMenuBar {{
        background-color: {BG_DARK};
        color: {TEXT_PRIMARY};
        border-bottom: 1px solid {BORDER};
    }}
    QMenuBar::item:selected {{
        background-color: {ACCENT};
        color: #ffffff;
    }}
    QMenu {{
        background-color: {BG_PANEL};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
    }}
    QMenu::item:selected {{
        background-color: {ACCENT};
        color: #ffffff;
    }}

    /* === Reset Camera Button === */
    QPushButton#btn-reset-camera {{
        background-color: transparent;
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 13px;
    }}
    QPushButton#btn-reset-camera:hover {{
        color: {TEXT_PRIMARY};
        border-color: {ACCENT};
    }}
    """

    # Apply combined stylesheet
    app.setStyleSheet(existing + custom_qss)
