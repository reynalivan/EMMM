# app/views/sections/folder_grid_panel.py

import os
from typing import Dict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, QSize, QEasingCurve
from qfluentwidgets import Flyout, InfoBarIcon
from PyQt6.QtGui import QPixmap
from app.viewmodels.folder_grid_vm import FolderGridVM
from app.views.components.breadcrumb_widget import BreadcrumbWidget
from app.utils.type_utils import ensure_model_type
from app.models.folder_item_model import FolderItemModel

# Import the custom grid widget and Fluent ScrollArea
from app.views.components.common.flow_grid_widget import FlowGridWidget
from qfluentwidgets import ScrollArea, ScrollBar, InfoBar, InfoBarIcon, InfoBarPosition

# Import logger only if error logging is kept
from app.utils.logger_utils import logger
from app.core import constants


class FolderGridPanel(QWidget):
    """Panel containing the breadcrumb and the main grid view for folders/mods."""

    def __init__(self, view_model: FolderGridVM, parent=None):
        super().__init__(parent)
        self.vm = view_model
        self.vm.set_handling_status_changes(True)
        self.vm.setItemLoadingState.connect(self._set_item_loading_state)
        self.vm.updateItemDisplay.connect(self._update_item_display)

        self._processing_infobars: Dict[str, InfoBar] = {}
        self._pending_operations_count = 0
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
        self.vm.set_breadcrumb_widget(self.breadcrumb_widget)

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

            # VM -> Panel (InfoBar Notifications)
            self.vm.operation_started.connect(self._on_operation_started)
            self.vm.operation_finished.connect(self._on_operation_finished)

            # VM -> Panel (Specific Item UI Control)
            self.vm.itemThumbnailNeedsUpdate.connect(self._update_item_thumbnail)
            self.vm.setItemLoadingState.connect(self._set_item_loading_state)
            self.vm.updateItemDisplay.connect(self._update_specific_item)
            self.gridWidget.itemClicked.connect(self.vm.select_folder_item)
            self.gridWidget.itemDoubleClicked.connect(self.vm.handle_item_double_click)
            self.gridWidget.itemStatusToggled.connect(self._on_item_status_toggled)
            # self.gridWidget.itemStatusToggled.connect(
            #    self.vm.handle_item_status_toggle_request
            # )
            # TODO: Connect other signals from gridWidget (itemStatusToggled etc.) to VM slots

        except AttributeError as e:
            # Keep error logging as it's essential for debugging connection issues
            logger.error(
                f"Error connecting signals in FolderGridPanel: {e}", exc_info=True
            )

    def _update_specific_item(self, item_path: str, update_data: dict):
        """Finds widget by path and updates its display based on data from VM."""
        # logger.debug(f"FolderGridPanel trying update for item: {item_path} with data: {update_data}") # Keep lean
        widget = self.gridWidget.findItemWidgetByPath(item_path)  # Gunakan helper baru

        if not widget:
            # logger.warning(f"Panel: Widget for path {item_path} not found for update.") # Keep lean
            return

        # Logika percabangan berdasarkan update_data (sama seperti ObjectListPanel)
        if "model_data" in update_data:
            model_data = update_data["model_data"]
            new_status = model_data.get("status", False)

            widget.status_switch.blockSignals(True)
            widget.status_switch.setChecked(new_status)
            widget.status_switch.blockSignals(False)
            widget.status_switch.setOnText("Enabled")
            widget.status_switch.setOffText("Disabled")
            logger.debug(f"Panel updated widget display for {item_path}")

        elif "path" in update_data and "status" in update_data:
            # Handle thumbnail update (jika FolderGridItemWidget punya set_thumbnail)
            thumbnail_path = update_data.get("path")
            status = update_data.get("status")
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
                    logger.error(
                        f"Panel: Error creating QPixmap for {thumbnail_path}: {e}"
                    )
                    pixmap = None
            # Pastikan widget punya method set_thumbnail
            if hasattr(widget, "set_thumbnail"):
                widget.set_thumbnail(pixmap)
            # else: logger.warning(f"Widget for {item_path} missing set_thumbnail method.") # Keep lean
        else:
            logger.warning(
                f"Panel received unknown update data for {item_path}: {update_data}"
            )

    def _on_operation_started(self, item_path: str, title: str):
        """Mark item as loading and lock interaction."""
        clean_path_key = self._get_clean_path(item_path)
        if not clean_path_key:
            return

        if existing_bar := self._processing_infobars.pop(clean_path_key, None):
            existing_bar.close()

        widget = self.gridWidget.findItemWidgetByPath(clean_path_key)
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

        widget = self.gridWidget.findItemWidgetByPath(clean_final_path)
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

    def _on_item_status_toggled(self, item_path: str, enabled: bool):
        """Handles when an item toggles its enabled/disabled switch."""
        model = self.vm.find_model_by_path(item_path)
        model = ensure_model_type(model, FolderItemModel)  # Safe guard here
        if model:
            self.vm.handle_item_status_toggle_request(model, enabled)
        else:
            logger.warning(f"FolderGridPanel: Invalid model type for path {item_path}")

    def _set_item_loading_state(self, item_path: str, is_loading: bool):
        widget = self.gridWidget.findItemWidgetByPath(item_path)
        if widget:
            widget.set_interactive(not is_loading)  # Disable/enable interaksi user
            widget.show_loading_overlay(is_loading)  # Tampilkan overlay loading

    def _update_item_display(self, item_path: str, payload: dict):
        widget = self.gridWidget.findItemWidgetByPath(item_path)
        if widget:
            widget.update_display(payload)

            # --- PENTING: Update path mapping registry ---
            new_path = payload.get("path")
            if new_path:
                self.gridWidget.updateItemPath(item_path, new_path)

    def _update_item_thumbnail(self, item_path: str, thumb_result: dict):
        """Updates the thumbnail of a specific item widget."""
        # Find widget using the original item path from the signal
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

    def closeEvent(self, event):
        if hasattr(self, "vm") and self.vm:
            self.vm.unbind_filewatcher_service()
        super().closeEvent(event)
