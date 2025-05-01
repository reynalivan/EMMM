# app/views/sections/object_list_panel.py

import os
from typing import Optional, Dict
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from qfluentwidgets import InfoBar, InfoBarIcon, InfoBarPosition

from app.viewmodels.object_list_vm import ObjectListVM
from app.views.components.object_list_item_widget import ObjectListItemWidget
from app.models.object_item_model import ObjectItemModel
from app.utils.logger_utils import logger
from app.core import constants


class ObjectListPanel(QWidget):
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
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ObjectListWidget")
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setStyleSheet(
            "QListWidget { border: none; background: transparent; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)

    def _connect_signals(self):
        self.vm.displayListChanged.connect(self._update_display_list)
        self.vm.loadingStateChanged.connect(self.list_widget.setDisabled)
        self.vm.itemThumbnailNeedsUpdate.connect(self._update_thumbnail)
        self.vm.setItemLoadingState.connect(self._set_item_loading_state)
        self.vm.updateItemDisplay.connect(self._update_item_display)
        self.vm.operation_started.connect(self._on_operation_started)
        self.vm.operation_finished.connect(self._on_operation_finished)
        self.vm.showError.connect(self._show_error)

        self.list_widget.itemClicked.connect(self._on_item_clicked)

    def _update_display_list(self, items: list):
        self.list_widget.clear()
        self._widget_map.clear()

        for item_model in items:
            if not isinstance(item_model, ObjectItemModel):
                continue

            widget = ObjectListItemWidget(item_model)
            list_item = QListWidgetItem()
            list_item.setSizeHint(widget.sizeHint())

            clean_key = self._get_clean_path(item_model.path)
            self._widget_map[clean_key] = widget

            # Connect switch
            widget.status_toggled.connect(
                lambda checked, m=item_model: self.vm.handle_item_status_toggle_request(
                    m, checked
                )
            )

            # TODO: Connect bulk checkbox if needed
            # widget.bulk_selection_changed.connect(...)

            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)
            self.vm.request_thumbnail_for(item_model)

    def _on_item_clicked(self, item: QListWidgetItem):
        widget = self.list_widget.itemWidget(item)
        if isinstance(widget, ObjectListItemWidget):
            self.vm.select_object_item(widget.get_item_model())

    def _update_thumbnail(self, path: str, result: dict):
        widget = self._widget_map.get(self._get_clean_path(path))
        if widget:
            if result and result.get("path"):
                pixmap = QPixmap(result["path"])
                if pixmap.isNull():
                    widget.set_placeholder_thumbnail()
                else:
                    widget.set_thumbnail(pixmap)
            else:
                widget.set_placeholder_thumbnail()

    def _set_item_loading_state(self, path: str, is_loading: bool):
        widget = self._widget_map.get(self._get_clean_path(path))
        if widget:
            widget.set_interactive(not is_loading)
            widget.show_loading_overlay(is_loading)

    def _update_item_display(self, old_path: str, payload: dict):
        new_path = payload.get("path")
        if not new_path:
            return

        old_key = self._get_clean_path(old_path)
        new_key = self._get_clean_path(new_path)

        widget = self._widget_map.pop(old_key, None)
        if widget:
            widget.update_display(payload)
            self._widget_map[new_key] = widget

    def _on_operation_started(self, path: str, title: str):
        widget = self._widget_map.get(self._get_clean_path(path))
        if widget:
            widget.set_interactive(False)
            widget.show_loading_overlay(True)
        self._pending_operations_count += 1

    def _on_operation_finished(self, orig, final, title, content, success):
        widget = self._widget_map.get(
            self._get_clean_path(final)
        ) or self._widget_map.get(self._get_clean_path(orig))

        if widget:
            widget.set_interactive(True)
            widget.show_loading_overlay(False)

        self._pending_operations_count -= 1
        if self._pending_operations_count <= 0:
            self._show_batch_summary()

    def _show_batch_summary(self):
        success = self.vm._status_manager.get_success_count()
        failed = self.vm._status_manager.get_fail_count()
        msg = (
            f"{success} updated, {failed} failed"
            if failed
            else f"{success} updated successfully"
        )
        InfoBar.success(
            "Batch Result",
            msg,
            parent=self.window(),
            position=InfoBarPosition.BOTTOM_RIGHT,
        )
        self.vm._status_manager.reset_count()

    def _show_error(self, title, msg):
        InfoBar.error(
            title, msg, parent=self.window(), position=InfoBarPosition.BOTTOM_RIGHT
        )

    def _get_clean_path(self, path: str) -> str:
        if not path:
            return ""
        name = os.path.basename(path)
        if name.lower().startswith(constants.DISABLED_PREFIX.lower()):
            name = name[len(constants.DISABLED_PREFIX) :]
        return os.path.normpath(os.path.join(os.path.dirname(path), name))

    def closeEvent(self, event):
        if self.vm:
            self.vm.unbind_filewatcher_service()
        super().closeEvent(event)
