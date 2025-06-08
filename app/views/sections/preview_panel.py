# app/views/sections/preview_panel.py
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
)

from qfluentwidgets import (
    CaptionLabel,
    ScrollArea,
    TitleLabel,
    SubtitleLabel,
    BodyLabel,
    TextEdit,
    SwitchButton,
    PrimaryPushButton,
    PushButton,
    FluentIcon,
    VBoxLayout as FluentVBoxLayout,  # Use fluent layout
)

# Import ViewModels and Services for type hinting and dependency injection
from app.viewmodels.preview_panel_vm import PreviewPanelViewModel
from app.services.thumbnail_service import ThumbnailService

# Import custom widgets we've designed
from app.views.components.thumbnail_widget import ThumbnailSliderWidget

# from app.views.components.keybinding_widget import KeyBindingWidget # To be created later


class PreviewPanel(QWidget):
    """The UI panel on the right that displays details for a selected FolderItem."""

    def __init__(
        self,
        viewmodel: PreviewPanelViewModel,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.view_model = viewmodel
        self._keybinding_widgets = []  # To hold created KeyBindingWidget instances

        self._init_ui()
        # self._bind_view_models() # To be implemented later
        pass

    def _init_ui(self):
        """Initializes all UI components for the preview panel."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Stack to switch between content view and empty view
        self.stack = QStackedWidget(self)
        main_layout.addWidget(self.stack)

        # --- 1. Main Content View (inside a ScrollArea) ---
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(self.scroll_area.Shape.NoFrame)
        self.scroll_area.setStyleSheet(
            "ScrollArea { background: transparent; border: none; }"
        )

        content_widget = QWidget()
        content_layout = FluentVBoxLayout(content_widget)  # Use fluent layout
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(12)

        self.scroll_area.setWidget(content_widget)

        # -- Header: Title and Status Switch --
        header_layout = QHBoxLayout()
        self.title_label = TitleLabel("No Mod Selected")
        self.title_label.setWordWrap(True)
        self.status_switch = SwitchButton()  # Status switch for the selected mod
        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.status_switch)
        content_layout.addLayout(header_layout)

        # -- Thumbnail Slider --
        self.thumbnail_slider = ThumbnailSliderWidget(self.view_model)
        self.thumbnail_slider.setMinimumHeight(200)  # Give it a minimum height
        content_layout.addWidget(self.thumbnail_slider)

        # -- Description Section --
        content_layout.addWidget(SubtitleLabel("Description"))
        self.description_editor = TextEdit()
        self.description_editor.setPlaceholderText("No description available.")
        self.description_editor.setObjectName("DescriptionEditor")
        self.description_editor.setMinimumHeight(80)
        self.save_description_button = PushButton("Save Description")
        self.save_description_button.setIcon(FluentIcon.SAVE)
        self.save_description_button.hide()  # Show only when description is changed
        content_layout.addWidget(self.description_editor)
        content_layout.addWidget(
            self.save_description_button, 0, Qt.AlignmentFlag.AlignRight
        )

        # -- Mod Config (.ini) Section --
        content_layout.addWidget(SubtitleLabel("Mod Configuration"))
        # This layout will be populated dynamically with KeyBindingWidgets
        config_container = QWidget()
        self.ini_config_layout = FluentVBoxLayout(config_container)
        self.ini_config_layout.setSpacing(8)

        # A container for the dynamically added widgets
        config_container.setLayout(content_layout)

        self.save_config_button = PrimaryPushButton("Save Configuration")
        self.save_config_button.setIcon(FluentIcon.SAVE)
        self.save_config_button.hide()  # Show only when config is changed

        content_layout.addWidget(config_container)
        content_layout.addWidget(
            self.save_config_button, 0, Qt.AlignmentFlag.AlignRight
        )

        content_layout.addStretch(1)  # Push all content to the top

        # --- 2. Empty State View ---
        self.empty_view = BodyLabel("Select a mod to see its details", self)
        self.empty_view.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- Assemble Stack ---
        self.stack.addWidget(self.scroll_area)
        self.stack.addWidget(self.empty_view)

        # Start by showing the empty view
        self.stack.setCurrentWidget(self.empty_view)

    def bind_viewmodel(self, viewmodel):
        """Connects this panel's widgets and slots to the ViewModel."""
        self.view_model = viewmodel

        # --- Connect ViewModel signals to this panel's slots ---
        self.view_model.item_loaded.connect(self._on_item_loaded)
        self.view_model.ini_config_ready.connect(self._on_ini_config_ready)
        # self.view_model.is_dirty_changed.connect(self.save_all_button.setEnabled)

        # --- Connect UI widget actions to ViewModel slots ---
        # Note: The status switch is special, it triggers an action on foldergrid_vm.
        # This connection is handled by MainWindow orchestrating the VMs.

        # self.description_editor.textChanged.connect(
        #    lambda: self.view_model.on_description_changed(self.description_editor.toPlainText())
        # )
        # self.save_all_button.clicked.connect(self.view_model.save_all_changes)

        # The ThumbnailSliderWidget will handle its own internal bindings for add/remove,
        # calling the appropriate methods on the view_model.
        # e.g., self.thumbnail_slider.add_requested.connect(self.view_model.add_new_thumbnail)
        pass

    # --- SLOTS (Responding to ViewModel Signals) ---

    def _on_item_loaded(self, item: object):
        """Flow 5.2 Part A: Populates the entire panel with data from a new item."""
        if not item:
            # Logic to clear the panel and show a "No item selected" message.
            return

        # 1. Update simple widgets
        # self.title_label.setText(item.actual_name)
        # self.status_switch.setChecked(item.status == ModStatus.ENABLED)
        # self.description_editor.setText(item.description)

        # 2. Pass image paths to the thumbnail slider
        # self.thumbnail_slider.set_image_paths(item.preview_images)

        # 3. Clear old .ini config widgets
        # while self.ini_config_layout.count():
        #     child = self.ini_config_layout.takeAt(0)
        #     if child.widget():
        #         child.widget().deleteLater()
        pass

    def _on_ini_config_ready(self, keybindings: list):
        """Flow 5.2 Part D: Populates the Mods Config area with KeyBindingWidgets."""
        # For each keybinding data object in the list, create a KeyBindingWidget,
        # connect its 'valueChanged' signal to self.view_model.on_keybinding_edited,
        # and add the widget to self.ini_config_layout.
        pass

    def clear_panel(self):
        """Clears all displayed data from the panel."""
        # Used when no item is selected, e.g., after deleting the active object.
        # self._on_item_loaded(None)
        pass
