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

            clean_path_key = self._get_clean_path(item_model.path)
            if clean_path_key:
                self._widget_map[clean_path_key] = widget
            else:
                logger.warning(
                    f"Could not generate clean path key for {item_model.path}"
                )

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
            self.vm.request_thumbnail_for(item_model)

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
            return os.path.normpath(
                os.path.join(dir_name, clean_base_name)
            )  # << PATCH NORM
        else:
            return os.path.normpath(item_path)  # << PATCH NORM

    def _set_item_loading_state(self, item_path: str, is_loading: bool):
        clean_path_key = self._get_clean_path(item_path)
        if not clean_path_key:
            return
        widget = self._find_widget_by_path(clean_path_key)
        if widget:
            widget.set_interactive(not is_loading)
            widget.show_loading_overlay(is_loading)

    def _update_item_display(self, old_path: str, payload: dict):
        """Update display dan internal path mapping setelah item di-rename."""
        new_path = payload.get("path")
        if not new_path:
            return

        clean_old_path = self._get_clean_path(old_path)
        clean_new_path = self._get_clean_path(new_path)

        widget = self._find_widget_by_path(clean_old_path)
        if widget:
            widget.update_display(payload)

            # Update internal mapping
            if clean_old_path in self._widget_map:
                self._widget_map.pop(clean_old_path)
            self._widget_map[clean_new_path] = widget
            logger.debug(
                f"ObjectListPanel: Updated widget map {clean_old_path} ➔ {clean_new_path}"
            )
        else:
            logger.warning(
                f"ObjectListPanel: Widget not found for old path {clean_old_path}"
            )

    def _update_item_thumbnail(self, item_path: str, result: dict):
        """Updates the thumbnail for a specific item widget."""
        """
        logger.debug(
            f"ObjectListPanel trying update for item: {item_path} with result: {result}"
        )
        """
        clean_path = self._get_clean_path(item_path)
        widget = self._find_widget_by_path(clean_path)
        if widget:
            #  logger.debug(f"Updating thumbnail for item: {clean_path}")
            if result and result.get("path"):
                logger.debug(f"Thumbnail path: {result['path']}")
                pixmap = QPixmap(result["path"])
                if pixmap.isNull():
                    logger.error(f"QPixmap is NULL for path: {result['path']}")
                    widget.set_placeholder_thumbnail()
                else:
                    widget.set_thumbnail(pixmap)
            else:
                widget.set_placeholder_thumbnail()

    def _find_widget_by_path(self, item_path: str) -> ObjectListItemWidget | None:
        """Safely retrieves a widget from the internal map using its clean path."""
        clean_path_key = self._get_clean_path(item_path)
        widget = self._widget_map.get(clean_path_key)
        if widget:
            return widget

    def closeEvent(self, event):
        if hasattr(self, "vm") and self.vm:
            self.vm.unbind_filewatcher_service()
        super().closeEvent(event)
