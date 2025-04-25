# app/views/sections/folder_grid_panel.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, QSize, QEasingCurve
from app.viewmodels.folder_grid_vm import FolderGridVM
from app.views.components.breadcrumb_widget import BreadcrumbWidget

# Import the custom grid widget and Fluent ScrollArea
from app.views.components.common.flow_grid_widget import FlowGridWidget
from qfluentwidgets import ScrollArea, ScrollBar

# Import logger only if error logging is kept
from app.utils.logger_utils import logger


class FolderGridPanel(QWidget):
    """Panel containing the breadcrumb and the main grid view for folders/mods."""

    def __init__(self, view_model: FolderGridVM, parent=None):
        super().__init__(parent)
        self.vm = view_model
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Creates and arranges the UI elements."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 5, 5, 5)
        self.main_layout.setSpacing(5)

        # 1. Breadcrumb
        self.breadcrumb_widget = BreadcrumbWidget(self)
        self.main_layout.addWidget(self.breadcrumb_widget)

        # TODO: Implement Filter Bar using Fluent widgets here

        # Optional Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet(
            "border-top: 1px solid rgba(0,0,0,0.1);"
        )  # Style needs theme awareness
        self.main_layout.addWidget(line)

        # 2. Grid Area using SmoothScrollArea and FlowGridWidget
        self.scrollArea = ScrollArea(self)
        self.scrollArea.enableTransparentBackground()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)

        # Optional: Configure smooth scroll animation
        # self.scrollArea.setScrollAnimation(Qt.Orientation.Vertical, 400, QEasingCurve.OutQuad)

        self.gridWidget = FlowGridWidget(self)
        self.scrollArea.setWidget(self.gridWidget)

        self.main_layout.addWidget(self.scrollArea, 1)  # Grid takes remaining space

    def _connect_signals(self):
        """Connects signals between VM, Panel, Breadcrumb, and Grid Widget."""
        if not hasattr(self, "gridWidget") or not hasattr(self, "breadcrumb_widget"):
            logger.error("UI components not ready for signal connection.")
            return
        try:
            # VM -> UI Elements
            self.vm.displayListChanged.connect(self.gridWidget.setItems)
            self.vm.breadcrumbChanged.connect(self.breadcrumb_widget.set_path)

            # UI Elements -> VM
            self.breadcrumb_widget.segment_clicked.connect(
                self.vm.navigate_to_breadcrumb_index
            )
            self.gridWidget.itemClicked.connect(self.vm.select_folder_item)
            self.gridWidget.itemDoubleClicked.connect(self.vm.handle_item_double_click)

            # TODO: Connect other signals from gridWidget (itemStatusToggled etc.) to VM slots

        except AttributeError as e:
            # Keep error logging as it's essential for debugging connection issues
            logger.error(
                f"Error connecting signals in FolderGridPanel: {e}", exc_info=True
            )

    # No _update_display_list or _clear_grid_items needed here anymore
    # No _update_breadcrumbs or _on_breadcrumb_clicked needed here anymore
