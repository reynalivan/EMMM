# app/views/components/objectlist_widget.py
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from app.viewmodels.mod_list_vm import ModListViewModel
from app.models.mod_item_model import FolderItem
from app.services.thumbnail_service import ThumbnailService


class ObjectListItemWidget(QWidget):
    """
    A self-contained widget to display a single ObjectItem. It forwards all
    user interactions to the ViewModel and updates its display based on the item model.
    """

    # Custom signal to notify the parent panel of a selection click.
    item_selected = pyqtSignal(object)  # Emits the item model

    def __init__(
        self,
        item: FolderItem,
        viewmodel: ModListViewModel,
        thumbnail_service: ThumbnailService,
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
        # self.status_switch.toggled.connect(self._on_status_toggled)
        # self.selection_checkbox.stateChanged.connect(self._on_selection_changed)
        pass

    def set_data(self, item: FolderItem):
        """Flow 2.2, 3.1a, 4.2.A: Updates the widget's display with new data."""
        self.item = item
        # Update UI elements: name_label, status_switch state, etc.
        # Request thumbnail update
        # pixmap = self.thumbnail_service.get_thumbnail(item.id, item.thumbnail_path, 'object')
        # self.thumbnail_label.setPixmap(pixmap)
        pass

    def show_processing_state(self, is_processing: bool, text: str = "Processing..."):
        """Flow 3.1a, 4.2: Shows a visual indicator that the item is being processed."""
        # Disables controls and can show an overlay with text on the widget.
        pass

    # --- Qt Event Handlers ---

    def contextMenuEvent(self, event):
        """Flow 4.2, 4.3, 6.3: Creates and shows a context menu on right-click."""
        # Create a menu with actions that connect directly to ViewModel methods.
        # e.g., rename_action.triggered.connect(lambda: self.view_model.rename_item(self.item.id))
        pass

    def mousePressEvent(self, event):
        """Flow 2.3: Notifies the parent panel that this item was clicked."""
        # This signal will be caught by ObjectListPanel, which then orchestrates
        # the call to the main view model to set the active object.
        self.item_selected.emit(self.item)
        super().mousePressEvent(event)
        pass

    def showEvent(self, event):
        """Flow 2.2: Triggers lazy-hydration when the widget becomes visible."""
        # if self.item.is_skeleton:
        #    self.view_model.request_item_hydration(self.item.id)
        super().showEvent(event)
        pass

    # --- Private Slots (Handling UI events) ---

    def _on_status_toggled(self):
        """Flow 3.1a: Forwards the status toggle action to the ViewModel."""
        self.view_model.toggle_item_status(self.item.id)
        pass

    def _on_selection_changed(self):
        """Flow 3.2: Forwards the selection change to the ViewModel."""
        # self.view_model.set_item_selected(
        #    self.item.id, self.selection_checkbox.isChecked()
        # )
        pass
