# app/views/dialogs/progress_dialog.py

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout
from qfluentwidgets import ProgressBar, BodyLabel, PushButton, TitleLabel

class ProgressDialog(QDialog):
    """A modal dialog to show creation progress with a cancel button."""
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Creating Mods")
        self.setFixedWidth(400)
        self.setModal(True) # Block interaction with the main window
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False) # Hide close button

        main_layout = QVBoxLayout(self)

        self.title_label = TitleLabel("Processing...", self)
        self.status_label = BodyLabel("Starting...", self)
        self.progress_bar = ProgressBar(self)
        self.cancel_button = PushButton("Cancel")

        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.cancel_button, 0, Qt.AlignmentFlag.AlignRight)

        self.cancel_button.clicked.connect(self.cancel_requested)
        self.cancel_button.clicked.connect(self.reject) # Close the dialog on cancel

    def update_progress(self, current: int, total: int, filename: str = ""):
        """Updates the progress bar and status label."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.status_label.setText(f"Processing {current} of {total} : {filename}")