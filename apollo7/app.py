"""QApplication bootstrap for Apollo 7."""

from PySide6.QtWidgets import QApplication

from apollo7.gui.theme import load_theme_qss


def run() -> int:
    """Create the application, apply theme, show main window, and exec."""
    app = QApplication([])
    app.setApplicationName("Apollo 7")
    app.setStyleSheet(load_theme_qss())

    # Import here to avoid circular imports and ensure QApplication exists first
    from apollo7.gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()
