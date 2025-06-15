# app/views/components/common/shimmer_frame.py
# A custom-painted shimmer overlay widget for indicating a loading state.

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, QRectF, Qt
from PyQt6.QtGui import QPainter, QBrush, QColor, QLinearGradient, QPainterPath


class ShimmerFrame(QWidget):
    """
    A reusable overlay widget that provides a shimmering loading animation.
    It's designed to be placed on top of other widgets (like a list or grid)
    and is controlled by its parent panel.
    """

    def __init__(self, parent: QWidget | None = None, radius: int = 8):
        super().__init__(parent)

        # --- Configurable Parameters ---
        # Colors for a dark theme shimmer
        self._base_color = QColor(55, 55, 55, 120)
        self._highlight_color = QColor(85, 85, 85, 160)
        self._speed = 0.025  # Animation speed
        self._highlight_width = 0.4  # Width of the shimmer highlight
        self._radius = radius

        self._gradient_pos = -0.5  # Start shimmer gradient offscreen (left)
        self._is_running = False

        # --- Animation Timer ---
        self.timer = QTimer(self)
        self.timer.setInterval(30)  # ~33 FPS for smooth animation
        self.timer.timeout.connect(self._update_gradient_pos)

        # --- Widget Attributes for Overlay Behavior ---
        # Let mouse clicks pass through to the widget underneath
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # We handle all painting ourselves
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        self.hide()  # Hidden by default

    def paintEvent(self, event):
        """Overrides the paint event to draw the semi-transparent background and the shimmer."""
        if not self._is_running or self.width() <= 1 or self.height() <= 1:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # --- Shimmer Gradient Calculation ---
        # Clamp values between 0.0 and 1.0
        start_pos = max(0.0, min(1.0, self._gradient_pos))
        end_pos = max(0.0, min(1.0, self._gradient_pos + self._highlight_width))

        if end_pos <= start_pos:
            return  # Avoid invalid gradient

        gradient = QLinearGradient(0, 0, self.width(), 0)
        # Base color across the whole gradient
        gradient.setColorAt(0.0, self._base_color)
        gradient.setColorAt(1.0, self._base_color)
        # Insert the highlight color to create the shimmer effect
        gradient.setColorAt(start_pos, self._highlight_color)
        gradient.setColorAt(end_pos, self._base_color)

        # --- Draw the Rounded Rectangle ---
        rect_path = QPainterPath()
        rect_path.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)

        # Clip the painter to the rounded path before filling
        painter.setClipPath(rect_path)
        painter.fillRect(self.rect(), QBrush(gradient))

    def resizeEvent(self, event):
        """Ensure the widget repaints on resize."""
        super().resizeEvent(event)
        self.update()

    def _update_gradient_pos(self):
        """Advances the shimmer position and triggers a repaint."""
        if not self._is_running:
            return

        self._gradient_pos += self._speed
        # Reset position when it moves completely offscreen to the right
        if self._gradient_pos > (1.0 + self._highlight_width):
            self._gradient_pos = -self._highlight_width

        self.update()

    # --- Public Methods (API for the parent panel) ---

    def start_shimmer(self):
        """Makes the widget visible and starts the animation loop."""
        if self._is_running:
            return

        self._is_running = True
        self._gradient_pos = -self._highlight_width  # Reset position
        self.show()
        if not self.timer.isActive():
            self.timer.start()
        self.update()

    def stop_shimmer(self):
        """Stops the animation and hides the widget."""
        if not self._is_running:
            return

        self._is_running = False
        if self.timer.isActive():
            self.timer.stop()
        self.hide()
        self.update()  # Trigger a final repaint to clear the gradient
