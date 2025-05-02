# app/viewmodels/main_window_vm.py

import os
from typing import Optional
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal
from app.services.config_service import ConfigService
from app.models.config_model import GameDetail, AppSettings
from app.utils.logger_utils import logger
from app.services.file_watcher_service import FileWatcherService
from app.viewmodels.object_list_vm import ObjectListVM
from app.viewmodels.folder_grid_vm import FolderGridVM
from typing import List
from app.viewmodels.settings_vm import SettingsVM
from app.core.constants import CONFIG_KEY_SAFE_MODE, CONFIG_KEY_LAST_GAME


class MainWindowVM(QObject):
    # --- Signals ---
    game_list_updated = pyqtSignal(list)
    current_game_changed = pyqtSignal(GameDetail)
    safe_mode_status_changed = pyqtSignal(bool)
    global_refresh_requested = pyqtSignal()
    errorOccurred = pyqtSignal(str, str)  # title, message

    file_watcher_stats_updated = pyqtSignal(
        int, float
    )  # folders_watched, changes_per_sec

    def __init__(
        self,
        config_service: ConfigService,
        object_vm: ObjectListVM,
        folder_vm: FolderGridVM,
        setting_vm: SettingsVM,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._config_service = config_service
        self._available_games = []
        self._settings_vm = setting_vm
        self._current_game: Optional[GameDetail] = None
        self._is_safe_mode_on: bool = False
        self.file_watcher_service: Optional[FileWatcherService] = None
        self.object_vm = object_vm
        self.folder_vm = folder_vm
        self._app_settings: AppSettings = self._config_service.load_app_settings()

    def initialize_state(self) -> None:
        logger.info("Initializing MainWindowVM: loading config and game list...")

        self._update_game_list()
        # Find selected game
        selected_game = next(
            (
                g
                for g in self._available_games
                if g.name == self._app_settings.last_selected_game_name
            ),
            None,
        )
        if selected_game:
            self.set_current_game(selected_game)

    def select_game_by_name(self, name: str | None):
        if name is None:
            if self._current_game is not None:
                self.set_current_game(None)
            return

        if self._current_game and self._current_game.name == name:
            logger.debug("Game selection unchanged.")
            return

        logger.debug(f"Selecting game by name: {name}")
        game = next((g for g in self._available_games if g.name == name), None)
        self.set_current_game(game)
        self._save_last_selected_game()

    def set_current_game(self, game: Optional[GameDetail]):
        logger.debug(f"Setting current game: {game}")
        if self._current_game == game:
            logger.debug("Same game selected, skipping reload.")
            return

        self._current_game = game
        self.current_game_changed.emit(game)

        self.object_vm.clear_state()
        self.folder_vm.clear_state()

        if game:
            self._load_game_items(game.path)
            self._save_last_selected_game()

    def _load_game_items(self, game_path: str):
        if not game_path:
            return
        self.object_vm.load_game_items(game_path)
        self.folder_vm.clear_state()

    def _update_game_list(self) -> None:
        new_list = self._config_service.load_games()
        self._handle_new_game_list(new_list)

    def _handle_new_game_list(self, new_list: List[GameDetail]):
        new_keys = {(g.name, g.path) for g in new_list}
        old_keys = {(g.name, g.path) for g in self._available_games}

        if new_keys != old_keys:
            self._available_games = new_list
            self.game_list_updated.emit(new_list)
            if self._current_game and self._current_game.name not in [
                g.name for g in new_list
            ]:
                self.set_current_game(None)
        else:
            logger.debug("Game list unchanged.")

    def _save_last_selected_game(self):
        if self._current_game:
            self._save_setting(CONFIG_KEY_LAST_GAME, self._current_game.name)

    def _save_setting(self, key: Enum, value: any):
        try:
            key_str = key.value if isinstance(key, Enum) else str(key)
            if not hasattr(self._app_settings, key_str):
                logger.warning(f"Unknown config key: {key_str}")
                return
            if getattr(self._app_settings, key_str) == value:
                return
            setattr(self._app_settings, key_str, value)
            self._config_service.save_app_settings(self._app_settings)
            logger.debug(f"Saved setting {key_str} = {value}")
        except Exception as e:
            msg = f"Failed to save setting {key_str}: {e}"
            logger.error(msg, exc_info=True)
            self.errorOccurred.emit("Save Error", msg)

    def set_safe_mode(self, is_on: bool):
        logger.debug(f"MainWindowVM: Setting safe mode to: {is_on}")
        if self._is_safe_mode_on == is_on:
            logger.debug("Safe mode status unchanged.")
            return
        self._is_safe_mode_on = is_on
        self._save_safe_mode_setting()
        self.safe_mode_status_changed.emit(is_on)
        if self.folder_vm:
            self.folder_vm.set_safe_mode(is_on)

    def get_current_game(self) -> Optional[GameDetail]:
        return self._current_game

    def get_available_games(self) -> List[GameDetail]:
        return self._available_games

    def is_safe_mode_active(self) -> bool:
        return self._is_safe_mode_on

    def _save_safe_mode_setting(self):
        logger.debug("MainWindowVM: Saving safe mode setting...")
        self._save_setting(CONFIG_KEY_SAFE_MODE, self._is_safe_mode_on)

    def bind_filewatcher_service(self, watcher: FileWatcherService):
        """Connect FileWatcherService to MainWindowVM."""
        logger.info("MainWindowVM: Binding FileWatcherService.")
        if self.file_watcher_service:
            self.file_watcher_service.statsUpdated.disconnect(
                self._on_filewatcher_stats_updated
            )
        self.file_watcher_service = watcher
        watcher.statsUpdated.connect(self._on_filewatcher_stats_updated)

    def _on_filewatcher_stats_updated(self, folder_count: int, change_rate: float):
        """Internal slot: update UI with file watcher stats."""
        logger.debug(
            f"MainWindowVM: FileWatcher stats updated -> {folder_count} folders, {change_rate:.1f} changes/sec"
        )
        self.file_watcher_stats_updated.emit(folder_count, change_rate)

    def get_settings_vm(self) -> SettingsVM:
        """Expose the settingsvm instance."""
        return self._settings_vm
