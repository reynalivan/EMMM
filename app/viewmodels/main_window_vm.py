# app/viewmodels/main_window_vm.py
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, List, Dict
from app.models.config_model import AppConfig
from app.models.game_model import Game
from app.models.mod_item_model import ObjectItem


class MainWindowViewModel(QObject):
    """
    Orchestrates high-level application state, global workflows,
    and communication between other ViewModels.
    """

    # --- Signals for Global UI Feedback ---
    toast_requested = pyqtSignal(
        str, str
    )  # message, level ('info', 'error', 'success')
    global_operation_started = pyqtSignal(str)
    global_operation_finished = pyqtSignal()
    global_progress_updated = pyqtSignal(int, int)  # value, total
    settings_dialog_requested = pyqtSignal()

    # --- Signals for Game List UI ---
    game_list_updated = pyqtSignal(list)  # list[Game]
    active_game_changed = pyqtSignal(object)  # Game object or None

    def __init__(
        self,
        config_service,
        workflow_service,
        objectlist_vm,
        foldergrid_vm,
        preview_panel_vm,
    ):
        super().__init__()
        # --- Injected Services & ViewModels ---
        self.config_service = config_service
        self.workflow_service = workflow_service
        self.objectlist_vm = objectlist_vm
        self.foldergrid_vm = foldergrid_vm
        self.preview_panel_vm = preview_panel_vm

        # --- Internal State ---
        self.config: Optional[AppConfig] = None
        self.active_game: Optional[Game] = None
        self.active_object: Optional[ObjectItem] = None

        self._connect_child_vm_signals()

    # --- Initialization ---

    def start_initial_load(self):
        """Flow 1.1: Kicks off the entire application loading sequence."""
        pass  # Starts an async worker to call config_service.load_config()

    def refresh_all_from_config(self):
        """Flow 2.1: Reloads config from disk, typically after settings change."""
        pass  # Calls config_service.load_config() and then _process_config_update()

    # --- Public Slots (for UI Actions) ---

    def set_current_game(self, game):
        """Flow 2.1: Sets the active game, triggering objectlist load."""
        pass  # Updates state, saves to config, emits signals, and calls objectlist_vm.load_items()

    def set_active_object(self, object_item):
        """Flow 2.3: Sets the active object, triggering foldergrid load."""
        pass  # Updates state and calls foldergrid_vm.load_items()

    def toggle_safe_mode(self, is_on: bool):
        """Flow 6.1: Initiates the global Safe Mode workflow."""
        pass  # Validates, then starts async worker to call workflow_service.apply_safe_mode()

    def initiate_global_randomize(self):
        """Flow 6.2.B: Initiates the global mod randomization workflow."""
        pass  # Validates, gets user confirmation, then starts async worker for global randomize.

    def request_main_refresh(self):
        """Handles the main refresh button action, reloading the active view."""
        pass  # Reloads objectlist or foldergrid based on what is currently active.

    # --- Private Slots (for Async/Signal Handling) ---

    def _connect_child_vm_signals(self):
        """Connects signals from child VMs to orchestrator methods."""
        # Flow 3.1a & 4.2.A: An active object was modified/renamed
        self.objectlist_vm.active_object_modified.connect(
            self._on_active_object_modified
        )
        # Flow 4.2.B: An active object was deleted
        self.objectlist_vm.active_object_deleted.connect(self._on_active_object_deleted)
        # Flow 3.1b (Revised): A foldergrid item was modified, check if it's the one in preview
        self.foldergrid_vm.foldergrid_item_modified.connect(
            self._on_foldergrid_item_modified
        )
        pass

    def _on_active_object_modified(self, modified_item):
        """Flow 3.1a: Handles an active object being modified or renamed."""
        # If the modified item is the currently active object, update the preview panel.
        pass  # Checks if modified_item matches self.active_object and calls preview_panel_vm.update_preview()

    def _on_active_object_deleted(self, deleted_item):
        """Flow 4.2.B: Handles an active object being deleted."""
        pass  # Checks if deleted_item matches self.active_object and calls preview_panel_vm.clear_preview()

    def _process_config_update(self):
        """Flow 2.1: Central logic to process a newly loaded AppConfig."""
        pass  # Emits game_list_updated, handles empty game list, calls _determine_active_game()

    def _determine_active_game(self):
        """Flow 2.1: Finds the last active game or defaults to the first."""
        pass  # Logic to find and call set_current_game()

    def _on_load_config_finished(self, result):
        """Flow 1.1: Handles the result of the initial config load."""
        pass  # Updates self.config and calls _process_config_update()

    def _on_safe_mode_finished(self, result):
        """Flow 6.1: Handles the result of the Safe Mode workflow."""
        pass  # Hides overlay, saves config, and reloads foldergrid on success.

    def _on_foldergrid_item_modified(self, modified_item):
        """Flow 3.1b: Relays an item update to the preview panel if necessary."""
        pass  # Checks if modified_item is active in preview_panel_vm and calls its update method.
