"""Settings dialog for API key management.

Modal dialog allowing users to enter and save their Anthropic API key.
The key is stored in ~/.apollo7/config.json and loaded at startup.
"""

from __future__ import annotations

import apollo7.config.settings as settings
from apollo7.config.settings import load_api_key, save_api_key

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Signal


class SettingsDialog(QtWidgets.QDialog):
    """Modal dialog for managing application settings.

    Currently provides API key entry for Claude features. The key
    is persisted to ~/.apollo7/config.json on save.

    Signals:
        api_key_saved: Emitted with the key string when saved.
    """

    api_key_saved = Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 200)
        self.setModal(True)

        self._build_ui()
        self._load_current_key()

    def _build_ui(self) -> None:
        """Build the dialog layout."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Heading
        heading = QtWidgets.QLabel("Settings")
        heading.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(heading)

        layout.addSpacing(8)

        # API key label
        key_label = QtWidgets.QLabel("Anthropic API Key")
        key_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(key_label)

        # API key input
        self._key_input = QtWidgets.QLineEdit()
        self._key_input.setObjectName("api-key-input")
        self._key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("sk-ant-...")
        layout.addWidget(self._key_input)

        # Help text
        help_label = QtWidgets.QLabel(
            "Required for Claude features. Get a key at console.anthropic.com"
        )
        help_label.setStyleSheet("font-size: 11px; color: #808080;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        layout.addStretch()

        # Button row
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        btn_discard = QtWidgets.QPushButton("Discard Changes")
        btn_discard.setStyleSheet(
            "background-color: transparent; border: 1px solid #3a3a3a;"
        )
        btn_discard.clicked.connect(self.reject)
        btn_layout.addWidget(btn_discard)

        btn_save = QtWidgets.QPushButton("Save API Key")
        btn_save.setObjectName("btn-save-key")
        btn_save.setStyleSheet(
            "background-color: #0078FF; color: #ffffff; font-weight: 600;"
        )
        btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _load_current_key(self) -> None:
        """Populate input with existing key if available."""
        current = load_api_key()
        if current:
            self._key_input.setText(current)

    def _on_save(self) -> None:
        """Save the API key and close the dialog."""
        key = self._key_input.text().strip()
        if key:
            save_api_key(key)
            # Update the module-level constant so the app picks it up
            settings.CLAUDE_API_KEY = key
            self.api_key_saved.emit(key)
        self.accept()
