# app/views/sections/preview_panel.py
from PyQt6.QtWidgets import QWidget

# Import all necessary UI components (e.g., TitleLabel, SwitchButton, TextEdit, etc.)
# and custom widgets like ThumbnailSliderWidget, KeyBindingWidget.
# ...


class PreviewPanel(QWidget):
    """The UI panel on the right that displays details for a selected FolderItem."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = None
        self._keybinding_widgets = []  # To hold created KeyBindingWidget instances

        # --- Initialize UI components ---
        # self.title_label = TitleLabel(...)
        # self.status_switch = SwitchButton(...)
        # self.description_editor = TextEdit(...)
        # self.thumbnail_slider = ThumbnailSliderWidget(...)
        # self.ini_config_layout = QVBoxLayout(...)
        # self.save_all_button = PrimaryPushButton("Save All Changes")
        pass

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
