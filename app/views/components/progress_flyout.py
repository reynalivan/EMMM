# app/views/components/progress_flyout.py

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import FlyoutViewBase, BodyLabel, ProgressBar, TitleLabel

class ProgressFlyoutView(FlyoutViewBase):
    """
    A custom view to be shown inside a Flyout, displaying the progress
    of a background operation like reconciliation.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(20, 16, 20, 16)
        self.vBoxLayout.setSpacing(12)

        # --- Create Widgets ---
        self.titleLabel = TitleLabel("Synchronizing...", self)
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")

        # --- Add Widgets to Layout ---
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.progress_bar)

    def set_progress(self, current: int, total: int):
        """Updates the value of the progress bar."""
        if total > 0:
            percentage = int((current / total) * 100)
            if self.progress_bar:
                self.progress_bar.setValue(percentage)

    def reset(self):
        """Resets the progress bar to zero."""
        self.progress_bar.setValue(0)