# app/views/sections/foldergrid_panel.py

from pathlib import Path
from typing import Dict

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QScrollArea,
    QStackedWidget,
)

from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    SearchLineEdit,
    DropDownPushButton,
    PrimaryPushButton,
    PushButton,
    ComboBox,
    FlowLayout,
    SubtitleLabel,
    IndeterminateProgressBar,
)

from app.viewmodels.mod_list_vm import ModListViewModel
from app.views.components.breadcrumb_widget import BreadcrumbWidget
from app.views.components.common.shimmer_frame import ShimmerFrame


class FolderGridPanel(QWidget):
    """The UI panel that displays the grid of mod folders and subfolders."""

    # Custom signal to notify the main window that a new item is selected for preview
    item_selected = pyqtSignal(object)

    def __init__(self, viewmodel: ModListViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = viewmodel
        self._item_widgets: Dict[str, QWidget] = {}  # Maps item_id to its widget

        self._init_ui()
        # self._bind_view_models() # To be implemented later

        # Enable Drag & Drop for this panel
        self.setAcceptDrops(True)

    def _init_ui(self):
        """Initializes all UI components for this panel."""

        # --- Toolbar ---
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 10, 10, 5)
        toolbar_layout.setSpacing(10)

        self.search_bar = SearchLineEdit(self)
        self.search_bar.setPlaceholderText("Search in current folder...")

        self.filter_button = DropDownPushButton(FluentIcon.FILTER, "Filter", self)

        self.create_button = PrimaryPushButton(FluentIcon.ADD, "Create", self)
        self.randomize_button = PushButton(FluentIcon.ROTATE, "Shuffle", self)

        self.preset_combo = ComboBox(self)
        self.preset_combo.setPlaceholderText("Apply Preset")
        self.preset_combo.setMinimumWidth(150)
        self.preset_combo.setEnabled(False)

        toolbar_layout.addWidget(self.search_bar, 1)
        toolbar_layout.addWidget(self.filter_button)
        toolbar_layout.addSpacing(20)
        toolbar_layout.addWidget(self.preset_combo)
        toolbar_layout.addWidget(self.randomize_button)
        toolbar_layout.addWidget(self.create_button)

        # --- Breadcrumb Navigation ---
        self.breadcrumb_widget = BreadcrumbWidget(self)

        # --- Separator Line ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("border-top: 1px solid rgba(255, 255, 255, 0.08);")

        # --- Main Content Area (Stack for switching between states) ---
        self.stack = QStackedWidget(self)

        # State 1: Grid Area (inside a ScrollArea)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; }")

        grid_container_widget = QWidget()
        self.grid_layout = FlowLayout(grid_container_widget, isTight=True)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setVerticalSpacing(15)
        self.grid_layout.setHorizontalSpacing(15)
        self.scroll_area.setWidget(grid_container_widget)

        # State 2: Empty Folder Label
        self.empty_folder_label = SubtitleLabel(
            "This folder is empty.\nDrag a .zip file here to create a new mod.", self
        )
        self.empty_folder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # State 3: Shimmer Frame for Loading
        self.shimmer_frame = ShimmerFrame(self)

        # REVISED: State 4: Placeholder for when no object is selected
        self.placeholder_label = BodyLabel(
            "Select object on left sidebar to view list of mods", self
        )
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add all state widgets to the stack
        self.stack.addWidget(self.placeholder_label)  # Initial view
        self.stack.addWidget(self.scroll_area)
        self.stack.addWidget(self.empty_folder_label)
        self.stack.addWidget(self.shimmer_frame)

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 0, 5, 5)
        main_layout.setSpacing(5)
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.breadcrumb_widget)
        main_layout.addWidget(separator)
        main_layout.addWidget(self.stack, 1)

        # Set the initial state of the panel
        self.stack.setCurrentWidget(self.placeholder_label)

    def bind_viewmodel(self, viewmodel):
        """Connects this panel's widgets and slots to the ViewModel."""
        self.view_model = viewmodel

        # --- Connect ViewModel signals to this panel's slots ---
        self.view_model.loading_started.connect(self._on_loading_started)
        self.view_model.loading_finished.connect(self._on_loading_finished)
        self.view_model.path_changed.connect(self._on_path_changed)
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
        # self.breadcrumb.navigation_requested.connect(self.view_model.load_items)
        # self.search_bar.textChanged.connect(self.view_model.on_search_query_changed)
        # self.create_button.clicked.connect(self._on_create_mod_requested)
        # self.randomize_button.clicked.connect(self.view_model.initiate_randomize)
        # (Connections for filter button, bulk action buttons, preset combobox, etc.)
        pass

    # --- SLOTS (Responding to ViewModel Signals) ---

    def _on_loading_started(self):
        """Flow 2.3: Clears the view and shows the loading shimmer."""
        # Clear all widgets from the grid view.
        # self._item_widgets.clear()
        # self.shimmer_frame.start_shimmer()
        pass

    def _on_loading_finished(self):
        """Flow 2.3: Hides the loading shimmer."""
        # self.shimmer_frame.stop_shimmer()
        pass

    def _on_path_changed(self, new_path: Path):
        """Flow 2.3: Updates the breadcrumb widget with the new navigation path."""
        # self.breadcrumb.update_path(new_path)
        pass

    def _on_items_updated(self, items: list):
        """Flow 2.3 & 5.1: Repopulates the entire grid view with new items."""
        # Clear the view, then create and add FolderGridItemWidget for each item.
        # Handle the case where 'items' is empty by showing a "folder is empty" message.
        pass

    def _on_item_needs_update(self, item: object):
        """Flow 2.3 & 3.1b: Finds and redraws a single widget for a targeted update."""
        # widget = self._item_widgets.get(item.id)
        # if widget: widget.set_data(item)
        pass

    def _on_item_processing_started(self, item_id: str):
        """Flow 3.1b & 4.2: Shows a processing state on a specific widget."""
        # widget = self._item_widgets.get(item_id)
        # if widget: widget.show_processing_state(True)
        pass

    def _on_item_processing_finished(self, item_id: str, success: bool):
        """Flow 3.1b & 4.2: Hides the processing state on a specific widget."""
        # widget = self._item_widgets.get(item_id)
        # if widget: widget.show_processing_state(False)
        pass

    def _on_selection_changed(self, has_selection: bool):
        """Flow 3.2: Enables or disables bulk action buttons based on selection."""
        # self.bulk_enable_button.setEnabled(has_selection)
        pass

    def _on_bulk_action_started(self):
        """Flow 3.2 & 6.2: Disables UI controls during a bulk operation."""
        # Disable search, filter, create, randomize, presets, and all item checkboxes.
        pass

    def _on_bulk_action_completed(self, failed_items: list):
        """Flow 3.2 & 6.2: Re-enables UI controls after a bulk operation."""
        # Re-enable all controls disabled in the method above.
        pass

    # --- UI EVENT HANDLERS (Forwarding to ViewModel) ---

    def _on_create_mod_requested(self):
        """Flow 4.1.A: Shows the creation dialog and forwards to the ViewModel."""
        # Open CreateModDialog, get the task details.
        # self.view_model.initiate_create_mods([task])
        pass

    def dropEvent(self, event):
        """Flow 4.1.A: Handles dropped files and forwards them to the ViewModel."""
        # Filter for .zip files from the event's mime data.
        # Create a list of creation tasks.
        # self.view_model.initiate_create_mods(tasks)
        pass
