# app/views/sections/objectlist_panel.py
from typing import Dict

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QStackedWidget, QListWidget

from qfluentwidgets import (
    FluentIcon,
    SearchLineEdit,
    DropDownPushButton,
    SubtitleLabel,
    PushButton,
    VBoxLayout,
    FlowLayout,
    IndeterminateProgressBar,
)

from app.viewmodels.mod_list_vm import ModListViewModel
from app.views.components.objectlist_widget import ObjectListItemWidget
from app.views.components.common.shimmer_frame import ShimmerFrame

# Import other necessary components...


class ObjectListPanel(QWidget):
    """The UI panel that displays the list of object items (characters, weapons, etc.)."""

    # Custom signal to notify the main window that a new object should be set as active.
    item_selected = pyqtSignal(object)

    def __init__(self, viewmodel: ModListViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = viewmodel

        # Maps item_id to its widget for quick access
        self._item_widgets: Dict[str, QWidget] = {}

        self._init_ui()
        self._connect_signals_to_viewmodel()

    def _init_ui(self):
        """Initializes all UI components for this panel using fluent layouts."""

        # --- Toolbar ---
        toolbar_layout = FlowLayout()  # Use fluent FlowLayout
        toolbar_layout.setContentsMargins(10, 10, 10, 5)
        toolbar_layout.setHorizontalSpacing(10)
        # set minimumSize toolbar layout
        self.search_bar = SearchLineEdit(self)
        self.search_bar.setPlaceholderText("Search objects...")
        toolbar_layout.addWidget(self.search_bar)

        self.filter_button = DropDownPushButton(FluentIcon.FILTER, "Filter", self)
        toolbar_layout.addWidget(self.filter_button)

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
        self.list_widget.setStyleSheet(
            "QListWidget { border: none; background: transparent; padding-right: 5px; }"
            "QListWidget::item { border-bottom: 1px solid rgba(255, 255, 255, 0.05); }"
            "QListWidget::item:selected { background: rgba(255, 255, 255, 0.08); border-radius: 4px; }"
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
        main_layout = VBoxLayout(self)  # Use fluent VBoxLayout
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.bulk_action_widget)
        main_layout.addWidget(self.stack, 1)

    def _connect_signals_to_viewmodel(self):
        # ViewModel -> View connections
        self.view_model.items_updated.connect(self._on_items_updated)
        # ... other vm -> view connections

        # View -> ViewModel connections
        # self.search_bar.textChanged.connect(self.view_model.on_search_query_changed)
        # ... other view -> vm connections

    def bind_viewmodel(self, viewmodel):
        """Connects this panel's widgets and slots to the ViewModel."""
        self.view_model = viewmodel

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

        # --- Connect UI widget actions to ViewModel slots ---
        # self.search_bar.textChanged.connect(self.view_model.on_search_query_changed)
        # self.create_button.clicked.connect(self._on_create_object_requested)
        pass

    # --- SLOTS (Responding to ViewModel Signals) ---

    def _on_loading_started(self):
        """Flow 2.2: Clears the view and shows the loading shimmer."""
        # self._item_widgets.clear()
        # Clear widgets from layout...
        # self.shimmer_frame.start_shimmer()
        pass

    def _on_loading_finished(self):
        """Flow 2.2: Hides the loading shimmer."""
        # self.shimmer_frame.stop_shimmer()
        pass

    def _on_items_updated(self, items: list):
        """Flow 2.2 & 5.1: Repopulates the entire grid view with new items."""
        # 1. Clear the view and self._item_widgets map.

        # 2. For each item, create a new ObjectListItemWidget.
        # for item in items:
        #     widget = ObjectListItemWidget(item, self.view_model, ...)
        #
        #     # PATCH IMPLEMENTATION: Connect the child's signal to this panel's slot.
        #     widget.item_selected.connect(self._on_list_item_selected)
        #
        #     # 3. Add the widget to the layout and the internal map.
        #     self._item_widgets[item.id] = widget
        #     self.grid_layout.addWidget(widget)

        # 4. Handle the case where 'items' is empty by showing a "no results" message.
        pass

    def _on_item_needs_update(self, item: object):
        """Flow 2.2 & 3.1: Finds and redraws a single widget for a targeted update."""
        # widget = self._item_widgets.get(item.id)
        # if widget: widget.set_data(item)
        pass

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
