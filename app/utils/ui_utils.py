# app/utils/ui_utils.py
from PyQt6.QtWidgets import QWidget, QFrame, QMessageBox


class UiUtils:
    """A collection of static utility functions and custom widgets for the UI."""

    @staticmethod
    def create_confirmation_dialog(
        parent: QWidget, title: str, text: str, informative_text: str = ""
    ) -> bool:
        """Creates a standardized confirmation dialog (e.g., for deletes or overwrites)."""
        # Returns True if the user clicks the affirmative button (Yes/OK), otherwise False.
        return True  # Placeholder for actual dialog logic


class ShimmerFrame(QFrame):
    """A reusable overlay widget that provides a shimmering loading animation."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # --- UI and Animation objects would be initialized here ---
        self.hide()  # Initially hidden

    def start_shimmer(self):
        """Makes the widget visible and starts the animation loop."""
        self.show()
        # self.animation.start()
        pass

    def stop_shimmer(self):
        """Stops the animation and hides the widget."""
        # self.animation.stop()
        self.hide()
        pass
