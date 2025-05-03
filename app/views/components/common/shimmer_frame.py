import sys
import math
from PyQt6.QtWidgets import QWidget, QApplication  # Added for testing if needed
from PyQt6.QtCore import QObject, QEvent, QTimer, QRectF, Qt
from PyQt6.QtGui import QPainter, QBrush, QColor, QLinearGradient, QPainterPath


# ============================================
# Corrected ShimmerFrame Class
# ============================================
class ShimmerFrame(QWidget):

    def __init__(
        self, parent=None, radius: int = 10, base_color=None, highlight_color=None
    ):
        super().__init__(parent)

        # === Configurable Parameters ===
        self._base_color = base_color or QColor(80, 80, 80, 100)
        self._highlight_color = highlight_color or QColor(120, 120, 120, 150)
        self._speed = 0.02  # default
        self._highlight_width = 0.3
        self._radius = radius
        self._gradient_pos = -0.5  # Start shimmer gradient offscreen (left)
        self._is_running = False

        # === Animation Timer ===
        self.timer = QTimer(self)
        self.timer.setInterval(30)  # ~33 FPS
        self.timer.timeout.connect(self._update_gradient_pos)

        # === Visual Style ===
        self.setStyleSheet(
            f"""
            border-radius: {radius}px;
            background-color: rgba(0, 0, 0, 0);  /* Fully transparent */
            """
        )

        # === Overlay Attributes ===
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )  # Let clicks pass through
        self.setAttribute(
            Qt.WidgetAttribute.WA_NoSystemBackground
        )  # Disable native background
        self.setAutoFillBackground(False)  # Avoid background painting
        self.hide()  # Hidden by default

    def start(self, delay_ms=0):
        if self._is_running:
            return
        self._is_running = True
        self._gradient_pos = -0.5
        self.show()
        QTimer.singleShot(delay_ms, self._start_timer)

    def _start_timer(self):
        if not self.timer.isActive():
            self.timer.start()
        self.update()

    def stop(self):
        """Stops the shimmer animation."""
        if self._is_running:
            self._is_running = False
            if self.timer.isActive():
                self.timer.stop()
            self.hide()  # Optionally hide shimmer if no longer needed
            self.update()  # Clean repaint (clears gradient)

    def stop_and_delete(self):
        """Stops shimmer and schedules the widget for deletion."""
        self.stop()
        self.deleteLater()  # Mark widget for safe deletion in Qt event loop

    def _update_gradient_pos(self):
        """Advance shimmer position and trigger repaint."""
        if not self._is_running:
            return

        self._gradient_pos += self._speed
        if self._gradient_pos > 1.5 or not math.isfinite(self._gradient_pos):
            self._gradient_pos = -0.5

        self.update()

    def _clamp01(self, val: float) -> float:
        """Clamp float to range [0.0, 1.0], handle NaN/infinity safely."""
        try:
            return max(0.0, min(1.0, float(val)))
        except (TypeError, ValueError):
            print(f"[Shimmer] Invalid value in _clamp01: {val}. Defaulting to 0.0")
            return 0.0

    def paintEvent(self, event):
        """Paint shimmer effect with gradient inside rounded rect."""
        if self.width() <= 1 or self.height() <= 1 or not self._is_running:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Clamp shimmer positions
        width = self.width()
        start = self._clamp01(self._gradient_pos)
        end = self._clamp01(self._gradient_pos + self._highlight_width)

        # Ensure valid width
        if end <= start:
            end = min(1.0, start + 0.001)

        # Gradient build
        grad = QLinearGradient(0, 0, width, 0)
        grad.setColorAt(0.0, self._base_color)
        grad.setColorAt(1.0, self._base_color)
        grad.setColorAt(start, self._highlight_color)
        grad.setColorAt(end, self._base_color)

        # Clip to rounded rect
        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, float(self._radius), float(self._radius))

        painter.setClipPath(path)
        painter.fillRect(rect, QBrush(grad))

    def set_radius(self, radius: int):
        self._radius = radius
        self.setStyleSheet(
            f"border-radius: {radius}px; background-color: rgba(0, 0, 0, 0);"
        )
        self.update()

    def is_running(self) -> bool:
        return self._is_running
