# app/views/sections/object_list_panel.py

import os
from typing import Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem

# Fluent InfoBar
from qfluentwidgets import InfoBar, InfoBarIcon, InfoBarPosition

# App imports
from app.models.object_item_model import ObjectItemModel
from app.viewmodels.object_list_vm import ObjectListVM
from app.views.components.folder_grid_item_widget import FolderGridItemWidget
from app.views.components.object_list_item_widget import ObjectListItemWidget
from app.utils.logger_utils import logger
from app.core import constants


class ObjectListPanel(QWidget):
    """Panel displaying the list of object items (mod categories)."""

    def __init__(self, view_model: ObjectListVM, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.vm = view_model
        self.vm.set_handling_status_changes(True)

        self._widget_map: Dict[str, ObjectListItemWidget] = {}
        self._processing_infobars: Dict[str, InfoBar] = {}
        self._pending_operations_count = 0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Creates and arranges the UI elements."""
        # TODO: Add filter/search bar UI elements here
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ObjectListWidget")
        self.list_widget.setStyleSheet(
            "QListWidget { border: none; background-color: transparent; }"
        )
        # TODO: Implement Model/View + Delegate for performance instead of QListWidget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # TODO: Add filter bar to layout
        layout.addWidget(self.list_widget)

    def _connect_signals(self):
        """Connects signals between VM and Panel/Widgets."""
        if not hasattr(self, "vm") or not self.vm:
            logger.error("ViewModel not available for signal connection.")
            return
        try:
            # VM -> Panel General Updates
            self.vm.displayListChanged.connect(self._update_display_list)
            self.vm.loadingStateChanged.connect(self._set_list_loading)
            self.vm.showError.connect(self._show_error_infobar)

            # VM -> Panel (InfoBar Notifications)
            self.vm.operation_started.connect(self._on_operation_started)
            self.vm.operation_finished.connect(self._on_operation_finished)

            # VM -> Panel (Specific Item UI Control)
            # Use original_path as key from VM signals
            self.vm.itemThumbnailNeedsUpdate.connect(self._update_item_thumbnail)

            self.vm.setItemLoadingState.connect(self._set_item_loading_state)
            self.vm.updateItemDisplay.connect(self._update_item_display)

            # Panel Widgets -> VM
            self.list_widget.itemClicked.connect(self._on_item_clicked)
            # Note: status_toggled connected in _update_display_list
        except AttributeError as e:
            logger.error(
                f"Error connecting signals in ObjectListPanel: {e}", exc_info=True
            )

    def _clear_widget_map_and_items(self):
        """Clears the internal widget map and the QListWidget items."""
        self.list_widget.clear()
        self._widget_map.clear()

    def _update_display_list(self, items: list):
        """Populates the list widget with items from the ViewModel."""
        self._clear_widget_map_and_items()
        if not items:
            return

        for item_model in items:
            if not isinstance(item_model, ObjectItemModel):
                continue

            list_item = QListWidgetItem()
            widget = ObjectListItemWidget(item_model)
            list_item.setSizeHint(widget.sizeHint())

            # --- START MODIFICATION: Use clean path as map key ---
            clean_path_key = self._get_clean_path(item_model.path)
            if clean_path_key:  # Only map if path is valid
                self._widget_map[clean_path_key] = widget
            else:
                logger.warning(
                    f"Could not generate clean path key for {item_model.path}"
                )
            # --- END MODIFICATION ---

            # Connect the item widget's toggle signal to the VM's request slot
            try:
                widget.status_toggled.connect(
                    lambda checked, mod=item_model: self.vm.handle_item_status_toggle_request(
                        mod, checked
                    )
                )
                # TODO: Connect widget.bulk_selection_changed if needed
            except AttributeError as e:
                logger.error(
                    f"Error connecting signals for {item_model.display_name}: {e}"
                )

            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)

            # NOTE: Thumbnail requests deferred

    def _find_widget_by_path(self, item_path: str) -> ObjectListItemWidget | None:
        """Safely retrieves a widget from the internal map using its (usually original) path."""
        clean_path_key = self._get_clean_path(item_path)
        if not clean_path_key:
            logger.error(f"Cannot find widget for invalid path: {item_path}")
            return None

        widget = self._widget_map.get(clean_path_key)
        # if not widget: logger.warning(f"Widget not found in map for path: {normalized_path}") # Keep lean
        return widget

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handles clicking on an item in the list."""
        widget = self.list_widget.itemWidget(item)
        if isinstance(widget, ObjectListItemWidget):
            model = widget.get_item_model()
            self.vm.select_object_item(model)

    # --- Slots for Handling VM Signals ---

    def _set_list_loading(self, is_loading: bool):
        """Handles overall list loading state."""
        # TODO: Implement better visual indication for list loading
        self.list_widget.setEnabled(not is_loading)

    def _show_error_infobar(self, title: str, message: str):
        """Displays a generic error InfoBar."""
        InfoBar.error(
            title,
            message,
            duration=5000,
            position=InfoBarPosition.BOTTOM_RIGHT,
            parent=self.window(),
        )

    def _set_item_loading_state(self, item_path: str, is_loading: bool):
        """Sets the loading state for a specific item widget (uses clean path for lookup)."""
        # item_path received here is the original path from VM signal
        clean_path_key = self._get_clean_path(item_path)
        if not clean_path_key:
            return
        widget = self._find_widget_by_path(clean_path_key)

        if widget:
            widget.set_interactive(not is_loading)
            widget.show_loading_overlay(is_loading)
        # else: logger.warning(...) # Keep lean

    def _update_item_thumbnail(self, item_path: str, thumb_result: dict):
        """Updates the thumbnail of a specific item widget."""
        # Find widget using the original item path from the signal
        # _find_widget_by_path handles cleaning the path for map lookup
        widget = self.gridWidget.findItemWidgetByPath(item_path)
        if widget:
            thumbnail_path = thumb_result.get("path")
            status = thumb_result.get("status")
            pixmap = None
            if (
                status in ["hit", "generated"]
                and thumbnail_path
                and os.path.exists(thumbnail_path)
            ):
                try:
                    pixmap = QPixmap(thumbnail_path)
                    if pixmap.isNull():
                        pixmap = None
                except Exception as e:
                    logger.error(f"Panel: Error creating QPixmap: {e}")
                    pixmap = None  # Ensure pixmap is None on error
            # Ensure widget has the method before calling
            if hasattr(widget, "set_thumbnail"):
                widget.set_thumbnail(pixmap)

    def _on_operation_started(self, item_path: str, title: str):
        """Mark item as loading and lock interaction."""
        clean_path_key = self._get_clean_path(item_path)
        if not clean_path_key:
            return

        if existing_bar := self._processing_infobars.pop(clean_path_key, None):
            existing_bar.close()

        widget = self._find_widget_by_path(clean_path_key)
        if widget:
            widget.set_interactive(False)
            widget.show_loading_overlay(True)

        processing_bar = InfoBar(
            icon=InfoBarIcon.INFORMATION,
            title=title,
            content="Processing...",
            isClosable=False,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=-1,
            parent=self.window(),
        )
        self._processing_infobars[clean_path_key] = processing_bar
        processing_bar.show()

        self._pending_operations_count += 1

    def _on_operation_finished(
        self,
        original_item_path: str,
        final_item_path: str,
        title: str,
        content: str,
        success: bool,
    ):
        """Unlock item and handle batch InfoBar after all operations done."""
        clean_final_path = self._get_clean_path(final_item_path)

        if existing_bar := self._processing_infobars.pop(clean_final_path, None):
            existing_bar.close()

        widget = self._find_widget_by_path(clean_final_path)
        if widget:
            widget.set_interactive(True)
            widget.show_loading_overlay(False)

        self._pending_operations_count -= 1

        if self._pending_operations_count <= 0:
            self._show_batch_summary_infobar()

    def _show_batch_summary_infobar(self):
        """Show one final InfoBar summarizing the batch operation result."""
        success_count = self.vm._status_manager.get_success_count()
        failed_count = self.vm._status_manager.get_fail_count()

        position = InfoBarPosition.BOTTOM_RIGHT
        parent_window = self.window()
        duration = 2500 if failed_count == 0 else 5000

        if failed_count > 0:
            InfoBar.error(
                title=f"{failed_count} item(s) failed",
                content="Some items could not be updated. Please check.",
                isClosable=True,
                duration=duration,
                position=position,
                parent=parent_window,
            )
        else:
            InfoBar.success(
                title=f"{success_count} item(s) updated successfully",
                content="All items processed without errors.",
                isClosable=True,
                duration=duration,
                position=position,
                parent=parent_window,
            )

        self.vm._status_manager.reset_count()

    def _get_clean_path(self, item_path: str) -> str:
        """Removes the DISABLED prefix from the folder name in the path."""
        if not item_path:
            return ""
        dir_name = os.path.dirname(item_path)
        base_name = os.path.basename(item_path)
        prefix = constants.DISABLED_PREFIX
        if base_name.lower().startswith(prefix.lower()):
            clean_base_name = base_name[len(prefix) :]
            return os.path.normpath(os.path.join(dir_name, clean_base_name))
        else:
            return os.path.normpath(item_path)

    def _set_item_loading_state(self, item_path: str, is_loading: bool):
        clean_path_key = self._get_clean_path(item_path)
        if not clean_path_key:
            return
        widget = self._find_widget_by_path(clean_path_key)
        if widget:
            widget.set_interactive(not is_loading)
            widget.show_loading_overlay(is_loading)

    def _update_item_display(self, item_path: str, payload: dict):
        widget = self._find_widget_by_path(item_path)
        if widget:
            widget.update_display(payload)

    def _find_widget_by_path(self, item_path: str) -> ObjectListItemWidget | None:
        """Safely retrieves a widget from the internal map using its clean path."""
        clean_path_key = self._get_clean_path(item_path)
        if not clean_path_key:
            logger.error(f"Cannot find widget for invalid path: {item_path}")
            return None
        return self._widget_map.get(clean_path_key)
