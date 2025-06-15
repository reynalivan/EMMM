# App/viewmodels/preview panel vm.py

from PyQt6.QtCore import QObject, pyqtSignal
from app.models.mod_item_model import FolderItem, ModStatus
from app.utils.logger_utils import logger


class PreviewPanelViewModel(QObject):
    """Manages state and logic for the detailed preview panel."""

    # ---Signals for UI Updates & Feedback ---

    item_loaded = pyqtSignal(object)  # Emits FolderItem to populate the entire panel

    ini_config_ready = pyqtSignal(
        list
    )  # Emits list[KeyBinding] to render the .ini editor

    is_dirty_changed = pyqtSignal(
        bool
    )  # Emits True/False to enable/disable save buttons

    toast_requested = pyqtSignal(str, str)  # message, level

    # ---Signals for Cross-ViewModel Communication ---

    item_metadata_saved = pyqtSignal(
        object
    )  # Emits updated FolderItem for list view sync

    def __init__(self, mod_service, ini_parsing_service):
        super().__init__()
        # ---Injected Services ---

        self.mod_service = mod_service
        self.ini_parsing_service = ini_parsing_service

        # ---Internal State ---

        self.current_item = None  # The FolderItem being displayed

        self.editable_keybindings = (
            []
        )  # A mutable list of KeyBinding objects for live edits

        self._unsaved_description = None  # Holds unsaved description text

        self._unsaved_ini_changes = False  # Flag for unsaved .ini edits

    # ---Public Methods (API for the View) ---

    def _create_dict_from_item(self, item: FolderItem) -> dict:
        """Helper to create a view-ready dictionary from a FolderItem model."""
        if not item:
            return {}

        return {
            "id": item.id,
            "actual_name": item.actual_name,
            "is_enabled": (item.status == ModStatus.ENABLED),
            "description": item.description or "",
            "author": item.author or "N/A",
            "tags": item.tags or [],
            "preview_images": item.preview_images or [],
            # ... add other fields needed by view
        }

    # This method was called when the new item was selected from the foldergrid

    def set_current_item(self, item_data: dict | None):
        """Flow 5.2 Part A: Main entry point for setting a new item to preview."""
        # ... (Logic for Unsved Changes remains here)

        # Find the actual model item from foldergrid_vm's list
        # ... this logic will be implemented later when connecting item selection.
        # For now, we assume we have a model item.

        # For now, we make a placeholder
        self.current_item = None  # Placeholder

        view_dict = item_data  # Assume the item_data is the correct DICT

        self.item_loaded.emit(view_dict)
        # self._load_ini_config_async () # call async load for .ini files

    def update_view_for_item(self, new_item_model: FolderItem):
        """
        Flow 3.1b: Updates the view when the currently displayed item is modified
        externally (e.g., from the foldergrid).
        """
        logger.info(
            f"PreviewPanel receiving external update for item: {new_item_model.actual_name}"
        )
        # Internal State Update

        self.current_item = new_item_model

        # Change the model to DICTI

        view_dict = self._create_dict_from_item(new_item_model)
        self.item_loaded.emit(view_dict)

    def save_all_changes(self):
        """Flow 5.2 Part B & D: Saves all pending changes (description, .ini config)."""
        pass

    def add_new_thumbnail(self, image_data):
        """Flow 5.2 Part C: Starts the async process to add a new thumbnail."""
        pass

    def remove_thumbnail(self, image_path: object):
        """Flow 5.2 Part C: Starts the async process to remove a thumbnail."""
        pass

    # ---Public Slots (for UI Edit Tracking) ---

    def on_description_changed(self, text: str):
        """Flow 5.2 Part B: Tracks live edits in the description text area."""
        pass

    def on_keybinding_edited(self, binding_id: str, field: str, new_value):
        """Flow 5.2 Part D: Tracks live edits made to a keybinding in the UI."""
        pass

    # ---Private/Internal Logic & Slots ---

    def _prompt_for_unsaved_changes(self):
        """Flow 5.2 Part A: Shows the 'Save/Discard/Cancel' dialog."""
        # Returns an enum or string indicating user's choice

        pass

    def _load_ini_config_async(self):
        """Flow 5.2 Part A: Starts the background worker to parse .ini files."""
        pass

    def _update_dirty_state(self):
        """Checks all unsaved flags and emits is_dirty_changed signal."""
        pass

    # ---Private Slots for Async Results ---

    def _on_ini_config_loaded(self, result: dict):
        """Handles the result of the .ini parsing worker."""
        pass

    def _on_description_saved(self, result: dict):
        """Handles the result of the description save operation."""
        pass

    def _on_ini_saved(self, result: dict):
        """Handles the result of the .ini configuration save operation."""
        pass

    def _on_thumbnail_added(self, result: dict):
        """Handles the result of the thumbnail addition operation."""
        pass

    def _on_thumbnail_removed(self, result: dict):
        """Handles the result of the thumbnail removal operation."""
        pass
