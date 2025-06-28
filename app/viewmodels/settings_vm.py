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
from app.services.database_service import DatabaseService

class SettingsViewModel(QObject):
    """Manages the state and logic for the transactional Settings dialog."""

    # ---Signals for UI & Cross-ViewModel Communication ---

    games_list_refreshed = pyqtSignal(list)
    presets_list_refreshed = pyqtSignal(dict)
    config_updated = pyqtSignal()
    toast_requested = pyqtSignal(str, str)  # message, level
    game_type_selection_requested = pyqtSignal(dict, list)

    confirmation_requested = pyqtSignal(dict)
    error_dialog_requested = pyqtSignal(str, str)  # title, message

    def __init__(
        self,
        config_service: ConfigService,
        game_service: GameService,
        workflow_service: WorkflowService,
        database_service: DatabaseService,
    ):
        super().__init__()
        # ---Injected Services ---

        self.config_service = config_service
        self.game_service = game_service
        self.workflow_service = workflow_service
        self.database_service = database_service

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
            {"id": g.id, "name": g.name, "path": str(g.path), "game_type": g.game_type} for g in self.temp_games
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
        """
        [REVISED] Processes game proposals. If a proposal is complete (has a game_type),
        it's added directly. If not, it emits a signal to request user input.
        """
        logger.info(f"Processing {len(proposals)} game proposals.")

        complete_proposals = []
        incomplete_proposals = []

        # Split proposals into complete and incomplete
        for proposal in proposals:
            if proposal.get("game_type"):
                complete_proposals.append(proposal)
            else:
                incomplete_proposals.append(proposal)

        # Process complete proposals directly
        if complete_proposals:
            self.add_games_to_list(complete_proposals)

        # For incomplete proposals, trigger a signal to request input
        if incomplete_proposals:
            # Get all possible game_types from the database to display in the ComboBox
            available_types = self.database_service.get_all_game_types()

            # We will only request input for the first incomplete proposal at this time
            # Logic for handling multiple incomplete proposals could be added later if needed
            if available_types:
                logger.info(f"Incomplete proposal found for '{incomplete_proposals[0]['name']}'. Requesting user selection.")
                self.game_type_selection_requested.emit(incomplete_proposals[0], available_types)
            else:
                self.toast_requested.emit("Cannot add game: No game types found in database.", "error")

    def set_game_type_and_add(self, proposal: dict, selected_game_type: str):
        """
        Called by the View after the user selects a game_type from the dialog.
        This method finalizes the proposal and adds it.
        """
        logger.info(f"User selected game_type '{selected_game_type}' for '{proposal['name']}'.")

        # Perbarui proposal dengan game_type yang dipilih pengguna
        proposal['game_type'] = selected_game_type

        # Kirim proposal yang sudah lengkap untuk diproses
        self.add_games_to_list([proposal])

    def add_games_to_list(self, proposals_to_add: list[dict]):
        """
        A helper method that takes a list of COMPLETE proposals and adds them
        to the temporary game list.
        """
        added_count = 0
        existing_paths = {str(g.path) for g in self.temp_games}
        existing_names = {g.name.lower() for g in self.temp_games}

        for proposal in proposals_to_add:
            name = proposal["name"]
            path_obj = proposal["path"]
            game_type = proposal.get("game_type")

            if name.lower() in existing_names or str(path_obj) in existing_paths:
                self.toast_requested.emit(f"Game '{name}' already exists.", "warning")
                continue

            logger.info(f"Adding new game to temporary list: {name} (Type: {game_type}) at {path_obj}")
            new_game = Game(name=name, path=path_obj, game_type=game_type)
            self.temp_games.append(new_game)
            added_count += 1

        if added_count > 0:
            # Refresh view
            view_data = [
                {"id": g.id, "name": g.name, "path": str(g.path), "game_type": g.game_type}
                for g in self.temp_games
            ]
            self.games_list_refreshed.emit(view_data)

    def update_temp_game(self, game_id: str, new_name: str, new_path: Path, new_game_type: str):
        """Flow 1.2: Edits a game in the temporary list."""
        # find the game to update by ID
        game_to_update = next((g for g in self.temp_games if g.id == game_id), None)
        if not game_to_update:
            logger.warning(f"Could not find game with ID {game_id} to update.")
            return

        # create a new Game object with updated values
        updated_game = Game(name=new_name, path=new_path, game_type=new_game_type, id=game_id)

        # Replace the old object with the new one in the list
        index = self.temp_games.index(game_to_update)
        self.temp_games[index] = updated_game

        logger.info(f"Updated game '{new_name}' in temporary list.")

        # Refresh view
        view_data = [
            {"id": g.id, "name": g.name, "path": str(g.path), "game_type": g.game_type}
            for g in self.temp_games
        ]
        self.games_list_refreshed.emit(view_data)

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
