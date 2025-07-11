# App/views/sections/foldergrid panel.py


from pathlib import Path
from typing import Dict
from app.utils.logger_utils import logger
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QListWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)
from PyQt6.QtGui import QAction
from qfluentwidgets import (
    FluentIcon,
    SearchLineEdit,
    DropDownToolButton,
    TransparentToolButton,
    PrimaryToolButton,
    ComboBox,
    ScrollArea,
    BodyLabel,
    PopUpAniStackedWidget,
    RoundMenu,
    PrimaryPushButton,
    PushButton,
    CheckBox,
    FlowLayout,
    TitleLabel,
    IconWidget,
)
from qfluentwidgets.components.widgets import HorizontalSeparator
from app.viewmodels.mod_list_vm import ModListViewModel
from app.views.components.breadcrumb_widget import BreadcrumbWidget
from app.views.components.common.shimmer_frame import ShimmerFrame
from app.views.components.common.flow_grid_widget import FlowGridWidget
from app.views.components.foldergrid_widget import FolderGridItemWidget


class FolderGridPanel(QWidget):
    """The UI panel that displays the grid of mod folders and subfolders."""

    # Custom signal to notify the main window that a new item is selected for preview

    item_selected = pyqtSignal(object)

    def __init__(self, viewmodel: ModListViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = viewmodel
        self._item_widgets: Dict[str, QWidget] = {}  # Maps item_id to its widget

        self.filter_menu = None
        self.filter_widgets = {}

        self._init_ui()
        self._bind_viewmodel()

        # Enable Drag & Drop for this panel

        self.setAcceptDrops(True)

    # In app/views/sections/foldergrid_panel.py

    def _init_ui(self):
        """Initializes all UI components for this panel (Fluent-enhanced)."""

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 10, 0, 5)
        main_layout.setSpacing(6)

        self.setLayout(main_layout)

        # ---Toolbar ---
        toolbar = QHBoxLayout(self)
        toolbar.setSpacing(6)
        toolbar.setContentsMargins(14, 1, 14, 1)

        # Search
        self.search_bar = SearchLineEdit(self)
        self.search_bar.setPlaceholderText("Search folder…")
        toolbar.addWidget(self.search_bar)

        # Filter dropdown
        self.filter_btn = DropDownToolButton(FluentIcon.FILTER, self)
        self.filter_btn.setToolTip("Filter")
        self.filter_menu = RoundMenu(parent=self)
        self.filter_btn.setMenu(self.filter_menu)
        toolbar.addWidget(self.filter_btn)

        # Preset combo
        self.preset_combo = ComboBox(self)
        self.preset_combo.setPlaceholderText("Apply Preset")
        self.preset_combo.setMinimumWidth(150)
        self.preset_combo.setEnabled(False)
        toolbar.addWidget(self.preset_combo)

        # Shuffle button
        self.randomize_btn = TransparentToolButton(FluentIcon.ROTATE, self)
        self.randomize_btn.setToolTip("Shuffle mods")
        toolbar.addWidget(self.randomize_btn)

        # Spacer
        toolbar.addStretch()

        # Create Button (Primary, on the far right)
        self.create_btn = PrimaryToolButton(FluentIcon.ADD, self)
        self.create_btn.setToolTip("Create new mod")
        toolbar.addWidget(self.create_btn)

        main_layout.addLayout(toolbar)

        # --- Result Bar ---
        self.result_bar_widget = QWidget(self)
        self.result_bar_widget.setObjectName("ResultBar")
        result_bar_layout = QHBoxLayout(self.result_bar_widget)
        result_bar_layout.setContentsMargins(14, 4, 10, 4)
        self.result_label = BodyLabel("...")
        self.clear_filter_button = TransparentToolButton(FluentIcon.CLOSE, self.result_bar_widget)
        self.clear_filter_button.setToolTip("Clear all filters and search")
        result_bar_layout.addWidget(self.result_label, 1)
        result_bar_layout.addWidget(self.clear_filter_button)
        self.result_bar_widget.setVisible(False)
        main_layout.addWidget(self.result_bar_widget)

        # Breadcrumb & separator
        self.breadcrumb_widget = BreadcrumbWidget(self)
        main_layout.addWidget(self.breadcrumb_widget)
        separator = HorizontalSeparator(self)
        main_layout.addWidget(separator)

        # Stacked content area
        self.stack = PopUpAniStackedWidget(self)
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Grid in scroll area
        self.grid_widget = FlowGridWidget(self)
        self.scroll_area.setWidget(self.grid_widget)

        # Placeholder, empty, loading states
        self.placeholder_label = BodyLabel("Select an object to view mods...", self)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)


        # Widget for empty state
        self.empty_state_widget = QWidget(self)
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)
        self.empty_icon = IconWidget(FluentIcon.SEARCH, self.empty_state_widget)
        self.empty_icon.setFixedSize(48, 48)
        self.empty_title_label = TitleLabel("Title", self.empty_state_widget)
        self.empty_subtitle_label = BodyLabel("Subtitle", self.empty_state_widget)
        self.empty_subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_subtitle_label.setWordWrap(True)
        empty_layout.addStretch(1)
        empty_layout.addWidget(self.empty_icon, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title_label, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_subtitle_label, 0, Qt.AlignmentFlag.AlignTop)
        empty_layout.addStretch(1)

        self.shimmer_frame = ShimmerFrame(self)

        # Add to the stack
        self.stack.addWidget(self.placeholder_label)
        self.stack.addWidget(self.scroll_area)
        self.stack.addWidget(self.empty_state_widget)
        self.stack.addWidget(self.shimmer_frame)

        main_layout.addWidget(self.stack, 1)

        # Set initial state
        self.stack.setCurrentWidget(self.placeholder_label)

    def _bind_viewmodel(self):
        """Connects this panel's widgets and slots to the ViewModel."""
        # ---Connect ViewModel signals to this panel's slots ---
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

        # --- Connections for UI feedback ---
        self.view_model.filter_state_changed.connect(self._on_filter_state_changed)
        self.view_model.empty_state_changed.connect(self._on_empty_state_changed)
        self.view_model.clear_search_text.connect(self.search_bar.clear)
        self.clear_filter_button.clicked.connect(self.view_model.clear_all_filters_and_search)

        self.view_model.available_filters_changed.connect(self._on_available_filters_changed)

        # ---Connect UI widget actions to ViewModel slots ---
        self.view_model.active_selection_changed.connect(
            self._on_active_selection_changed
        )
        self.breadcrumb_widget.navigation_requested.connect(
            self._on_breadcrumb_navigation
        )
        self.search_bar.textChanged.connect(self.view_model.on_search_query_changed)
        # self.create_button.clicked.connect(self._on_create_mod_requested)
        # self.randomize_button.clicked.connect(self.view_model.initiate_randomize)
        # (Connections for filter button, bulk action buttons, preset combobox, etc.)

    # ---SLOTS (Responding to ViewModel Signals) ---

    def _on_loading_started(self):
        """Flow 2.3: Clears the view and shows the loading shimmer."""
        self.grid_widget.clear_items()
        self._item_widgets.clear()
        self.stack.setCurrentWidget(self.shimmer_frame)

    def _on_loading_finished(self):
        """Flow 2.3: Hides the loading shimmer."""
        self.shimmer_frame.stop_shimmer()
        pass

    def _on_path_changed(self, new_path: Path | None):
        """Flow 2.3: Updates the breadcrumb widget with the new navigation path."""
        if new_path and new_path.is_dir():
            # The new breadcrumb widget handles all root path and update logic internally.
            # We just need to give it the current path.
            self.breadcrumb_widget.set_current_path(new_path)
            self.breadcrumb_widget.setVisible(True)
        else:
            # If path is None or invalid, clear and hide the breadcrumb.
            self.breadcrumb_widget.clear()
            self.breadcrumb_widget.setVisible(False)

            # The rest of your logic to show a placeholder is correct
            self.grid_widget.clear_items()
            self.stack.setCurrentWidget(self.placeholder_label)

    def _on_items_updated(self, items_data: list[dict]):
        """
        Flow 2.3: Repopulates the entire grid view with new skeleton items.
        """
        logger.debug(f"Received {len(items_data)} items to display in foldergrid.")

        self.grid_widget.clear_items()
        self._item_widgets.clear()

        # Grid has been cleaned in _on_loading_started
        if not items_data:
            return

        self.stack.setCurrentWidget(self.scroll_area)

        for item_data in items_data:
            # 1. Create the card widget
            widget = FolderGridItemWidget(
                item_data=item_data,
                viewmodel=self.view_model,
            )

            # 2. Connect its signals
            widget.item_selected.connect(self._on_grid_item_selected)
            widget.item_selected.connect(self.item_selected)

            self.grid_widget.add_widget(widget)
            self._item_widgets[item_data["id"]] = widget

    def _on_item_needs_update(self, item_data: dict):
        """Flow 2.3 Stage 2: Finds and redraws a single widget with hydrated data."""
        item_id = item_data.get("id") or ""
        # _item_widgets bisa berisi QListWidgetItem atau QWidget langsung
        # Bergantung pada implementasi panel Anda (QListWidget vs FlowLayout)
        list_or_item_widget = self._item_widgets.get(item_id)

        if not list_or_item_widget:
            return

        # Tentukan widget sebenarnya
        # Untuk ObjectListPanel (menggunakan QListWidget)
        widget = list_or_item_widget

        # Panggil set_data pada widget anak dengan data baru
        if isinstance(widget, FolderGridItemWidget):
            widget.set_data(item_data)

    def _on_item_processing_started(self, item_id: str):
        """Flow 3.1b & 4.2: Shows a processing state on a specific widget."""
        widget = self._item_widgets.get(item_id)
        if isinstance(widget, FolderGridItemWidget):
            widget.show_processing_state(True)

    def _on_item_processing_finished(self, item_id: str, success: bool):
        """Flow 3.1b & 4.2: Hides the processing state on a specific widget."""
        widget = self._item_widgets.get(item_id)
        if isinstance(widget, FolderGridItemWidget):
            widget.show_processing_state(False)

    # In app/views/sections/foldergrid_panel.py

    def _on_breadcrumb_navigation(self, path: Path):
        """
        Handles the navigation request from the breadcrumb widget.
        This slot ensures all necessary arguments are passed to the ViewModel.
        """
        logger.info(f"Breadcrumb navigation requested for path: {path}")

        # Get the current game context from the ViewModel
        current_game = self.view_model.current_game
        if not current_game:
            logger.error(
                "Cannot navigate via breadcrumb without an active game context."
            )
            return

        # Call the ViewModel's load_items method with all arguments complete
        self.view_model.load_items(
            path=path,
            game=current_game,
            is_new_root=False,  # Breadcrumb navigation is always within the current root
        )

    def _on_active_selection_changed(self, selected_item_id: str | None):
        """Applies a visual 'selected' state to the correct widget."""
        for item_id, widget in self._item_widgets.items():
            # You need to implement a 'set_selected' method on your widget
            # For example, it could change the border color or background.
            is_selected = item_id == selected_item_id

            if isinstance(widget, FolderGridItemWidget):
                widget.set_selected(is_selected)

    def _on_grid_item_selected(self, item_data: dict):
        """
        Handles when a grid item is single-clicked.
        Forwards selection to the main window AND tells the ViewModel about the new active selection.
        """
        # 1. Tell the ViewModel which item is now the active one
        item_id = item_data.get("id")
        self.view_model.set_active_selection(item_id)

        # 2. Forward the selection to the main window to update the preview panel
        self.item_selected.emit(item_data)

    def _on_available_filters_changed(self, filter_options: dict):
        """Clears and rebuilds the foldergrid filter menu UI controls dynamically."""
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

            if name == 'Tags':
                # Use CheckBoxes for multi-select tags
                tags_widget = QWidget()
                tags_layout = FlowLayout(tags_widget) # Use FlowLayout for tags
                tags_layout.setContentsMargins(0, 0, 0, 0)
                tag_checkboxes = []
                for tag in options:
                    checkbox = CheckBox(tag)
                    tags_layout.addWidget(checkbox)
                    tag_checkboxes.append(checkbox)
                self.filter_widgets[name.lower()] = tag_checkboxes
                layout.addWidget(tags_widget)
            else: # For Author and other single-select filters
                combo = ComboBox()
                combo.addItems(["All"] + options)
                self.filter_widgets[name.lower()] = combo
                layout.addWidget(combo)

        layout.addSpacing(10)
        button_layout = QHBoxLayout()
        reset_button = PushButton("Reset")
        apply_button = PrimaryPushButton("Apply")
        button_layout.addWidget(reset_button)
        button_layout.addWidget(apply_button)
        layout.addLayout(button_layout)

        reset_button.clicked.connect(self._on_reset_filters)
        apply_button.clicked.connect(self._on_apply_filters)

        self.filter_menu.addWidget(container, selectable=False)

    def _on_apply_filters(self):
        """Collects filter values from all widgets and sends them to the ViewModel."""
        active_filters = {}
        for key, widget_or_list in self.filter_widgets.items():
            if isinstance(widget_or_list, list): # Handle CheckBoxes for Tags
                selected_tags = [cb.text() for cb in widget_or_list if cb.isChecked()]
                if selected_tags:
                    active_filters[key] = selected_tags
            elif isinstance(widget_or_list, ComboBox): # Handle ComboBox for Author
                value = widget_or_list.currentText()
                if value != "All":
                    active_filters[key] = value

        self.view_model.set_filters(active_filters)
        self.filter_menu.close()

    def _on_reset_filters(self):
        """Resets all filter widgets and tells the ViewModel to clear filters."""
        for key, widget_or_list in self.filter_widgets.items():
            if isinstance(widget_or_list, list):
                for cb in widget_or_list:
                    cb.setChecked(False)
            elif isinstance(widget_or_list, ComboBox):
                widget_or_list.setCurrentIndex(0)

        self.view_model.clear_filters()
        self.filter_menu.close()

    def _on_filter_state_changed(self, show_bar: bool, count: int):
        """Shows or hides the result bar based on the filter state."""
        if show_bar:
            plural = "s" if count > 1 else ""
            self.result_label.setText(f"{count} result{plural} found")

        self.result_bar_widget.setVisible(show_bar)

    def _on_empty_state_changed(self, title: str, subtitle: str):
        """Updates the text on the empty state widget and displays it."""
        self.empty_title_label.setText(title)
        self.empty_subtitle_label.setText(subtitle)

        if "filter" in subtitle or "criteria" in subtitle:
            self.empty_icon.setIcon(FluentIcon.FILTER)
        else:
            self.empty_icon.setIcon(FluentIcon.FOLDER)

        self.stack.setCurrentWidget(self.empty_state_widget)

    def _on_selection_changed(self, has_selection: bool):
        """Flow 3.2: Enables or disables bulk action buttons based on selection."""
        # Self.bulk enable button.set enabled(has selection)

        pass

    def _on_bulk_action_started(self):
        """Flow 3.2 & 6.2: Disables UI controls during a bulk operation."""
        # Disable search, filter, create, randomize, presets, and all item checkboxes.

        pass

    def _on_bulk_action_completed(self, failed_items: list):
        """Flow 3.2 & 6.2: Re-enables UI controls after a bulk operation."""
        # Re-enable all controls disabled in the method above.

        pass

    # ---UI EVENT HANDLERS (Forwarding to ViewModel) ---

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
