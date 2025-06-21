# App/viewmodels/preview panel vm.py

import asyncio
import copy
from pathlib import Path
from typing import Any, Dict
from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal
from qfluentwidgets import MessageBox
from app.models.mod_item_model import FolderItem, ModStatus
from app.services.ini_parsing_service import IniParsingService, KeyBinding
from app.services.mod_service import ModService
from app.utils import SystemUtils
from app.viewmodels.mod_list_vm import ModListViewModel
from app.utils.async_utils import Worker
from app.utils.logger_utils import logger


class PreviewPanelViewModel(QObject):
    """Manages state and logic for the detailed preview panel."""

    # ---Signals for UI Updates & Feedback ---
    item_loaded = pyqtSignal(object)  # Emits FolderItem to populate the entire panel
    ini_config_loading = pyqtSignal(bool)
    ini_config_ready = pyqtSignal(list)
    is_description_dirty_changed = pyqtSignal(bool)
    toast_requested = pyqtSignal(str, str)  # message, level
    # ---Signals for Cross-ViewModel Communication ---
    item_metadata_saved = pyqtSignal(object)
    save_description_state = pyqtSignal(str, bool)  # text, is_enabled
    unsaved_changes_prompt_requested = pyqtSignal(dict)
    ini_dirty_state_changed = pyqtSignal(bool)
    save_config_state = pyqtSignal(str, bool)

    def __init__(
        self,
        mod_service,
        ini_parsing_service,
        thumbnail_service,
        foldergrid_vm,
        sys_utils,
    ):
        super().__init__()
        # ---Injected Services ---
        self.foldergrid_vm: ModListViewModel = foldergrid_vm
        self.sys_utils: SystemUtils = sys_utils
        self.mod_service: ModService = mod_service
        self.ini_parsing_service: IniParsingService = ini_parsing_service
        # ---Internal State ---
        self.current_item_model: FolderItem | None = None
        self.is_description_dirty = False
        self.is_ini_dirty = False
        self._unsaved_ini_changes: Dict[str, Dict[str, Any]] = {}
        self._unsaved_description: str | None = None
        self.editable_keybindings: list[KeyBinding] = (
            []
        )  # A mutable list of KeyBinding objects for live edits

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
        "" "Loading new items, checking changes that have not been stored in advance." ""
        # ---Unsaved Changes Guard Clause ---
        if self.is_description_dirty:
            # Revised: Change the question text to yes/no and remove the button option
            logger.info("Unsaved changes detected. Requesting confirmation from view.")
            context = {"next_item_data": item_data}
            self.unsaved_changes_prompt_requested.emit(context)
            return

        self._load_item(item_data)

    def discard_changes_and_proceed(self, next_item_data: dict | None):
        """
        Slots called by view if the user agrees to remove the change.
        """
        logger.info("User chose to discard changes. Proceeding with navigation.")
        self._reset_dirty_state()
        self._load_item(next_item_data)

    def _load_item(self, item_data: dict | None) -> None:
        """Load selected item; parse its .ini files off-UI-thread."""
        if not item_data:
            self.clear_panel()
            return

        # ── locate model ──────────────────────────────────────────────────────
        item_id = item_data.get("id")
        self.current_item_model = next(
            (m for m in self.foldergrid_vm.master_list if m.id == item_id), None
        )

        if not self.current_item_model:
            logger.error("Model not found for item%s", item_id)
            self.clear_panel()
            return

        # ── push basic data to UI immediately ────────────────────────────────
        self.item_loaded.emit(self._create_dict_from_item(self.current_item_model))

        # ── start async parsing (thread-pool) ─────────────────────────────────
        logger.info("Async ini-parsing for '%s'", self.current_item_model.actual_name)
        self.ini_config_loading.emit(True)  # show spinner

        # run new async loader in worker thread → no UI freeze
        folder_path = self.current_item_model.folder_path

        worker = Worker(
            lambda: asyncio.run(
                self.ini_parsing_service.load_keybindings_async(folder_path)
            )
        )
        worker.signals.result.connect(self._on_ini_config_loaded)
        worker.signals.error.connect(self._on_ini_config_error)

        thread_pool = QThreadPool.globalInstance()
        if thread_pool is not None:
            thread_pool.start(worker)
        else:
            logger.error(
                "QThreadPool.globalInstance() returned None. Cannot start worker."
            )

    def save_description(self) -> bool:
        """Starting the process of storing the description in the background."""
        if (
            not self.is_description_dirty
            or self._unsaved_description is None
            or not self.current_item_model
        ):
            return False

        logger.info(
            f"Saving description for '{self.current_item_model.actual_name}'..."
        )
        self.save_description_state.emit("Saving...", False)

        worker = Worker(
            self.mod_service.update_item_properties,
            self.current_item_model,
            {"description": self._unsaved_description},
        )
        worker.signals.result.connect(self._on_description_saved)
        thread_pool = QThreadPool.globalInstance()
        if thread_pool is not None:
            thread_pool.start(worker)
        else:
            logger.error(
                "QThreadPool.globalInstance() returned None. Cannot start worker."
            )
        return True  # Indicates the storage process begins

    def update_view_for_item(self, new_item_model: FolderItem):
        """
        Flow 3.1b: Updates the view when the currently displayed item is modified
        externally (e.g., from the foldergrid).
        """
        logger.info(
            f"PreviewPanel receiving external update for item:{new_item_model.actual_name}"
        )
        # Internal State Update
        self.current_item = new_item_model
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
        if not self.current_item_model:
            return

        # Compare the current text with the original description of the model
        current_description = self.current_item_model.description or ""
        is_now_dirty = text != current_description

        # Only update and sign signal if the state 'is_description_dirty' changes
        if is_now_dirty != self.is_description_dirty:
            self.is_description_dirty = is_now_dirty
            self.is_description_dirty_changed.emit(self.is_description_dirty)

        # Save text that has not been stored if 'dirty'
        if self.is_description_dirty:
            self._unsaved_description = text
        else:
            self._unsaved_description = None

    def on_keybinding_edited(
        self, binding_id: str, field_type: str, field_identifier: object, new_value: str
    ):
        """
        Flow 5.2 Part D: Tracks live edits made to a keybinding in the UI.
        This version correctly handles the signal and data structure.
        """
        logger.debug(
            f"Keybinding edited: id={binding_id}, type={field_type}, identifier={field_identifier}, value='{new_value}'"
        )

        # Use Setdefault to make a sub-time if not yet. This is safer.
        changes_for_binding = self._unsaved_ini_changes.setdefault(binding_id, {})

        # Keep changes based on the type of field
        if field_type in ["key", "back"]:
            # 'keys' and 'backs' stored in their own sub-dam
            key_or_back_changes = changes_for_binding.setdefault(field_type, {})
            # Field identifier here is an index (int)
            key_or_back_changes[field_identifier] = new_value

        elif field_type == "assignment":
            # 'Assignments' is kept in its own sub-fiery
            assignment_changes = changes_for_binding.setdefault("assignments", {})
            # Field_Identifier here is the name of the variable (STR)
            assignment_changes[field_identifier] = new_value

        # Tell UI that there is a change in configuration. This has not been saved
        if not self.is_ini_dirty:
            self.is_ini_dirty = True
            self.ini_dirty_state_changed.emit(True)

    # ---Private/Internal Logic & Slots ---
    def open_ini_file(self, file_path: Path):
        """Requests the system utility to open the specified .ini file."""
        logger.info(f"Request to open .ini file:{file_path}")
        self.sys_utils.open_path_in_explorer(file_path)

    def _prompt_for_unsaved_changes(self):
        """Flow 5.2 Part A: Shows the 'Save/Discard/Cancel' dialog."""
        # Returns an enum or string indicating user's choice
        pass

    def _load_ini_config_async(self):
        """Flow 5.2 Part A: Starts the background worker to parse .ini files."""
        pass

    def _update_dirty_state(self):
        """Checks all unsaved flags and emits is_description_dirty_changed signal."""
        pass

    # ---Private Slots for Async Results ---
    def save_ini_config(self):
        """Starting the configuration storage process. This is in the background."""
        if not self._unsaved_ini_changes:
            return

        logger.info("Saving .ini configuration changes...")
        self.save_config_state.emit("Saving...", False)

        worker = Worker(
            self.ini_parsing_service.save_ini_changes, self.editable_keybindings
        )
        worker.signals.result.connect(self._on_ini_saved)
        # Todo: Also Connect to Slot Error Handling

        thread_pool = QThreadPool.globalInstance()
        if thread_pool:
            thread_pool.start(worker)

    def _on_ini_config_loaded(self, result: dict):
        """Handles the result of the .ini parsing worker."""
        self.ini_config_loading.emit(False)  # Hide Loading Spinner

        if result.get("success"):
            self.editable_keybindings = result.get("data", [])
            # Save the original state for comparison when there is editing
            self.original_keybindings = copy.deepcopy(self.editable_keybindings)

        self.ini_config_ready.emit(self.editable_keybindings)
        self.ini_dirty_state_changed.emit(False)

    def _on_ini_config_error(self, error_info: tuple):
        """Handling unexpected errors from Worker Parsing. This."""
        self.ini_config_loading.emit(False)
        logger.error(f"Critical error during .ini parsing:{error_info[1]}")
        self.toast_requested.emit(
            "A critical error occurred while reading mod configurations.", "error"
        )
        self.ini_config_ready.emit([])  # Send an empty list

    def _on_description_saved(self, result: dict):
        """Handles the result of the description save operation."""
        if not result.get("success"):
            self.toast_requested.emit(result.get("error", "Failed to save."), "error")
            self.save_description_state.emit("Save Description", True)
            return

        self.toast_requested.emit("Description saved successfully.", "success")
        self._reset_dirty_state()

        # Update State with a new model from the safety results
        self.current_item_model = result.get("data")

        # Send a signal that metadata item has changed (for sync with foldergrid)
        self.item_metadata_saved.emit(self.current_item_model)

    def _reset_dirty_state(self):
        self.is_description_dirty = False
        self._unsaved_description = None
        self.is_description_dirty_changed.emit(False)
        self.save_description_state.emit("Save Description", True)

    def _on_ini_saved(self, result: dict):
        """Handles the result of the .ini configuration save operation."""
        self.save_config_state.emit(
            "Save Configuration", True
        )  # Return the state button

        if not result.get("success"):
            errors = result.get("errors", [])
            error_msg = f"Failed to save{len(errors)}file(s). Check logs for details."
            self.toast_requested.emit(error_msg, "error")
            return

        self.toast_requested.emit("Configuration saved successfully.", "success")
        # After successfully saved, update State 'Original' and Reset 'Dirty' Flag
        self.original_keybindings = copy.deepcopy(self.editable_keybindings)
        self._unsaved_ini_changes = {}
        self.ini_dirty_state_changed.emit(False)

    def _on_thumbnail_added(self, result: dict):
        """Handles the result of the thumbnail addition operation."""
        pass

    def _on_thumbnail_removed(self, result: dict):
        """Handles the result of the thumbnail removal operation."""
        pass

    def clear_panel(self):
        "" "Clean the preview panel." ""
        self.current_item_data = None
        self.is_description_dirty = False
        self.item_loaded.emit(None)
