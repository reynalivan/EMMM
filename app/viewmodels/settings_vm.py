from PyQt6.QtCore import QObject, pyqtSignal
from app.models.config_model import GameDetail
from app.services.config_service import ConfigService
from app.core.exceptions import ConfigError
from app.utils.logger_utils import logger


class SettingsVM(QObject):
    game_list_changed = pyqtSignal()
    save_finished = pyqtSignal(bool)

    def __init__(self,
                 config_service: ConfigService,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._config_service = config_service
        self._editable_games: list[GameDetail] = []

    def load_settings(self) -> None:
        """Load list of games from config file into internal state"""
        try:
            self._editable_games = self._config_service.load_games()
            logger.info(
                f"Loaded {len(self._editable_games)} game(s) from config.ini")
            self.game_list_changed.emit()
        except ConfigError as e:
            logger.error("Failed to load games from config.ini", exc_info=True)
            self._editable_games = []
            self.game_list_changed.emit()

    def get_editable_games(self) -> list[GameDetail]:
        """Return copy of editable game list"""
        return self._editable_games.copy()

    def add_game(self, name: str, path: str) -> bool:
        """Add a new game to the editable list. Name must be unique"""
        if not name or not path:
            logger.warning("Add game failed: empty name or path")
            return False

        if any(game.name == name for game in self._editable_games):
            logger.warning(f"Add game failed: duplicate name '{name}'")
            return False

        self._editable_games.append(GameDetail(name=name, path=path))
        logger.info(f"Added game: {name} -> {path}")
        self.game_list_changed.emit()
        return True

    def remove_game(self, index: int) -> None:
        """Remove a game by index (safe)"""
        try:
            removed = self._editable_games.pop(index)
            logger.info(f"Removed game: {removed.name}")
            self.game_list_changed.emit()
        except IndexError:
            logger.warning(f"Remove game failed: index out of range ({index})")

    def update_game(self, index: int, name: str, path: str) -> bool:
        """Update game name and path at specified index"""
        if not (0 <= index < len(self._editable_games)):
            logger.warning(f"Update game failed: invalid index {index}")
            return False

        for i, game in enumerate(self._editable_games):
            if i != index and game.name == name:
                logger.warning(f"Update game failed: duplicate name '{name}'")
                return False

        self._editable_games[index] = GameDetail(name=name, path=path)
        logger.info(f"Updated game at index {index}: {name} -> {path}")
        self.game_list_changed.emit()
        return True

    def save_changes(self) -> None:
        """Save the editable game list to config.ini"""
        success = self._config_service.save_games(self._editable_games)
        if success:
            logger.info("Saved game list to config.ini successfully")
        else:
            logger.error("Failed to save game list to config.ini")
        self.save_finished.emit(success)
