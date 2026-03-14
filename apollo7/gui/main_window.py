"""Main window -- placeholder until Task 2."""

from PySide6.QtWidgets import QLabel, QMainWindow

from apollo7.config.settings import MIN_WINDOW_SIZE, WINDOW_SIZE


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apollo 7")
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*MIN_WINDOW_SIZE)
        self.setCentralWidget(QLabel("Apollo 7 -- viewport placeholder"))
