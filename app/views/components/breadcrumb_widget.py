# app/views/components/breadcrumb_widget.py

from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6.QtCore import (
    pyqtSignal,
    Qt,
    QTimer,
)  # Import QTimer just in case needed later, Qt might not be needed now

# --- Fluent Widget Imports ---
from qfluentwidgets import (
    BreadcrumbBar,
    setFont,
)  # Import BreadcrumbBar, setFont is optional

# --- End Fluent Widget Imports ---
# Import logger if you intend to add logging later, otherwise can be removed
from app.utils.logger_utils import logger


class BreadcrumbWidget(QWidget):
    """
    A wrapper widget providing a standard interface ('segment_clicked' signal)
    around qfluentwidgets.BreadcrumbBar for breadcrumb navigation.
    """

    # Keep existing signal name for compatibility with FolderGridPanel
    segment_clicked = pyqtSignal(int)  # index of the clicked segment

    def __init__(self, parent: QWidget | None = None):
        """Initialize the wrapper and the internal BreadcrumbBar."""
        super().__init__(parent)

        # Main layout for this wrapper widget (simple box)
        self.widget_layout = QHBoxLayout(self)
        self.widget_layout.setContentsMargins(16, 8, 8, 0)

        # Create the core BreadcrumbBar component from qfluentwidgets
        self.breadcrumb_bar = BreadcrumbBar(self)
        try:
            # Assuming the signal indicating a click provides the index
            self.breadcrumb_bar.currentIndexChanged.connect(
                self._on_internal_breadcrumb_clicked
            )
        except AttributeError:
            logger.error(
                "'BreadcrumbBar' object has no attribute 'currentIndexChanged'. Check signal name in documentation for your version."
            )

        self.widget_layout.addWidget(self.breadcrumb_bar)

    def set_path(self, segments: list[str]):
        """Sets the breadcrumb path displayed in the widget."""
        logger.info(f"BreadcrumbWidget: set_path called with segments: {segments}")
        try:
            blocked = self.breadcrumb_bar.blockSignals(True)

            self.breadcrumb_bar.clear()
            if not segments:
                return

            logger.debug(
                f"  Adding {len(segments)} items to BreadcrumbBar..."
            )  # Hapus jika tidak perlu
            # Add each segment
            for i, name in enumerate(segments):
                self.breadcrumb_bar.addItem(routeKey=str(i), text=name)

        finally:
            self.breadcrumb_bar.blockSignals(blocked)

    def _on_internal_breadcrumb_clicked(self, index: int):
        self.segment_clicked.emit(index)
