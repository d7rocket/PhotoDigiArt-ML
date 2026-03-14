"""Apollo 7 dark theme -- Maya x Unreal x modern SaaS aesthetic.

Custom QSS stylesheet with electric blue (#0078FF) accent color,
dark backgrounds, and styled interactive elements.
"""


def load_theme_qss() -> str:
    """Return the full Apollo 7 dark QSS stylesheet."""
    accent = "#0078FF"
    accent_hover = "#339BFF"
    accent_pressed = "#005FCC"
    bg_dark = "#1a1a1a"
    bg_panel = "#242424"
    bg_widget = "#2d2d2d"
    bg_input = "#1e1e1e"
    text_primary = "#e0e0e0"
    text_secondary = "#808080"
    text_disabled = "#555555"
    border = "#3a3a3a"
    border_focus = accent

    return f"""
    /* === Base === */
    QMainWindow, QWidget {{
        background-color: {bg_dark};
        color: {text_primary};
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }}

    /* === Splitter Handles === */
    QSplitter::handle {{
        background-color: {border};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}
    QSplitter::handle:hover {{
        background-color: {accent};
    }}

    /* === Buttons === */
    QPushButton {{
        background-color: {bg_widget};
        color: {text_primary};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {accent};
        border-color: {accent};
        color: #ffffff;
    }}
    QPushButton:pressed {{
        background-color: {accent_pressed};
        border-color: {accent_pressed};
    }}
    QPushButton:disabled {{
        background-color: {bg_panel};
        color: {text_disabled};
        border-color: {bg_panel};
    }}

    /* === Progress Bar === */
    QProgressBar {{
        background-color: {bg_widget};
        border: 1px solid {border};
        border-radius: 4px;
        text-align: center;
        color: {text_primary};
        height: 18px;
        font-size: 11px;
    }}
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 3px;
    }}

    /* === Scroll Bars === */
    QScrollBar:vertical {{
        background-color: {bg_panel};
        width: 8px;
        border: none;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background-color: {border};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {accent};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
        border: none;
    }}
    QScrollBar:horizontal {{
        background-color: {bg_panel};
        height: 8px;
        border: none;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {border};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {accent};
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
        border: none;
    }}

    /* === Labels === */
    QLabel {{
        color: {text_secondary};
        background-color: transparent;
    }}
    QLabel#panel-title {{
        color: {text_primary};
        font-size: 14px;
        font-weight: 600;
        padding: 8px 12px;
    }}

    /* === Group Box === */
    QGroupBox {{
        background-color: {bg_panel};
        border: 1px solid {border};
        border-radius: 6px;
        margin-top: 14px;
        padding-top: 18px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 8px;
        color: {accent};
    }}

    /* === Combo Box === */
    QComboBox {{
        background-color: {bg_widget};
        color: {text_primary};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 24px;
    }}
    QComboBox:hover {{
        border-color: {accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {bg_widget};
        color: {text_primary};
        border: 1px solid {border};
        selection-background-color: {accent};
        selection-color: #ffffff;
    }}

    /* === Slider === */
    QSlider::groove:horizontal {{
        background-color: {bg_widget};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background-color: {accent};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background-color: {accent_hover};
    }}
    QSlider::sub-page:horizontal {{
        background-color: {accent};
        border-radius: 2px;
    }}

    /* === Line Edit / Spin Box === */
    QLineEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {bg_input};
        color: {text_primary};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {border_focus};
    }}

    /* === Tab Widget === */
    QTabWidget::pane {{
        border: 1px solid {border};
        background-color: {bg_panel};
    }}
    QTabBar::tab {{
        background-color: {bg_widget};
        color: {text_secondary};
        padding: 6px 16px;
        border: 1px solid {border};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background-color: {bg_panel};
        color: {accent};
        border-bottom: 2px solid {accent};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {bg_panel};
        color: {text_primary};
    }}

    /* === Radio Button === */
    QRadioButton {{
        color: {text_secondary};
        spacing: 8px;
        padding: 4px 2px;
    }}
    QRadioButton:hover {{
        color: {text_primary};
    }}
    QRadioButton:checked {{
        color: {text_primary};
        font-weight: 600;
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {border};
        border-radius: 10px;
        background-color: {bg_input};
    }}
    QRadioButton::indicator:hover {{
        border-color: {accent_hover};
    }}
    QRadioButton::indicator:checked {{
        border-color: {accent};
        background-color: {accent};
    }}
    QRadioButton::indicator:checked:hover {{
        border-color: {accent_hover};
        background-color: {accent_hover};
    }}

    /* === Checkbox === */
    QCheckBox {{
        color: {text_secondary};
        spacing: 8px;
        padding: 4px 2px;
    }}
    QCheckBox:hover {{
        color: {text_primary};
    }}
    QCheckBox:checked {{
        color: {text_primary};
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {border};
        border-radius: 3px;
        background-color: {bg_input};
    }}
    QCheckBox::indicator:hover {{
        border-color: {accent_hover};
    }}
    QCheckBox::indicator:checked {{
        border-color: {accent};
        background-color: {accent};
    }}

    /* === Feature Viewer === */
    QWidget#feature-viewer {{
        background-color: {bg_dark};
        border-top: 1px solid {border};
    }}

    /* === Simulation Panel === */
    QPushButton#btn-simulate {{
        background-color: {accent};
        color: #ffffff;
        font-weight: 600;
        font-size: 14px;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
    }}
    QPushButton#btn-simulate:hover {{
        background-color: {accent_hover};
    }}
    QPushButton#btn-simulate:pressed {{
        background-color: {accent_pressed};
    }}
    QPushButton#btn-simulate:disabled {{
        background-color: {bg_panel};
        color: {text_disabled};
    }}

    QPushButton#btn-reset-section {{
        background-color: transparent;
        color: {text_secondary};
        border: 1px solid {border};
        border-radius: 3px;
        padding: 3px 8px;
        font-size: 11px;
    }}
    QPushButton#btn-reset-section:hover {{
        color: {text_primary};
        border-color: {accent};
    }}

    QPushButton#btn-reset-all {{
        background-color: transparent;
        color: {text_secondary};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 5px 12px;
        font-weight: 500;
    }}
    QPushButton#btn-reset-all:hover {{
        color: {text_primary};
        border-color: {accent};
    }}

    /* Collapsible group boxes (checkable toggle) */
    QGroupBox::indicator {{
        width: 12px;
        height: 12px;
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

    /* === Tooltip === */
    QToolTip {{
        background-color: {bg_widget};
        color: {text_primary};
        border: 1px solid {border};
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
    }}

    /* === Menu Bar === */
    QMenuBar {{
        background-color: {bg_dark};
        color: {text_primary};
        border-bottom: 1px solid {border};
    }}
    QMenuBar::item:selected {{
        background-color: {accent};
        color: #ffffff;
    }}
    QMenu {{
        background-color: {bg_panel};
        color: {text_primary};
        border: 1px solid {border};
    }}
    QMenu::item:selected {{
        background-color: {accent};
        color: #ffffff;
    }}
    """
