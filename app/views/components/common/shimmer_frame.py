# app/views/components/common/shimmer_frame.py

from PyQt6.QtWidgets import QFrame, QWidget
from PyQt6.QtCore import QPropertyAnimation


class ShimmerFrame(QFrame):
    """
    A reusable overlay widget that provides a shimmering loading animation.
    It's placed on left panel objectlist and top panel foldergrid. This is
    shown/hidden by the ViewModel's loading signals.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # --- UI and Animation objects would be initialized here ---
        # self.animation = QPropertyAnimation(...)
        self.hide()  # The widget is hidden by default.

    def paintEvent(self, event):
        """Overrides the paint event to draw the semi-transparent background and the shimmer."""
        # This is where the visual magic happens, using QPainter to draw the gradient.
        super().paintEvent(event)
        pass

    # --- Public Methods (API for the parent panel) ---

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
