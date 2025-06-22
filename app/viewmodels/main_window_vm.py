# App/viewmodels/main window vm.py

from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool
from typing import Optional, List, Dict

from app.utils.logger_utils import logger
from app.utils.async_utils import Worker

# Import models and services for type hinting

from app.models.config_model import AppConfig
from app.models.game_model import Game
from app.models.mod_item_model import ObjectItem
from app.services.config_service import ConfigService
from app.services.workflow_service import WorkflowService
from .mod_list_vm import ModListViewModel
from .preview_panel_vm import PreviewPanelViewModel

from enum import Enum, auto


class ToastLevel(Enum):
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()


class MainWindowViewModel(QObject):
    """
    Orchestrates high-level application state, global workflows,
    and communication between other ViewModels.
    """

    # ---Signals for Global UI Feedback ---

    toast_requested = pyqtSignal(str, ToastLevel)  # message, level

    global_operation_started = pyqtSignal(str)
    global_operation_finished = pyqtSignal()
    global_progress_updated = pyqtSignal(int, int)  # value, total

    settings_dialog_requested = pyqtSignal()
    safe_mode_switch_state = pyqtSignal(bool)

    # ---Signals for Game List UI ---

    game_list_updated = pyqtSignal(list)  # list[dict] instead of list[Game]

    active_game_changed = pyqtSignal(object)  # Game object or None

    def __init__(
        self,
        config_service: ConfigService,
        workflow_service: WorkflowService,
        objectlist_vm: ModListViewModel,
        foldergrid_vm: ModListViewModel,
        preview_panel_vm: PreviewPanelViewModel,
    ):
        super().__init__()

        # ---Injected Services & ViewModels ---
        self.config_service = config_service
        self.workflow_service = workflow_service
        self.objectlist_vm = objectlist_vm
        self.foldergrid_vm = foldergrid_vm
        self.preview_panel_vm = preview_panel_vm

        # ---Internal State ---
        self.config: Optional[AppConfig] = None
        self.active_game: Optional[Game] = None
        self.active_object: Optional[ObjectItem] = None
        self._pending_foldergrid_path_to_refresh: Path | None = None
        self._connect_child_vm_signals()

    # ---Initialization ---

    def start_initial_load(self):
        """Flow 1.1: Kicks off the application loading sequence in a background thread."""
        logger.info("Starting initial configuration load...")
        self.toast_requested.emit("Loading configuration...", ToastLevel.INFO)

        # Create a worker to load config file without blocking the UI

        worker = Worker(self.config_service.load_config)

        # Connect signals from the worker to the appropriate slots

        worker.signals.result.connect(self._on_load_config_finished)
        worker.signals.error.connect(self._on_load_config_error)

        # Execute the worker in the global thread pool

        thread_pool = QThreadPool.globalInstance()

        if thread_pool:
            thread_pool.start(worker)
        else:
            # This case is highly unlikely in a running app but is good to handle.

            logger.critical("Could not retrieve the global QThreadPool instance.")
            self.toast_requested.emit(
                "Critical error: Could not start background tasks.", "error"
            )

    def refresh_all_from_config(self):
        """Flow 2.1: Reloads config from disk, typically after settings change."""
        logger.info("Configuration has changed. Refreshing application state...")
        # Re-running the initial load sequence is the most reliable way to refresh

        app_config = self.config_service.load_config()
        self._on_load_config_finished(app_config)

    # ---Public Slots (for UI Actions) ---

    def set_current_game(self, game: Optional[Game]):
        """Flow 2.1: Sets the active game, triggering objectlist load."""
        if not game or (self.active_game and self.active_game.id == game.id):
            return  # Do nothing if the game is the same or invalid

        logger.info(f"Setting active game to: '{game.name}'")
        self.active_game = game

        # Save this choice for the next session

        self.config_service.save_setting("last_active_game_id", self.active_game.id)

        # Revised: DICT EMIT contains relevant data, not all objects

        active_game_data = {"name": self.active_game.name, "id": self.active_game.id}
        self.active_game_changed.emit(active_game_data)

        # Flow 2.1 Step 5: Trigger the next flow

        if self.active_game.path and self.active_game.path.is_dir():
            self.objectlist_vm.load_items(
                path=self.active_game.path, game=self.active_game
            )
        else:
            logger.error(
                f"Cannot load mods for '{self.active_game.name}', path is invalid or not set."
            )
            self.objectlist_vm.unload_items()
            self.foldergrid_vm.unload_items()
            self.toast_requested.emit(
                f"Path for {self.active_game.name} is invalid!", "error"
            )

    def set_current_game_by_name(self, game_name: str):
        """
        Finds a game by its name and sets it as active.
        Called by the UI (e.g., ComboBox).
        """
        if not self.config:
            return

        game = next((g for g in self.config.games if g.name == game_name), None)
        if game:
            self.set_current_game(game)

    def set_active_object(self, object_item_data: dict | None):
        """
        Flow 2.3 Trigger A: Receives a data dictionary from the view, finds the
        corresponding model object, and triggers the foldergrid load.
        """
        if not object_item_data:
            self.active_object = None
            if self.foldergrid_vm:
                self.foldergrid_vm.unload_items()
            return

        item_id = object_item_data.get("id")
        if not item_id:
            logger.error("set_active_object received data with no ID.")
            return

        # Redundancy Prevention: Check against the current active object's ID

        if self.active_object and self.active_object.id == item_id:
            return

        # ---LOGIC: Find the actual model object from the list ---

        object_item = next(
            (item for item in self.objectlist_vm.master_list if item.id == item_id),
            None,
        )

        if not object_item:
            logger.error(
                f"Could not find ObjectItem with ID '{item_id}' in master list."
            )
            return
        # ---END REVISED LOGIC ---

        # From here on, we use the real `object_item` model, so the rest of the code works.

        logger.info(f"Setting active object to: '{object_item.actual_name}'")
        self.active_object = object_item

        if self.active_game and object_item.folder_path.is_dir():
            self.foldergrid_vm.load_items(
                path=object_item.folder_path, game=self.active_game, is_new_root=True
            )
        elif not self.active_game:
            logger.error("Cannot load foldergrid: No active game context.")
        else:
            logger.error(
                f"Path for object '{object_item.actual_name}' is invalid: {object_item.folder_path}"
            )
            self.foldergrid_vm.unload_items()
            self.toast_requested.emit(
                f"Path for {object_item.actual_name} is invalid!", "error"
            )

    def toggle_safe_mode(self, is_on: bool):
        """Flow 6.1: Initiates the global Safe Mode workflow."""
        pass  # Validates, then starts async worker to call workflow_service.apply_safe_mode()

    def initiate_global_randomize(self):
        """Flow 6.2.B: Initiates the global mod randomization workflow."""
        pass  # Validates, gets user confirmation, then starts async worker for global randomize.

    def request_main_refresh(self):
        """Handles the main refresh button action, reloading the active view."""
        if self.active_game:
            # Store the path we want to recover after the objectlist is refreshed
            if self.active_object and self.foldergrid_vm.current_path:
                self._pending_foldergrid_path_to_refresh = (
                    self.foldergrid_vm.current_path
                )
            else:
                self._pending_foldergrid_path_to_refresh = None

            # 1. Always refresh the top-level object list
            logger.info(f"Refreshing object list for '{self.active_game.name}'")
            self.objectlist_vm.load_items(
                path=self.active_game.path,
                game=self.active_game,
                is_new_root=True,  # Treat refresh as setting a new root
            )

        else:
            logger.warning("Refresh requested, but no active game.")
            self.toast_requested.emit("No active game to refresh.", "info")

    # ---Private Slots (for Async/Signal Handling) ---

    def _connect_child_vm_signals(self):
        """Connects signals from child VMs to orchestrator methods."""
        # Flow 3.1a & 4.2.A: An active object was modified/renamed
        self.objectlist_vm.active_object_modified.connect(
            self._on_active_object_modified
        )
        # Flow 4.2.B: An active object was deleted
        self.objectlist_vm.active_object_deleted.connect(self._on_active_object_deleted)

        # Flow 3.1b: A foldergrid item was modified, check if it's the one in preview
        self.foldergrid_vm.foldergrid_item_modified.connect(
            self._on_foldergrid_item_modified
        )

        # Flow 2.3 Trigger B: An item in the object list was selected
        self.preview_panel_vm.item_metadata_saved.connect(
            self.foldergrid_vm.update_item_in_list
        )
        self.objectlist_vm.load_completed.connect(self._on_objectlist_refresh_complete)
        self.objectlist_vm.toast_requested.connect(self._on_toast_requested)
        self.foldergrid_vm.toast_requested.connect(self._on_toast_requested)
        self.preview_panel_vm.toast_requested.connect(self._on_toast_requested)
        self.foldergrid_vm.active_selection_changed.connect(
            self._on_foldergrid_selection_changed
        )
        self.foldergrid_vm.selection_invalidated.connect(
            self.preview_panel_vm.clear_panel
        )

    def _on_toast_requested(self, message: str, level: str = "info"):
        """
        Creates and shows a non-blocking InfoBar (toast) notification
        at the top-right of the window.
        """
        # Convert string level to ToastLevel enum if necessary
        if isinstance(level, str):
            try:
                toast_level = ToastLevel[level.upper()]
            except KeyError:
                toast_level = ToastLevel.INFO
        else:
            toast_level = level
        # Emit the toast notification
        self.toast_requested.emit(message, toast_level)

    def _on_active_object_modified(self, new_object_item: ObjectItem):
        """
        Handles the domino effect when an active object is modified (e.g., toggled).
        """
        # Check whether the item that changes is the item that we are actively seeing.

        if self.active_object and self.active_object.id == new_object_item.id:
            logger.info(
                f"Active object '{self.active_object.actual_name}' was modified. Refreshing foldergrid."
            )

            # 1. Update state object aktif di main view model

            self.active_object = new_object_item

            # 2. PICKE Re -loading foldergrid with a new path
            # (For example, the current path has a "disabled" prefix)

            self.foldergrid_vm.load_items(
                path=new_object_item.folder_path,
                game=self.active_game,
                is_new_root=True,
            )

    def _on_active_object_deleted(self, deleted_item):
        """Flow 4.2.B: Handles an active object being deleted."""
        pass  # Checks if deleted_item matches self.active_object and calls preview_panel_vm.clear_preview()

    def _process_config_update(self):
        """
        Flow 2.1 Step 2: Core function for processing configuration updates.
        """
        if not self.config or not self.config.games:
            logger.warning(
                "No games configured. Unloading content and requesting settings dialog."
            )
            self.objectlist_vm.unload_items()
            self.foldergrid_vm.unload_items()
            self.active_game_changed.emit(None)  # Notify UI to disable relevant parts

            self.settings_dialog_requested.emit()
            return

        # Convert Game objects to dictionaries

        view_data = [{"name": g.name, "id": g.id} for g in self.config.games]

        self.game_list_updated.emit(view_data)  # Emit list of dictionaries

        self._determine_active_game()

    def _determine_active_game(self):
        """Flow 2.1 Step 4: Finds the last active game or defaults to the first."""
        if not self.config:
            return

        game_to_set = None
        previous_active_id = (
            self.active_game.id if self.active_game else self.config.last_active_game_id
        )

        if previous_active_id:
            game_to_set = next(
                (g for g in self.config.games if g.id == previous_active_id), None
            )

        if not game_to_set:
            game_to_set = self.config.games[0]
            logger.info(
                f"No valid last active game found. Defaulting to first game: '{game_to_set.name}'"
            )

        self.set_current_game(game_to_set)

    def _on_load_config_finished(self, app_config: AppConfig):
        """
        Flow 1.1: Slot executed when the config is successfully loaded.
        It updates the state and triggers the next step in the loading process.
        """
        logger.info("Configuration loaded. Updating view model state...")
        self.config = app_config

        # Proceed to the next step in the startup flow

        self._process_config_update()

    def _on_load_config_error(self, error_info: tuple):
        """Handles errors that occur during the config loading process."""
        exctype, value, tb = error_info
        logger.critical(
            f"An unhandled exception occurred during config load: {value}\n{tb}"
        )
        self.toast_requested.emit(
            "Error loading configuration. See logs for details.", ToastLevel.ERROR
        )
        # In case of a critical error, we can proceed with a default empty config

        self._on_load_config_finished(AppConfig())

    def _on_safe_mode_finished(self, result):
        """Flow 6.1: Handles the result of the Safe Mode workflow."""
        pass  # Hides overlay, saves config, and reloads foldergrid on success.

    def _on_foldergrid_item_modified(self, modified_item):
        """
        Flow 3.1b Domino Effect: Checks if the modified item from the grid
        is the one currently active in the PreviewPanel.
        """
        # Check if the preview panel is displaying something and if the IDs match
        if (
            self.preview_panel_vm.current_item_model
            and self.preview_panel_vm.current_item_model.id == modified_item.id
        ):

            logger.info(
                f"Currently previewed item '{modified_item.actual_name}' was modified. Updating preview."
            )
            # If it matches, forward the updated model object to preview_panel_vm
            logger.info(
                f"Currently previewed item '{modified_item.actual_name}' was modified. Updating preview."
            )
            self.preview_panel_vm.update_view_for_item(modified_item)

    def _on_objectlist_refresh_complete(self, success: bool):
        """
        Handles the refresh chain. After the objectlist is refreshed,
        it intelligently decides whether to restore the foldergrid's sub-path
        or clear its selection.
        """
        path_to_recover = self._pending_foldergrid_path_to_refresh
        self._pending_foldergrid_path_to_refresh = (
            None  # Clear pending state immediately
        )

        if not success:
            return

        if not path_to_recover:
            # Nothing to recover, we are done.
            return

        # After objectlist refresh, self.active_object is now up-to-date.
        # Check if the path to recover is still valid and belongs to the active object.
        is_path_still_valid = False
        if self.active_object and path_to_recover.is_dir():
            try:
                # This check ensures the path is still a child of the (potentially renamed) active object
                path_to_recover.relative_to(self.active_object.folder_path)
                is_path_still_valid = True
            except ValueError:
                is_path_still_valid = False

        if is_path_still_valid:
            # If path is valid, restore the foldergrid view to that path.
            logger.info(
                f"Step 2: Restoring and refreshing folder grid view for '{path_to_recover}'"
            )
            self.foldergrid_vm.load_items(
                path=path_to_recover, game=self.active_game, is_new_root=False
            )
        else:
            # --- FIX: If path is NOT valid, explicitly clear the foldergrid selection ---
            # This will trigger the domino effect to clear the PreviewPanel.
            logger.warning(
                f"Could not restore path '{path_to_recover}', it's no longer valid. Clearing selection."
            )
            self.foldergrid_vm.set_active_selection(None)

    def _on_foldergrid_selection_changed(self, selected_item_id: str | None):
        """
        Handles when the active selection in the foldergrid is cleared.
        """
        # If the selection is cleared (ID is None), command the preview panel to clear itself.
        # We don't need to handle the case where an item IS selected, because that's
        # already handled by the item_selected -> set_current_item flow.
        if selected_item_id is None:
            logger.info(
                "Foldergrid selection cleared, commanding preview panel to clear."
            )
            self.preview_panel_vm.clear_panel()
