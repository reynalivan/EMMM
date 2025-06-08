# app/views/components/foldergrid_widget.py
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from app.models.mod_item_model import FolderItem
from app.viewmodels.mod_list_vm import ModListViewModel


class FolderGridItemWidget(QWidget):
    """
    A self-contained widget for a single item in the foldergrid. It can represent
    either a navigable folder or a final mod item.
    """

    # Custom signal to notify the main panel of a selection click
    item_selected = pyqtSignal(object)  # Emits the item model

    def __init__(
        self,
        item: FolderItem,
        viewmodel: ModListViewModel,
        thumbnail_service: object,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.item = item
        self.view_model = viewmodel
        self.thumbnail_service = thumbnail_service

        self._init_ui()
        self._connect_signals()
        self.set_data(item)

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        # Create labels, checkbox, switch, and icon widgets.
        pass

    def _connect_signals(self):
        """Connects internal UI widget signals to their handler methods."""
        # Connect user actions to methods that will call the ViewModel.
        # e.g., self.status_switch.toggled.connect(self._on_status_toggled)
        pass

    def set_data(self, item: FolderItem):
        """Flow 2.3 & 3.1b: Updates the widget's display with new data."""
        self.item = item
        # Initially, this is called with skeleton data.
        # After hydration, it's called again with the full data.

        # Logic to update UI elements like name, status, etc.

        # Determine which icon/thumbnail to show.
        if item.is_navigable:
            # Show a generic folder icon if it's a navigation folder.
            # pixmap = self.thumbnail_service.get_thumbnail(None, None, 'folder')
            pass
        else:
            # Request the mod's thumbnail if it's a mod item.
            # pixmap = self.thumbnail_service.get_thumbnail(item.id, item.preview_images[0] if item.preview_images else None, 'mod')
            pass

        # self.thumbnail_label.setPixmap(pixmap)
        pass

    def show_processing_state(self, is_processing: bool, text: str = "Processing..."):
        """Flow 3.1b, 4.2: Shows a visual indicator that the item is being processed."""
        # Disables controls and can show an overlay with text on the widget.
        pass

    # --- Qt Event Handlers ---

    def contextMenuEvent(self, event):
        """Flow 4.2, 4.3, 6.3: Creates and shows a context menu on right-click."""
        # Logic to create a menu with "Enable/Disable", "Pin", "Rename", "Delete" actions.
        # Actions are connected directly to ViewModel methods.
        pass

    def mousePressEvent(self, event):
        """Flow 5.2: Notifies the main view that this item was selected for preview."""
        # Do not emit if it's a navigation folder, as that's handled by double-click.
        if not self.item.is_navigable:
            self.item_selected.emit(self.item)
        super().mousePressEvent(event)
        pass

    def mouseDoubleClickEvent(self, event):
        """Flow 2.3: Handles navigation into a subfolder."""
        if self.item.is_navigable:
            self.view_model.load_items(self.item.folder_path)
        super().mouseDoubleClickEvent(event)
        pass

    def showEvent(self, event):
        """Flow 2.3: Triggers lazy-hydration when the widget becomes visible."""
        if self.item.is_skeleton:
            self.view_model.request_item_hydration(self.item.id)
        super().showEvent(event)
        pass

    # --- Private Slots (Handling UI events) ---

    def _on_status_toggled(self):
        """Flow 3.1b: Forwards the status toggle action to the ViewModel."""
        self.view_model.toggle_item_status(self.item.id)
        pass

    def _on_selection_changed(self):
        """Flow 3.2: Forwards the selection change to the ViewModel."""
        # self.view_model.set_item_selected(
        #    self.item.id, self.selection_checkbox.isChecked()
        # )
        pass
