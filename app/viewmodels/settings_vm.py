# App/viewmodels/settings vm.py

import dataclasses
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
from app.models.config_model import AppConfig
from app.models.game_model import Game
from app.services.config_service import ConfigService, ConfigSaveError
from app.services.game_service import GameService
from app.services.workflow_service import WorkflowService
from app.utils.logger_utils import logger


class SettingsViewModel(QObject):
    """Manages the state and logic for the transactional Settings dialog."""

    # ---Signals for UI & Cross-ViewModel Communication ---

    games_list_refreshed = pyqtSignal(list)
    presets_list_refreshed = pyqtSignal(dict)
    config_updated = pyqtSignal()
    toast_requested = pyqtSignal(str, str)  # message, level

    confirmation_requested = pyqtSignal(dict)
    error_dialog_requested = pyqtSignal(str, str)  # title, message

    def __init__(
        self,
        config_service: ConfigService,
        game_service: GameService,
        workflow_service: WorkflowService,
    ):
        super().__init__()
        # ---Injected Services ---

        self.config_service = config_service
        self.game_service = game_service
        self.workflow_service = workflow_service

        # ---Transactional State ---

        self.original_config: AppConfig | None = None
        self.temp_games: list[Game] = []  # A mutable list for game edits

        self.temp_presets: dict = {}  # A mutable dict for preset edits

    # ---Public Methods (API for the View) ---

    def load_current_config(self, app_config: AppConfig):
        """Flow 1.2: Loads current config into a temporary state for editing."""
        logger.info("Loading current configuration into SettingsViewModel.")
        self.original_config = app_config
        self.temp_games = list(app_config.games) if app_config else []
        # self.temp_presets = dict(app_config.presets) if app_config else {}

        # Prepare simple data for the view
        # Convert list[Game] to list[dict]

        view_data = [
            {"id": g.id, "name": g.name, "path": str(g.path)} for g in self.temp_games
        ]

        # Emit signals to tell the dialog to populate its UI

        self.games_list_refreshed.emit(view_data)
        # self.presets_list_refreshed.emit(self.temp_presets) # For later

    def save_all_changes(self) -> bool:
        """
        Validates temporary changes and saves them to disk via ConfigService.
        Returns True on success, False on failure.
        """
        logger.info("Attempting to save all settings changes.")
        # ---1. Final Validation ---

        names = [g.name for g in self.temp_games]
        if len(names) != len(set(names)):
            error_msg = "Cannot save: Duplicate game names found. Please ensure all game names are unique."
            logger.error(error_msg)
            self.error_dialog_requested.emit("Validation Error", error_msg)
            return False

        # ---2. Create New Config State ---

        if not self.original_config:
            # Should not happen in normal flow, but as a safeguard

            new_config = AppConfig(games=self.temp_games)
        else:
            new_config = dataclasses.replace(
                self.original_config,
                games=self.temp_games,
                # presets=self.temp_presets # Add this later
            )

        # ---3. Transactional Save ---

        try:
            self.config_service.save_config(new_config)
            self.config_updated.emit()  # Notify MainWindowViewModel

            return True
        except ConfigSaveError as e:
            logger.critical(f"Failed to save configuration: {e}", exc_info=True)
            self.error_dialog_requested.emit(
                "Save Error", f"Failed to save configuration file.\n\nReason: {e}"
            )
            return False

    # ---Game Management ---

    def add_game_from_path(self, path: Path):
        """Flow 1.2: Memulai deteksi dan meminta konfirmasi jika perlu."""
        detection_result = self.game_service.propose_games_from_path(path)

        if detection_result.is_detected:
            logger.info(f"XXMI structure detected at {path}.")
            dialog_params = {
                "title": "XXMI Structure Detected",
                "text": f"Found {len(detection_result.proposals)} potential games. Do you want to import them all?",
                # 'Context' helps us know what to do with the results later
                "context": {
                    "type": "xxmi_import",
                    "proposals": detection_result.proposals,
                    "fallback_proposal": [{"name": path.name, "path": path}],
                },
            }
            self.confirmation_requested.emit(dialog_params)
        else:
            # If there is nothing to confirm, immediately process

            logger.info(
                f"No XXMI structure detected at {path}. Processing single game."
            )
            self._process_proposals(detection_result.proposals)

    # Revised: a new slot to receive the results of the confirmation dialogue

    def on_confirmation_result(self, result: bool, context: dict):
        """Dipanggil oleh View setelah pengguna menutup dialog konfirmasi."""
        if context.get("type") == "xxmi_import":
            if result:  # Users press "yes"

                proposals = context.get("proposals", [])
                logger.info("User confirmed XXMI import. Processing all proposals.")
                self._process_proposals(proposals)
            else:  # Users press "no"

                proposals = context.get("fallback_proposal", [])
                logger.info(
                    "User declined XXMI import. Processing selected folder only."
                )
                self._process_proposals(proposals)

    def _process_proposals(self, proposals: list[dict]):
        """Memvalidasi dan menambahkan proposal game ke daftar sementara."""
        logger.info(f"Processing {len(proposals)} game proposals.")
        added_count = 0
        existing_paths = {str(g.path) for g in self.temp_games}
        existing_names = {g.name for g in self.temp_games}

        for proposal in proposals:
            name = proposal["name"]
            path_obj = proposal["path"]

            if name in existing_names or str(path_obj) in existing_paths:
                self.toast_requested.emit(f"Game '{name}' already exists.", "warning")
                continue

            logger.info(f"Adding new game to temporary list: {name} at {path_obj}")
            new_game = Game(name=name, path=path_obj)
            self.temp_games.append(new_game)
            added_count += 1

        if added_count > 0:
            # Refresh view

            view_data = [
                {"id": g.id, "name": g.name, "path": str(g.path)}
                for g in self.temp_games
            ]
            self.games_list_refreshed.emit(view_data)

    def update_temp_game(self, game_id: str, new_name: str, new_path: Path):
        """Flow 1.2: Edits a game in the temporary list."""
        pass

    def remove_temp_game(self, game_id: str):
        """Flow 1.2: Removes a game from the temporary list."""
        pass

    # ---Preset Management (Async Operations) ---

    def rename_preset(self, old_name: str, new_name: str):
        """Flow 6.2.A: Starts the async workflow to rename a preset and update all mods."""
        pass

    def delete_preset(self, preset_name: str):
        """Flow 6.2.A: Starts the async workflow to delete a preset and update all mods."""
        pass

    # ---Private Slots for Async Results ---

    def _on_preset_rename_finished(self, result: dict):
        """Handles the result of the preset rename workflow."""
        pass

    def _on_preset_delete_finished(self, result: dict):
        """Handles the result of the preset delete workflow."""
        pass
