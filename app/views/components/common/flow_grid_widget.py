# app/views/components/common/flow_grid_widget.py (REVISED)

from PyQt6.QtWidgets import QWidget, QLayoutItem
from PyQt6.QtCore import pyqtSignal, QObject
from qfluentwidgets import FlowLayout
# Adjust import paths based on your actual structure
from app.views.components.folder_grid_item_widget import FolderGridItemWidget
from app.models.folder_item_model import FolderItemModel
from app.utils.logger_utils import logger


class FlowGridWidget(QWidget):
    """
    A widget that displays FolderGridItemWidgets in a responsive flow layout
    using qfluentwidgets.FlowLayout. Handles item creation and relays signals.
    """
    # --- Signals (Emitted by this widget) ---
    itemClicked = pyqtSignal(FolderItemModel)
    itemDoubleClicked = pyqtSignal(FolderItemModel)
    itemStatusToggled = pyqtSignal(FolderItemModel, bool)  # model, is_checked
    itemBulkSelectionChanged = pyqtSignal(FolderItemModel,
                                          bool)  # model, is_checked
    itemPasteRequested = pyqtSignal(FolderItemModel)  # model

    # --- End Signals ---

    # Corrected __init__: No VM or Breadcrumb needed here
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FlowGridContentWidget")

        # Apply FlowLayout directly to this widget
        self.flowLayout = FlowLayout(self, needAni=False)  # Set parent=self
        self.flowLayout.setContentsMargins(8, 8, 8, 8)  # Adjust as needed
        self.flowLayout.setVerticalSpacing(10)  # Adjust as needed
        self.flowLayout.setHorizontalSpacing(10)  # Adjust as needed

        # Removed self.vm, self.breadcrumb_widget
        # Removed self._connect_signals() call

    def clearItems(self):
        """Removes all items from the layout and deletes the widgets safely."""
        # logger.debug(f"FlowGridWidget: Clearing {self.flowLayout.count()} items.") # Keep lean

        # --- START MODIFICATION: Handle takeAt() returning QWidget ---
        # Loop while the layout still has items to take
        while (item_or_widget := self.flowLayout.takeAt(0)) is not None:
            widget_to_delete = None
            if isinstance(item_or_widget, QWidget):
                # If takeAt directly returns the widget (based on error)
                widget_to_delete = item_or_widget
            elif isinstance(item_or_widget, QLayoutItem):
                # Standard QLayout behavior fallback
                widget_to_delete = item_or_widget.widget()
            else:
                logger.warning(
                    f"FlowLayout.takeAt(0) returned unexpected type: {type(item_or_widget)}"
                )

            if widget_to_delete is not None:
                # logger.debug(f"  Deleting widget: {widget_to_delete.objectName()}") # Keep lean
                # Disconnect signals first (safer)
                try:
                    widget_to_delete.disconnect()
                except TypeError:
                    pass
                # Schedule for deletion
                widget_to_delete.deleteLater()
        # --- END MODIFICATION ---

    # Renamed from _update_display_list
    def setItems(self, item_models: list[FolderItemModel]):
        """Clears existing items and adds new ones based on the provided models."""
        self.clearItems()  # Clear previous widgets first
        # logger.debug(f"FlowGridWidget: Setting {len(item_models)} items.") # Keep lean

        for model in item_models:
            if not isinstance(model, FolderItemModel):
                logger.warning(
                    f"FlowGridWidget: Skipping non-FolderItemModel item: {model}"
                )
                continue

            widget = FolderGridItemWidget(model)

            # Connect signals FROM the item widget TO THIS widget's signals
            # Using lambdas to capture the specific 'model' for each widget
            try:
                # --- Keep only this block for connecting signals ---
                widget.clicked.connect(
                    lambda mod=model: self.itemClicked.emit(mod))
                widget.doubleClicked.connect(
                    lambda mod=model: self.itemDoubleClicked.emit(mod))
                widget.status_toggled.connect(
                    lambda checked, mod=model: self.itemStatusToggled.emit(
                        mod, checked))
                widget.bulk_selection_changed.connect(
                    lambda checked, mod=model: self.itemBulkSelectionChanged.
                    emit(mod, checked))
                widget.paste_requested.connect(
                    lambda mod=model: self.itemPasteRequested.emit(mod))
            except AttributeError as e:
                logger.error(
                    f"FlowGridWidget: Error connecting signals for item {model.display_name}: {e}"
                )

            self.flowLayout.addWidget(widget)  # Add item widget to layout

        # Remove self.resize(...) call
        # Trigger layout update
        self.flowLayout.invalidate()
        self.updateGeometry()  # Update this widget's geometry

    # sizeHint override can be useful
    def sizeHint(self):
        return self.flowLayout.sizeHint()

    # Removed methods that don't belong here:
    # _connect_signals
    # _update_breadcrumbs
    # _on_breadcrumb_clicked
    # _log_and_emit_double_click


# --- End of flow_grid_widget.py ---
