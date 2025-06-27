# app/views/sections/objectlist_panel.py
from typing import Dict

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QListWidgetItem,
    QSizePolicy,
    QWidget,
    QStackedWidget,
    QListWidget,
    QVBoxLayout,
    QHBoxLayout,
)
from PyQt6.QtGui import QAction
from qfluentwidgets import (
    FluentIcon,
    SearchLineEdit,
    DropDownToolButton,
    SubtitleLabel,
    PushButton,
    VBoxLayout,
    FlowLayout,
    IndeterminateProgressBar,
    BodyLabel,
    RoundMenu,
    PrimaryPushButton,
    ComboBox,
    themeColor,
)

from app.utils.logger_utils import logger
from app.viewmodels.mod_list_vm import ModListViewModel
from app.views.components.objectlist_widget import ObjectListItemWidget
from app.views.components.common.shimmer_frame import ShimmerFrame
from app.services.thumbnail_service import ThumbnailService
from pathlib import Path

# Import other necessary components...


class ObjectListPanel(QWidget):
    """The UI panel that displays the list of object items (characters, weapons, etc.)."""

    # Custom signal to notify the main window that a new object should be set as active.
    item_selected = pyqtSignal(object)

    def __init__(self, viewmodel: ModListViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = viewmodel
        self._item_widgets: Dict[str, QListWidgetItem] = {}

        self.filter_menu = None
        self.filter_widgets = {}  # To store created filter ComboBoxes
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initializes all UI components for this panel using fluent layouts."""

        # --- Toolbar ---
        toolbar_layout = FlowLayout()  # Use fluent FlowLayout
        toolbar_layout.setContentsMargins(14, 1, 14, 1)
        toolbar_layout.setHorizontalSpacing(6)
        # set minimumSize toolbar layout
        self.search_bar = SearchLineEdit(self)
        self.search_bar.setPlaceholderText("Search objects...")

        self.filter_btn = DropDownToolButton(FluentIcon.FILTER, self)
        self.filter_btn.setToolTip("Filter")
        self.filter_menu = RoundMenu(parent=self)
        self.filter_btn.setMenu(self.filter_menu)

        toolbar_layout.addWidget(self.search_bar)
        toolbar_layout.addWidget(self.filter_btn)

        # --- Bulk Action Toolbar (Initially Hidden) ---
        self.bulk_action_widget = QWidget(self)
        bulk_action_layout = FlowLayout(self.bulk_action_widget, isTight=True)
        bulk_action_layout.setContentsMargins(10, 0, 10, 5)

        self.selection_label = SubtitleLabel("0 selected")
        self.select_all_button = PushButton("Select All")
        self.clear_selection_button = PushButton("Clear Selection")
        self.enable_selected_button = PushButton("Enable Selected")
        self.disable_selected_button = PushButton("Disable Selected")

        # --- Content Stack (for switching between states) ---
        self.stack = QStackedWidget(self)

        # 1. Main List Area
        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("ObjectListWidget")
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        border_color = themeColor().name()
        self.list_widget.setStyleSheet(
            "QListWidget { border: none; background: transparent; padding-right: 5px; }"
            "QListWidget::item { border-bottom: 1px solid rgba(255, 255, 255, 0.05); }"
            f"""QListWidget::item:selected {{ background: rgba(255, 255, 255, 0.08); border-left: 4px solid {border_color}; }}"""
        )

        # 2. Empty/No Results Label
        self.empty_label = SubtitleLabel("No objects found.", self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 3. Shimmer Frame for Loading
        self.shimmer_frame = ShimmerFrame(self)

        self.stack.addWidget(self.list_widget)
        self.stack.addWidget(self.empty_label)
        self.stack.addWidget(self.shimmer_frame)

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)  # Use fluent VBoxLayout
        main_layout.setContentsMargins(0, 10, 0, 5)
        main_layout.setSpacing(6)
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.bulk_action_widget)
        main_layout.addWidget(self.stack, 1)

    def _connect_signals(self):
        """Connects this panel's widgets and slots to the ViewModel."""
        # ViewModel -> View connections
        self.view_model.items_updated.connect(self._on_items_updated)
        # ... other vm -> view connections

        # View -> ViewModel connections
        # self.search_bar.textChanged.connect(self.view_model.on_search_query_changed)
        # ... other view -> vm connections

        # --- Connect ViewModel signals to this panel's slots ---
        self.view_model.loading_started.connect(self._on_loading_started)
        self.view_model.loading_finished.connect(self._on_loading_finished)
        self.view_model.items_updated.connect(self._on_items_updated)
        self.view_model.item_needs_update.connect(self._on_item_needs_update)
        self.view_model.item_processing_started.connect(
            self._on_item_processing_started
        )
        self.view_model.item_processing_finished.connect(
            self._on_item_processing_finished
        )
        self.view_model.selection_changed.connect(self._on_selection_changed)
        self.view_model.bulk_operation_started.connect(self._on_bulk_action_started)
        self.view_model.bulk_operation_finished.connect(self._on_bulk_action_completed)
        self.view_model.active_selection_changed.connect(
            self._on_active_selection_changed
        )
        self.view_model.available_filters_changed.connect(self._on_available_filters_changed)

        # --- Connect UI widget actions to ViewModel slots ---
        # self.search_bar.textChanged.connect(self.view_model.on_search_query_changed)
        # self.create_button.clicked.connect(self._on_create_object_requested)

    # --- SLOTS (Responding to ViewModel Signals) ---

    def _on_loading_started(self):
        """Flow 2.2: Clears the view and shows the loading shimmer."""
        self.list_widget.clear()
        self._item_widgets.clear()
        self.stack.setCurrentWidget(self.shimmer_frame)

    def _on_loading_finished(self):
        """Flow 2.2: Hides the loading shimmer."""
        # self.shimmer_frame.stop_shimmer()
        pass

    def _on_items_updated(self, items_data: dict):
        """Repopulates the list view with new data dictionaries."""
        self.list_widget.clear()
        self._item_widgets.clear()

        if not items_data:
            self.stack.setCurrentWidget(self.empty_label)
            return

        self.stack.setCurrentWidget(self.list_widget)

        for item_data in items_data:
            list_item = QListWidgetItem(self.list_widget)
            # Pass item_data (dict) ke constructor widget
            item_widget = ObjectListItemWidget(
                item_data=item_data,
                viewmodel=self.view_model,
            )
            item_widget.item_selected.connect(self._on_list_item_clicked)

            list_item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)

            self._item_widgets[item_data["id"]] = list_item

    def _on_list_item_clicked(self, item_data: dict):
        """Forwards the item selection event upwards to the main window."""
        # 1. FIX: Tell the ViewModel which item is now the active one so it can be remembered.
        item_id = item_data.get("id")
        self.view_model.set_active_selection(item_id)

        # 2. Forward the selection to the main window to update the foldergrid.
        self.item_selected.emit(item_data)

    def _on_item_needs_update(self, item_data: dict):
        """Flow 2.2 Stage 2: Finds and redraws a single widget for a targeted update."""
        item_id = item_data.get("id") or ""
        list_or_item_widget = self._item_widgets.get(item_id)

        if not list_or_item_widget:
            return

        if isinstance(list_or_item_widget, QListWidgetItem):
            widget = self.list_widget.itemWidget(list_or_item_widget)
        else:
            widget = list_or_item_widget

        if isinstance(widget, ObjectListItemWidget):
            widget.set_data(item_data)

    def _on_active_selection_changed(self, selected_item_id: str | None):
        """
        Responds to selection changes from the ViewModel, applying the
        selection to the correct QListWidgetItem.
        """
        if not selected_item_id:
            self.list_widget.clearSelection()
            return

        # Find the QListWidgetItem associated with the given ID
        list_item_to_select = self._item_widgets.get(selected_item_id)

        if list_item_to_select:
            # Programmatically set the current item in the QListWidget
            self.list_widget.setCurrentItem(list_item_to_select)
        else:
            # If the item is not found (e.g., filtered out), clear selection
            self.list_widget.clearSelection()

    def _on_item_processing_started(self, item_id: str):
        """Flow 3.1 & 4.2: Shows a processing state on a specific widget."""
        # widget = self._item_widgets.get(item_id)
        # if widget: widget.show_processing_state(True)
        pass

    def _on_item_processing_finished(self, item_id: str, success: bool):
        """Flow 3.1 & 4.2: Hides the processing state on a specific widget."""
        # widget = self._item_widgets.get(item_id)
        # if widget: widget.show_processing_state(False)
        pass

    def _on_selection_changed(self, has_selection: bool):
        """Flow 3.2: Enables or disables bulk action buttons based on selection."""
        # self.bulk_enable_button.setEnabled(has_selection)
        pass

    def _on_bulk_action_started(self):
        """Flow 3.2: Disables UI controls during a bulk operation."""
        # Disable search, filter, create, and all item checkboxes.
        pass

    def _on_bulk_action_completed(self, failed_items: list):
        """Flow 3.2: Re-enables UI controls after a bulk operation is finished."""
        # Re-enable all controls disabled in the method above.
        pass

    # --- Private Slots (Handling child widget signals) ---
    def _on_list_item_selected(self, item: object):
        """
        Flow 2.3: Forwards the item selection event upwards to the main window
        by emitting this panel's own signal.
        """
        self.item_selected.emit(item)
        pass

    # --- UI EVENT HANDLERS (Forwarding to ViewModel) ---
    def _on_create_object_requested(self):
        """Flow 4.1.B: Shows the creation choice dialog and forwards to the ViewModel."""
        # Show a dialog with "Manual" and "Sync from DB" options.
        # Based on the choice, call the appropriate method on self.view_model.
        pass

    def _clear_layout(self, layout):
        """Helper function to remove all widgets from a layout."""
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _on_available_filters_changed(self, filter_options: dict):
        """Clears and rebuilds the filter menu UI controls dynamically."""
        self.filter_menu.clear()
        self.filter_widgets.clear()

        if not filter_options:
            # Add a disabled action if there are no filters
            action = QAction("No Filters Available", self)
            action.setEnabled(False)
            self.filter_menu.addAction(action)
            return

        # Create a container widget and layout for our controls
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create filter controls dynamically
        for name, options in filter_options.items():
            layout.addWidget(BodyLabel(name))
            combo = ComboBox()
            combo.addItems(["All"] + options)
            layout.addWidget(combo)
            self.filter_widgets[name] = combo

        # Add Apply and Reset buttons
        layout.addSpacing(10)
        button_layout = QHBoxLayout()
        reset_button = PushButton("Reset")
        apply_button = PrimaryPushButton("Apply")
        button_layout.addWidget(reset_button)
        button_layout.addWidget(apply_button)
        layout.addLayout(button_layout)

        # Connect button signals
        reset_button.clicked.connect(self._on_reset_filters)
        apply_button.clicked.connect(self._on_apply_filters)

        self.filter_menu.addWidget(container, selectable=False)

    def _on_apply_filters(self):
        """Collects filter values and sends them to the ViewModel."""
        active_filters = {}
        for name, widget in self.filter_widgets.items():
            value = widget.currentText()
            if value != "All":
                active_filters[name.lower()] = value

        logger.info(f"Applying filters: {active_filters}")
        # self.view_model.set_filters(active_filters) # This method needs to be implemented in VM
        self.filter_menu.close()

    def _on_reset_filters(self):
        """Resets all filter widgets to 'All' and applies."""
        for widget in self.filter_widgets.values():
            widget.setCurrentIndex(0)
        self._on_apply_filters()