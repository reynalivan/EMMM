# app/views/sections/folder_grid_panel.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from typing import Dict
import os
from app.views.dialogs.filter_dialog import FilterDialog
from qfluentwidgets import (
    ScrollArea,
    InfoBar,
    InfoBarIcon,
    InfoBarPosition,
    SearchLineEdit,
    SubtitleLabel,
    TransparentToolButton,
    DropDownPushButton,
    FluentIcon as FIF,
)
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

        self._setup_ui()
        self._connect_signals()
        self.vm.set_handling_status_changes(True)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 5)
        self.main_layout.setSpacing(6)

        # === Top bar (Search + Filter + Clear) ===
        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)
        top_bar.setContentsMargins(14, 1, 14, 1)

        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("Search...")
        self.search_box.textChanged.connect(self._on_search_changed)

        self.filter_btn = DropDownPushButton(FIF.FILTER, "Filter", self)
        self.filter_btn.clicked.connect(self._on_filter_clicked)

        top_bar.addWidget(self.search_box)
        top_bar.addWidget(self.filter_btn)
        top_bar.addStretch()
        self.main_layout.addLayout(top_bar)

        # === Result summary bar ===
        self.result_summary_bar = QHBoxLayout()
        self.result_summary_bar.setContentsMargins(14, 1, 14, 1)
        self.result_summary_bar.setSpacing(8)

        self.result_label = SubtitleLabel("", self)
        self.result_label.setTextColor("gray")
        self.result_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )

        self.clear_all_btn = TransparentToolButton(FIF.CLOSE, self)
        self.clear_all_btn.setToolTip("Clear filters and search")
        self.clear_all_btn.clicked.connect(self._on_clear_all)

        self.result_summary_bar.addWidget(self.result_label)
        self.result_summary_bar.addStretch()
        self.result_summary_bar.addWidget(self.clear_all_btn)

        # Initially hidden
        self.result_label.setVisible(False)
        self.clear_all_btn.setVisible(False)

        # === Breadcrumb ===
        self.breadcrumb_widget = BreadcrumbWidget(self)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 1px solid rgba(0,0,0,0.1);")

        self.main_layout.addLayout(self.result_summary_bar)
        self.main_layout.addWidget(self.breadcrumb_widget)
        self.main_layout.addWidget(line)

        # === Scrollable grid ===
        self.scrollArea = ScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.enableTransparentBackground()

        self.gridWidget = FlowGridWidget(self)
        self.scrollArea.setWidget(self.gridWidget)
        self.main_layout.addWidget(self.scrollArea, 1)

    def _connect_signals(self):
        self.vm.resultSummaryUpdated.connect(self._update_result_summary)
        self.vm.resetFilterState.connect(self.reset_filters_and_search)
        self.vm.breadcrumbChanged.connect(self.breadcrumb_widget.set_path)
        self.vm.setItemLoadingState.connect(self._set_item_loading_state)
        self.vm.updateItemDisplay.connect(self._update_item_display)
        self.vm.itemThumbnailNeedsUpdate.connect(self.request_thumbnail_for)
        self.vm.operation_started.connect(self._on_operation_started)
        self.vm.operation_finished.connect(self._on_operation_finished)
        self.vm.batchOperationSummaryReady.connect(self._show_batch_summary)
        self.vm.filterSummaryChanged.connect(self._update_result_summary)
        self.vm.filterButtonStateChanged.connect(self._update_filter_button_state)
        self.gridWidget.visiblePathsRequested.connect(
            self.vm.handle_visible_thumbnail_requests
        )
        self.breadcrumb_widget.segment_clicked.connect(
            self.vm.navigate_to_breadcrumb_index
        )
        self.gridWidget.scrollNearBottom.connect(self.vm.try_load_more)

        self.vm.displayListChanged.connect(self.gridWidget.updateItems)

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

    def _on_operation_finished(self, orig: str, final: str, title, content, success):
        key = self._get_clean_path(final)
        if bar := self._processing_infobars.pop(key, None):
            bar.close()
        widget = self.gridWidget.findItemWidgetByPath(key)
        if widget:
            widget.set_interactive(True)
            widget.show_loading_overlay(False)

    def _show_batch_summary(self, msg: str, is_error: bool):
        fn = InfoBar.error if is_error else InfoBar.success
        fn(
            "Batch Update",
            msg,
            parent=self.window(),
            position=InfoBarPosition.BOTTOM_RIGHT,
        )

    def _update_item_display(self, path: str, payload: dict):
        widget = self.gridWidget.findItemWidgetByPath(path)
        if not widget:
            return
        widget.update_display(payload)
        new_path = payload.get("path")
        if new_path:
            self.gridWidget.updateItemPath(path, new_path)

    def request_thumbnail_for(self, path: str, result: dict):
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

    def _on_search_changed(self, text: str):
        self.vm.apply_filter_text(text)

    def _on_clear_all(self):
        self.search_box.clear()
        self.vm.clear_all_metadata_filters()
        self.vm._filter_and_sort()
        self._update_filter_button_state()

    def _update_result_summary(self, label: str, visible: bool):
        self.result_label.setVisible(visible)
        self.result_label.setText(label)
        self.clear_all_btn.setVisible(visible)

    def _on_filter_clicked(self):
        filters_metadata = self.vm.get_metadata_filter_options()
        active = (
            self.vm._metadata_filters if hasattr(self.vm, "_metadata_filters") else {}
        )

        dialog = FilterDialog(
            filters=filters_metadata,
            active_filters=active,
            apply_callback=self._on_filter_dialog_applied,
            parent=self,
        )
        dialog.exec()

    def _on_filter_dialog_applied(self, new_filters: dict[str, set[str]]):
        self.vm.set_metadata_filters(new_filters)
        self.vm._filter_and_sort()
        self._update_filter_button_state()

    def _update_filter_button_state(self):
        active_count = sum(len(v) for v in self.vm._filter_state.metadata.values())
        self.filter_btn.setText(
            f"Filter ({active_count})" if active_count else "Filter"
        )
        self.clear_all_btn.setVisible(active_count > 0 or self.search_box.text() != "")

    def reset_filters_and_search(self):
        self.search_box.clear()
        self.result_label.setText("")
        self.result_label.setVisible(False)
        self.clear_all_btn.setVisible(False)
        self.vm.clear_all_metadata_filters()
        self.vm.apply_filter_text("")
        self._update_filter_button_state()

    def closeEvent(self, event):
        if self.vm:
            self.vm.unbind_filewatcher()
        super().closeEvent(event)
