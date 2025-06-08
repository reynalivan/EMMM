# app/viewmodels/settings_vm.py
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
from app.models.config_model import AppConfig
import dataclasses


class SettingsViewModel(QObject):
    """Manages the state and logic for the transactional Settings dialog."""

    # --- Signals for UI & Cross-ViewModel Communication ---
    config_updated = pyqtSignal()
    long_operation_started = pyqtSignal(str)
    long_operation_finished = pyqtSignal(dict)  # Contains success/failure report
    toast_requested = pyqtSignal(str, str)  # message, level

    def __init__(self, config_service, game_service, workflow_service):
        super().__init__()
        # --- Injected Services ---
        self.config_service = config_service
        self.game_service = game_service
        self.workflow_service = workflow_service

        # --- Transactional State ---
        self.original_config = (
            None  # Stores the config state when the dialog was opened
        )
        self.temp_games = []  # A mutable list for game edits
        self.temp_presets = {}  # A mutable dict for preset edits

    # --- Public Methods (API for the View) ---

    def load_current_config(self, app_config: AppConfig):
        """Flow 1.2: Loads current config into a temporary state for editing."""
        self.original_config = app_config
        self.temp_games = list(app_config.games) if app_config else []
        self.temp_presets = dict(app_config.presets) if app_config else {}
        # Logic to emit signals to populate the view's lists...
        pass

    def save_all_changes(self) -> bool:
        """
        Flow 1.2: Validates, builds a new AppConfig object from temp state,
        and requests the ConfigService to save it.
        """
        # 1. Final validation (e.g., check for duplicate names/paths).
        # 2. Build the new AppConfig object from temp data.
        #    - `new_config = dataclasses.replace(self.original_config, ...)`
        # 3. Request the save operation.
        #    - `self.config_service.save_config(new_config)`
        # 4. Handle success/failure and return True/False.
        return True  # Placeholder for actual save logic

    # --- Game Management ---
    def add_game_from_path(self, path: Path):
        """Flow 1.2: Initiates the XXMI auto-detection and adds games to the temp list."""
        pass

    def update_temp_game(self, game_id: str, new_name: str, new_path: Path):
        """Flow 1.2: Edits a game in the temporary list."""
        pass

    def remove_temp_game(self, game_id: str):
        """Flow 1.2: Removes a game from the temporary list."""
        pass

    # --- Preset Management (Async Operations) ---
    def rename_preset(self, old_name: str, new_name: str):
        """Flow 6.2.A: Starts the async workflow to rename a preset and update all mods."""
        pass

    def delete_preset(self, preset_name: str):
        """Flow 6.2.A: Starts the async workflow to delete a preset and update all mods."""
        pass

    # --- Private Slots for Async Results ---

    def _on_preset_rename_finished(self, result: dict):
        """Handles the result of the preset rename workflow."""
        pass

    def _on_preset_delete_finished(self, result: dict):
        """Handles the result of the preset delete workflow."""
        pass
