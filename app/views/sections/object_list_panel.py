# app/views/sections/object_list_panel.py
import os
from typing import Optional, Dict
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
)
from qfluentwidgets import (
    DropDownPushButton,
    InfoBar,
    InfoBarPosition,
    FluentIcon as FIF,
    TransparentToolButton,
    SearchLineEdit,
    SubtitleLabel,
)

from app.viewmodels.object_list_vm import ObjectListVM
from app.views.components.object_list_item_widget import ObjectListItemWidget
from app.models.object_item_model import ObjectItemModel
from app.views.dialogs.filter_dialog import FilterDialog
from app.utils.logger_utils import logger
from app.core import constants


class ObjectListPanel(QWidget):
    def __init__(self, view_model: ObjectListVM, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.vm = view_model
        self._widget_map: Dict[str, ObjectListItemWidget] = {}
        self._processing_infobars: Dict[str, InfoBar] = {}
        self._pending_operations_count = 0

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(10, 10, 10, 0)
        top_bar_layout.setSpacing(6)

        # Search bar
        self.search_bar = SearchLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self._on_search_changed)
        top_bar_layout.addWidget(self.search_bar, 1)

        # Filter button
        self.filter_menu = DropDownPushButton(FIF.FILTER, "Filter", self)
        self.filter_menu.clicked.connect(self._on_filter_button_clicked)
        top_bar_layout.addWidget(self.filter_menu)
        top_bar_layout.addStretch()

        # Result summary bar
        self.result_summary_bar = QHBoxLayout()
        self.result_summary_bar.setContentsMargins(10, 0, 10, 0)
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

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ObjectListWidget")
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setStyleSheet(
            "QListWidget { border: none; background: transparent; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_bar_layout)
        layout.addLayout(self.result_summary_bar)
        layout.addWidget(self.list_widget)

    def _connect_signals(self):
        self.vm.displayListChanged.connect(self._update_display_list)
        self.vm.loadingStateChanged.connect(self.list_widget.setDisabled)
        self.vm.itemThumbnailNeedsUpdate.connect(self._update_thumbnail)
        self.vm.setItemLoadingState.connect(self._set_item_loading_state)
        self.vm.updateItemDisplay.connect(self._update_item_display)
        self.vm.operation_started.connect(self._on_operation_started)
        self.vm.operation_finished.connect(self._on_operation_finished)
        self.vm.batchSummaryReady.connect(self._show_batch_summary)
        self.vm.showError.connect(self._show_error)
        self.vm.filterButtonStateChanged.connect(self._update_filter_button_text)
        self.vm.resultSummaryUpdated.connect(self._update_result_label)
        self.list_widget.itemClicked.connect(self._on_item_clicked)

    def _on_filter_button_clicked(self):
        filters_metadata = self.vm.get_metadata_filter_options()
        active = self.vm._metadata_filters
        dialog = FilterDialog(
            filters=filters_metadata,
            active_filters=active,
            apply_callback=self._on_filter_dialog_applied,
            parent=self,
        )
        dialog.exec()

    def _on_filters_applied(self, result: dict[str, set[str]]):
        self.vm.set_metadata_filters(result)

    def _on_filter_dialog_applied(self, new_filters: dict[str, set[str]]):
        self.vm.set_metadata_filters(new_filters)
        self.vm._filter_and_sort()
        # optionally update UI (e.g., chip count, label text)

    def _on_clear_all(self):
        self.vm.clear_all_filters_and_search()
        self.search_bar.setText("")

    def _update_display_list(self, items: list):
        """Update list view with filtered and sorted items."""
        self.list_widget.clear()
        self._widget_map.clear()

        for item_model in items:
            if not isinstance(item_model, ObjectItemModel):
                continue

            widget = ObjectListItemWidget(item_model)
            list_item = QListWidgetItem()
            list_item.setSizeHint(widget.sizeHint())

            self._widget_map[self._get_clean_path(item_model.path)] = widget

            # Connect toggle signal
            widget.status_toggled.connect(
                lambda checked, m=item_model: self.vm.handle_item_status_toggle_request(
                    m, checked
                )
            )

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
            pixmap_path = result.get("path")
            if pixmap_path and QPixmap(pixmap_path).isNull() is False:
                widget.set_thumbnail(QPixmap(pixmap_path))
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

    def _show_batch_summary(self, result: dict[str, int]):
        if not result:
            return
        success = result.get("success", 0)
        failed = result.get("failed", 0)
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

    def _on_search_changed(self, text: str):
        self.vm.apply_filter_text(text.strip())  # or current status filter if needed

    def closeEvent(self, event):
        if self.vm:
            self.vm.unbind_filewatcher()
        super().closeEvent(event)

    def _update_filter_button_text(self, count: int):
        self.filter_menu.setText(f"Filter ({count})" if count else "Filter")

    def _update_result_label(self, msg: str):
        is_visible = bool(msg)
        self.result_label.setVisible(is_visible)
        self.clear_all_btn.setVisible(is_visible)
        self.result_label.setText(msg)
