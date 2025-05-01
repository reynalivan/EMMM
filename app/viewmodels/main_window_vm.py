# app/viewmodels/main_window_vm.py

import os
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from app.services.config_service import ConfigService
from app.models.config_model import GameDetail, AppSettings
from app.utils.logger_utils import logger
from app.services.file_watcher_service import FileWatcherService
from app.viewmodels.object_list_vm import ObjectListVM
from app.viewmodels.folder_grid_vm import FolderGridVM
from typing import List


class MainWindowVM(QObject):
    # --- Signals ---
    game_list_updated = pyqtSignal(list)
    current_game_changed = pyqtSignal(GameDetail)
    safe_mode_status_changed = pyqtSignal(bool)
    global_refresh_requested = pyqtSignal()

    file_watcher_stats_updated = pyqtSignal(
        int, float
    )  # folders_watched, changes_per_sec

    def __init__(
        self,
        config_service: ConfigService,
        object_vm: ObjectListVM,
        folder_vm: FolderGridVM,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._config_service = config_service
        self._available_games = []
        self._current_game: Optional[GameDetail] = None
        self._is_safe_mode_on: bool = False
        self.file_watcher_service: Optional[FileWatcherService] = None
        self.object_vm = object_vm
        self.folder_vm = folder_vm

    def load_initial_data(self) -> None:
        logger.debug("Loading initial data for MainWindowVM")

        try:
            self._available_games = self._config_service.load_games()
            self.game_list_updated.emit(self._available_games)
        except Exception as e:
            logger.error(f"Failed to load games from config: {e}", exc_info=True)
            self._available_games = []
            self.game_list_updated.emit([])

        try:
            settings = self._config_service.load_app_settings()
        except Exception as e:
            logger.warning(f"Failed to load app settings, using defaults: {e}")
            settings = AppSettings()  # fallback to default

        for g in self._available_games:
            if g.name == settings.last_selected_game_name:
                self._current_game = g
                self.current_game_changed.emit(g)

                if self.object_vm and self.folder_vm and g.path:
                    self.object_vm._load_items_for_path(g.path)
                break  # exit after found

    def select_game_by_name(self, name: str) -> None:
        logger.debug(f"Selecting game by name: {name}")
        for g in self._available_games:
            if g.name == name:
                self._current_game = g
                self._save_last_selected_game()
                self.current_game_changed.emit(g)

                # 🔧 Clear old state before loading new game
                if self.object_vm:
                    self.object_vm.clear_state()

                if self.folder_vm:
                    self.folder_vm.clear_state()

                # ✅ Load items after clear
                if g.path:
                    self.object_vm._load_items_for_path(g.path)
                    self.folder_vm._on_safe_mode_changed(self._is_safe_mode_on)

                return

    def update_game_list(self) -> None:
        logger.debug("Updating game list from config service")
        self._available_games = self._config_service.load_games()
        self.game_list_updated.emit(self._available_games)

        if self._current_game and not any(
            g.name == self._current_game.name for g in self._available_games
        ):
            self._current_game = None
            self.current_game_changed.emit(None)

    def _save_last_selected_game(self):
        logger.debug("Saving last selected game")
        settings = self._config_service.load_app_settings()
        settings.last_selected_game_name = (
            self._current_game.name if self._current_game else ""
        )
        self._config_service.save_app_settings(settings)

    def set_safe_mode(self, is_on: bool):
        logger.debug(f"MainWindowVM: Setting safe mode to: {is_on}")
        if self._is_safe_mode_on != is_on:
            self._is_safe_mode_on = is_on
            self._save_safe_mode_setting()
            logger.debug(f"MainWindowVM: Emitting safeModeStatusChanged({is_on})")
            self.safe_mode_status_changed.emit(is_on)

            if self.folder_vm:
                logger.debug(
                    "MainWindowVM: Propagating safe mode change to FolderGridVM."
                )
                self.folder_vm._on_safe_mode_changed(
                    is_on
                )  # <- FIX: propagate to folder grid
        else:
            logger.debug("MainWindowVM: Safe mode status unchanged.")

    def get_current_game(self) -> Optional[GameDetail]:
        return self._current_game

    def get_available_games(self) -> List[GameDetail]:
        return self._available_games

    def is_safe_mode_active(self) -> bool:
        return self._is_safe_mode_on

    def _save_safe_mode_setting(self):
        logger.debug("MainWindowVM: Saving safe mode setting...")
        try:
            settings = self._config_service.load_app_settings()
            settings.safe_mode_enabled = self._is_safe_mode_on
            self._config_service.save_app_settings(settings)
            logger.debug(
                f"MainWindowVM: Safe mode setting saved ({self._is_safe_mode_on})."
            )
        except Exception as e:
            logger.error(
                f"MainWindowVM: Failed to save safe mode setting: {e}", exc_info=True
            )

    def bind_filewatcher_service(self, watcher: FileWatcherService):
        """Connect FileWatcherService to MainWindowVM."""
        logger.info("MainWindowVM: Binding FileWatcherService.")
        self.file_watcher_service = watcher
        watcher.statsUpdated.connect(self._on_filewatcher_stats_updated)

    def _on_filewatcher_stats_updated(self, folder_count: int, change_rate: float):
        """Internal slot: update UI with file watcher stats."""
        logger.debug(
            f"MainWindowVM: FileWatcher stats updated -> {folder_count} folders, {change_rate:.1f} changes/sec"
        )
        self.file_watcher_stats_updated.emit(folder_count, change_rate)
