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
    TitleLabel,
    TransparentToolButton,
    PushButton,
    VBoxLayout,
    FlowLayout,
    IndeterminateProgressBar,
    BodyLabel,
    RoundMenu,
    IconWidget,
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

        self.empty_state_widget = QWidget(self)
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)

        self.empty_icon = IconWidget(FluentIcon.SEARCH, self.empty_state_widget)
        self.empty_icon.setFixedSize(48, 48)

        self.empty_title_label = TitleLabel("No Objects Found", self.empty_state_widget)
        self.empty_subtitle_label = BodyLabel("This category is empty.", self.empty_state_widget)
        self.empty_subtitle_label.setAlignment(Qt.AlignmentFlag.AlignBaseline | Qt.AlignmentFlag.AlignCenter)
        self.empty_subtitle_label.setWordWrap(True)

        # You can add a button here for a "call to action"
        self.empty_action_button = PushButton("Create New Object")
        self.empty_action_button.setVisible(False) # Hide it by default

        empty_layout.addStretch(1)
        empty_layout.addWidget(self.empty_icon, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title_label, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_subtitle_label, 0, Qt.AlignmentFlag.AlignTop)
        empty_layout.addWidget(self.empty_action_button, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch(1)

        # 3. Shimmer Frame for Loading (No changes here)
        self.shimmer_frame = ShimmerFrame(self)
        self.stack.addWidget(self.list_widget)
        self.stack.addWidget(self.empty_state_widget)
        self.stack.addWidget(self.shimmer_frame)

        # --- Result Bar (Initially Hidden) ---
        self.result_bar_widget = QWidget(self)
        self.result_bar_widget.setObjectName("ResultBar")
        result_bar_layout = QHBoxLayout(self.result_bar_widget)
        result_bar_layout.setContentsMargins(14, 4, 10, 4)

        self.result_label = BodyLabel("...")
        self.clear_filter_button = TransparentToolButton(FluentIcon.CLOSE, self.result_bar_widget)
        self.clear_filter_button.setToolTip("Clear all filters and search")

        result_bar_layout.addWidget(self.result_label, 1)
        result_bar_layout.addWidget(self.clear_filter_button)
        self.result_bar_widget.setVisible(False) # Hide it by default

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)  # Use fluent VBoxLayout
        main_layout.setContentsMargins(0, 10, 0, 5)
        main_layout.setSpacing(6)
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.result_bar_widget)
        main_layout.addWidget(self.bulk_action_widget)
        main_layout.addWidget(self.stack, 1)

    def _connect_signals(self):
        """Connects this panel's widgets and slots to the ViewModel."""
        # ViewModel -> View connections
        self.view_model.items_updated.connect(self._on_items_updated)

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
        self.view_model.empty_state_changed.connect(self._on_empty_state_changed)
        self.view_model.available_filters_changed.connect(self._on_available_filters_changed)
        self.view_model.filter_state_changed.connect(self._on_filter_state_changed)
        self.view_model.clear_search_text.connect(self.search_bar.clear)
        self.clear_filter_button.clicked.connect(self.view_model.clear_all_filters_and_search)

        # --- Connect UI widget actions to ViewModel slots ---
        self.search_bar.textChanged.connect(self.view_model.on_search_query_changed)
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
        """
        Repopulates the list view and intelligently updates the view state
        (list, empty, or no results).
        """
        self.list_widget.clear()
        self._item_widgets.clear()

        # --- UI Feedback Logic ---
        if not items_data:
            # If no items are available, show the empty state widget.
            return
        # -------------------------------------------

        # If there are items, show the list widget.
        self.stack.setCurrentWidget(self.list_widget)

        for item_data in items_data:
            list_item = QListWidgetItem(self.list_widget)
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
            action = QAction("No Filters Available", self)
            action.setEnabled(False)
            self.filter_menu.addAction(action)
            return

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create filter controls dynamically
        for name, options in filter_options.items():
            layout.addWidget(BodyLabel(name))
            combo = ComboBox()
            combo.addItems(["All"] + options)

            # --- State Persistence Logic ---
            # Check if there is an active filter for this combobox
            # The key in active_filters is lowercase (e.g., 'rarity')
            active_value = self.view_model.active_filters.get(name.lower())
            if active_value:
                combo.setCurrentText(active_value)
            # -----------------------------

            layout.addWidget(combo)
            self.filter_widgets[name] = combo

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
                # Use lowercase for the key to match model attributes
                active_filters[name.lower()] = value

        # Call the ViewModel method we implemented
        self.view_model.set_filters(active_filters)
        self.filter_menu.close()

    def _on_reset_filters(self):
        """Resets all filter widgets to 'All' and applies."""
        for widget in self.filter_widgets.values():
            widget.setCurrentIndex(0)

        # Call the ViewModel method to clear the filters
        self.view_model.clear_filters()
        self.filter_menu.close()


    def _on_empty_state_changed(self, title: str, subtitle: str):
        """Updates the text on the empty state widget and displays it."""
        self.empty_title_label.setText(title)
        self.empty_subtitle_label.setText(subtitle)

        # Example of contextual icon/button
        if "filter" in subtitle or "criteria" in subtitle:
            self.empty_icon.setIcon(FluentIcon.FILTER)
            self.empty_action_button.setVisible(False)
        else:
            self.empty_icon.setIcon(FluentIcon.SEARCH_MIRROR)
            self.empty_action_button.setVisible(True) # Show "Create" button for true empty states

        self.stack.setCurrentWidget(self.empty_state_widget)

    def _on_filter_state_changed(self, show_bar: bool, count: int):
        """Shows or hides the result bar based on the filter state."""
        if show_bar:
            plural = "s" if count > 1 else ""
            self.result_label.setText(f"{count} result{plural} found")

        self.result_bar_widget.setVisible(show_bar)