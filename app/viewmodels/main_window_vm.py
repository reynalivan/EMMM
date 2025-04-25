from PyQt6.QtCore import QObject, pyqtSignal
from app.services.config_service import ConfigService
from app.models.config_model import GameDetail, AppSettings
from app.utils.logger_utils import logger


class MainWindowVM(QObject):
    gameListUpdated = pyqtSignal(list)
    currentGameChanged = pyqtSignal(GameDetail)
    safeModeStatusChanged = pyqtSignal(bool)
    globalRefreshRequested = pyqtSignal()

    def __init__(self,
                 config_service: ConfigService,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._config_service = config_service
        self._available_games = []
        self._current_game: GameDetail | None = None
        self._is_safe_mode_on: bool = False

    def load_initial_data(self) -> None:
        logger.debug("Loading initial data for MainWindowVM")
        self._available_games = self._config_service.load_games()
        self.gameListUpdated.emit(self._available_games)

        settings = self._config_service.load_app_settings()
        for g in self._available_games:
            if g.name == settings.last_selected_game_name:
                self._current_game = g
                self.currentGameChanged.emit(g)
                return

    def select_game_by_name(self, name: str) -> None:
        logger.debug(f"Selecting game by name: {name}")
        for g in self._available_games:
            if g.name == name:
                self._current_game = g
                self._save_last_selected_game()
                self.currentGameChanged.emit(g)
                return

    def update_game_list(self) -> None:
        logger.debug("Updating game list from config service")
        self._available_games = self._config_service.load_games()
        self.gameListUpdated.emit(self._available_games)

        if self._current_game and not any(g.name == self._current_game.name
                                          for g in self._available_games):
            self._current_game = None
            self.currentGameChanged.emit(None)

    def _save_last_selected_game(self):
        logger.debug("Saving last selected game")
        settings = self._config_service.load_app_settings()
        settings.last_selected_game_name = self._current_game.name if self._current_game else ""
        self._config_service.save_app_settings(settings)

    def set_safe_mode(self, is_on: bool):
        """Sets the safe mode status and emits signal if changed."""
        logger.debug(f"MainWindowVM: Setting safe mode to: {is_on}")
        if self._is_safe_mode_on != is_on:
            self._is_safe_mode_on = is_on
            self._save_safe_mode_setting()  # Simpan ke config
            # Pastikan sinyal ini dipancarkan
            logger.debug(
                f"MainWindowVM: Emitting safeModeStatusChanged({is_on})")
            self.safeModeStatusChanged.emit(is_on)  # <-- PANCARKAN SINYAL
        else:
            logger.debug("MainWindowVM: Safe mode status unchanged.")

    def get_current_game(self) -> GameDetail | None:
        logger.debug(f"fGetting current game {self._current_game}")
        return self._current_game

    def get_available_games(self) -> list[GameDetail]:
        logger.debug(f"Getting available games: {self._available_games}")
        return self._available_games

    def is_safe_mode_active(self) -> bool:
        logger.debug(
            f"Checking if safe mode is active: {self._is_safe_mode_on}")
        return self._is_safe_mode_on

    def _save_safe_mode_setting(self):
        """Saves the current safe mode setting to config."""
        logger.debug("MainWindowVM: Saving safe mode setting...")
        try:
            settings = self._config_service.load_app_settings()
            settings.safe_mode_enabled = self._is_safe_mode_on
            self._config_service.save_app_settings(settings)
            logger.debug(
                f"MainWindowVM: Safe mode setting saved ({self._is_safe_mode_on})."
            )
        except Exception as e:
            # Log error, maybe emit an error signal?
            logger.error(f"MainWindowVM: Failed to save safe mode setting: {e}",
                         exc_info=True)
