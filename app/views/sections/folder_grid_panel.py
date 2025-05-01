# app/views/sections/folder_grid_panel.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from typing import Dict
import os

from qfluentwidgets import ScrollArea, InfoBar, InfoBarIcon, InfoBarPosition

from app.viewmodels.folder_grid_vm import FolderGridVM
from app.views.components.breadcrumb_widget import BreadcrumbWidget
from app.views.components.common.flow_grid_widget import FlowGridWidget
from app.models.folder_item_model import FolderItemModel
from app.utils.type_utils import ensure_model_type
from app.utils.logger_utils import logger
from app.core import constants


class FolderGridPanel(QWidget):
    def __init__(self, view_model: FolderGridVM, parent=None):
        super().__init__(parent)
        self.vm = view_model
        self._processing_infobars: Dict[str, InfoBar] = {}
        self._pending_operations_count = 0

        self._setup_ui()
        self._connect_signals()
        self.vm.set_handling_status_changes(True)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 5, 5, 5)
        self.main_layout.setSpacing(5)

        self.breadcrumb_widget = BreadcrumbWidget(self)
        self.main_layout.addWidget(self.breadcrumb_widget)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 1px solid rgba(0,0,0,0.1);")
        self.main_layout.addWidget(line)

        self.scrollArea = ScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.enableTransparentBackground()

        self.gridWidget = FlowGridWidget(self)
        self.scrollArea.setWidget(self.gridWidget)

        self.main_layout.addWidget(self.scrollArea, 1)

    def _connect_signals(self):
        self.vm.displayListChanged.connect(self.gridWidget.setItems)
        self.vm.breadcrumbChanged.connect(self.breadcrumb_widget.set_path)
        self.vm.setItemLoadingState.connect(self._set_item_loading_state)
        self.vm.updateItemDisplay.connect(self._update_item_display)
        self.vm.itemThumbnailNeedsUpdate.connect(self._update_item_thumbnail)
        self.vm.operation_started.connect(self._on_operation_started)
        self.vm.operation_finished.connect(self._on_operation_finished)

        self.breadcrumb_widget.segment_clicked.connect(
            self.vm.navigate_to_breadcrumb_index
        )

        self.gridWidget.itemClicked.connect(self.vm.select_folder_item)
        self.gridWidget.itemDoubleClicked.connect(self.vm.handle_item_double_click)
        self.gridWidget.itemStatusToggled.connect(self._on_item_status_toggled)

    def _on_item_status_toggled(self, path: str, enabled: bool):
        model = self.vm.find_model_by_path(path)
        model = ensure_model_type(model, FolderItemModel)
        if model:
            self.vm.handle_item_status_toggle_request(model, enabled)

    def _on_operation_started(self, path: str, title: str):
        key = self._get_clean_path(path)
        widget = self.gridWidget.findItemWidgetByPath(key)
        if widget:
            widget.set_interactive(False)
            widget.show_loading_overlay(True)

        bar = InfoBar(
            icon=InfoBarIcon.INFORMATION,
            title=title,
            content="Processing...",
            isClosable=False,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=-1,
            parent=self.window(),
        )
        self._processing_infobars[key] = bar
        bar.show()
        self._pending_operations_count += 1

    def _on_operation_finished(self, orig: str, final: str, title, content, success):
        key = self._get_clean_path(final)
        if bar := self._processing_infobars.pop(key, None):
            bar.close()
        widget = self.gridWidget.findItemWidgetByPath(key)
        if widget:
            widget.set_interactive(True)
            widget.show_loading_overlay(False)

        self._pending_operations_count -= 1
        if self._pending_operations_count <= 0:
            self._show_batch_summary()

    def _show_batch_summary(self):
        ok = self.vm._status_manager.get_success_count()
        fail = self.vm._status_manager.get_fail_count()
        pos = InfoBarPosition.BOTTOM_RIGHT
        msg = f"{fail} item(s) failed" if fail else f"{ok} item(s) updated"
        fn = InfoBar.error if fail else InfoBar.success
        fn("Batch Update", msg, parent=self.window(), position=pos)
        self.vm._status_manager.reset_count()

    def _update_item_display(self, path: str, payload: dict):
        widget = self.gridWidget.findItemWidgetByPath(path)
        if not widget:
            return
        widget.update_display(payload)
        new_path = payload.get("path")
        if new_path:
            self.gridWidget.updateItemPath(path, new_path)

    def _update_item_thumbnail(self, path: str, result: dict):
        widget = self.gridWidget.findItemWidgetByPath(path)
        if not widget:
            return
        pixmap = self._load_pixmap_from_result(result)
        if hasattr(widget, "set_thumbnail"):
            widget.set_thumbnail(pixmap)

    def _set_item_loading_state(self, path: str, is_loading: bool):
        widget = self.gridWidget.findItemWidgetByPath(path)
        if widget:
            widget.set_interactive(not is_loading)
            widget.show_loading_overlay(is_loading)

    def _get_clean_path(self, path: str) -> str:
        if not path:
            return ""
        base = os.path.basename(path)
        prefix = constants.DISABLED_PREFIX
        if base.lower().startswith(prefix.lower()):
            base = base[len(prefix) :]
        return os.path.normpath(os.path.join(os.path.dirname(path), base))

    def _load_pixmap_from_result(self, result: dict) -> QPixmap | None:
        if not result:
            return None
        thumb_path = result.get("path")
        status = result.get("status")
        if status not in ["hit", "generated"] or not os.path.exists(thumb_path):
            return None
        try:
            pixmap = QPixmap(thumb_path)
            return pixmap if not pixmap.isNull() else None
        except Exception as e:
            logger.error(f"Failed to load thumbnail: {e}")
            return None

    def closeEvent(self, event):
        if self.vm:
            self.vm.unbind_filewatcher_service()
        super().closeEvent(event)
