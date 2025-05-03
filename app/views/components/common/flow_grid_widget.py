# app/views/components/common/flow_grid_widget.py (REVISED)


import os
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

    # ---Signals (Emitted by this widget) ---
    itemClicked = pyqtSignal(FolderItemModel)
    itemDoubleClicked = pyqtSignal(FolderItemModel)
    itemBulkSelectionChanged = pyqtSignal(FolderItemModel, bool)  # model, is_checked

    itemPasteRequested = pyqtSignal(FolderItemModel)  # Model
    itemStatusToggled = pyqtSignal(str, bool)
    visiblePathsRequested = pyqtSignal(list)
    # ---End Signals ---

    # Corrected __init__: No VM or Breadcrumb needed here

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FlowGridContentWidget")
        self._path_to_widget: dict[str, FolderGridItemWidget] = {}

        self.flowLayout = FlowLayout(self, needAni=False)  # Set parent=self
        self.flowLayout.setContentsMargins(8, 8, 8, 8)  # Adjust as needed
        self.flowLayout.setVerticalSpacing(10)  # Adjust as needed
        self.flowLayout.setHorizontalSpacing(10)  # Adjust as needed
        self._item_widgets: list[FolderGridItemWidget] = []
        # Removed self.vm, self.breadcrumb_widget
        # Removed self._connect_signals() call

    def clearItems(self):
        """Removes all items from the layout and deletes the widgets safely."""
        while (item_or_widget := self.flowLayout.takeAt(0)) is not None:
            widget_to_delete = None
            if isinstance(item_or_widget, QWidget):
                widget_to_delete = item_or_widget
            elif isinstance(item_or_widget, QLayoutItem):
                widget_to_delete = item_or_widget.widget()
            else:
                logger.warning(
                    f"FlowLayout.takeAt(0) returned unexpected type: {type(item_or_widget)}"
                )

            if widget_to_delete is not None:
                try:
                    widget_to_delete.disconnect()
                except Exception:
                    pass  # Ignore disconnect error
                if widget_to_delete.isVisible():
                    widget_to_delete.hide()  # Hide first (safe way)
                widget_to_delete.setParent(None)  # Detach from layout
                widget_to_delete.deleteLater()  # Delete safely

        self._item_widgets.clear()
        self._path_to_widget.clear()

    # Renamed from _update_display_list

    def setItems(self, item_models: list[FolderItemModel]):
        """Clears existing items and adds new ones based on the provided models."""
        self.clearItems()

        for model in item_models:
            if not isinstance(model, FolderItemModel):
                logger.warning(f"FlowGridWidget: Skipping non-FolderItemModel: {model}")
                continue

            normalized_path = os.path.normpath(model.path)

            if normalized_path in self._path_to_widget:
                logger.warning(
                    f"FlowGridWidget: Duplicate path detected: {normalized_path}, overwriting."
                )

            widget = FolderGridItemWidget(model)
            self._item_widgets.append(widget)
            self._path_to_widget[normalized_path] = widget

            # Connect widget signals to GridWidget
            try:
                widget.clicked.connect(lambda mod=model: self.itemClicked.emit(mod))
                widget.doubleClicked.connect(
                    lambda mod=model: self.itemDoubleClicked.emit(mod)
                )
                widget.status_toggled.connect(
                    lambda checked, m=widget.item_model: self._on_item_status_toggled(
                        m, checked
                    )
                )
                widget.bulk_selection_changed.connect(
                    lambda checked, mod=model: self.itemBulkSelectionChanged.emit(
                        mod, checked
                    )
                )
                widget.paste_requested.connect(
                    lambda mod=model: self.itemPasteRequested.emit(mod)
                )
            except AttributeError as e:
                logger.error(
                    f"FlowGridWidget: Error connecting signals for {model.display_name}: {e}"
                )

            self.flowLayout.addWidget(widget)

        self.flowLayout.invalidate()
        self.updateGeometry()
        visible_paths = [os.path.normpath(model.path) for model in item_models[:30]]
        self.visiblePathsRequested.emit(visible_paths)

    def sizeHint(self):
        return self.flowLayout.sizeHint()

    def findItemWidgetByPath(self, item_path: str) -> FolderGridItemWidget | None:
        """Finds and returns the item widget corresponding to the given path."""
        normalized_path = os.path.normpath(item_path)
        return self._path_to_widget.get(normalized_path)

    def _on_item_status_toggled(self, model, checked: bool):
        if model:
            self.itemStatusToggled.emit(model.path, checked)

    def updateItemPath(self, old_path: str, new_path: str):
        """Updates internal widget mapping and model after a path rename."""
        normalized_old = os.path.normpath(old_path)
        normalized_new = os.path.normpath(new_path)

        item = self._path_to_widget.pop(normalized_old, None)
        if not item:
            logger.warning(
                f"FlowGridWidget: No widget found for old path: {normalized_old}"
            )
            return

        if normalized_new in self._path_to_widget:
            logger.warning(
                f"FlowGridWidget: Overwriting existing widget for new path: {normalized_new}"
            )

        self._path_to_widget[normalized_new] = item

        # Update the model inside the widget
        model = item.get_item_model()
        model.path = normalized_new
        model.folder_name = os.path.basename(normalized_new)

        logger.debug(
            f"FlowGridWidget: Path updated {normalized_old} ➔ {normalized_new}"
        )
