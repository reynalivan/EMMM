import configparser
from pathlib import Path
from typing import List
from app.models.config_model import GameDetail, AppSettings
from app.core.constants import (
    CONFIG_SECTION_GAMES,
    CONFIG_SECTION_SETTINGS,
    CONFIG_KEY_LAST_GAME,
    CONFIG_KEY_SAFE_MODE,
)
from app.core.exceptions import ConfigError
from app.utils.logger_utils import logger


class ConfigService:

    def __init__(self, config_filepath: str = "config.ini"):
        self._config_filepath = Path(config_filepath)
        self._parser = configparser.ConfigParser()

    def load_games(self) -> List[GameDetail]:
        self._read_config()
        if CONFIG_SECTION_GAMES not in self._parser:
            return []

        games = []
        for name, path in self._parser[CONFIG_SECTION_GAMES].items():
            games.append(GameDetail(name=name.strip(), path=path.strip()))
        logger.debug(f"Loaded games from config: {games}")
        return games

    def save_games(self, games: List[GameDetail]) -> bool:
        if CONFIG_SECTION_GAMES not in self._parser:
            self._parser.add_section(CONFIG_SECTION_GAMES)
        else:
            self._parser[CONFIG_SECTION_GAMES].clear()

        for game in games:
            self._parser.set(CONFIG_SECTION_GAMES, game.name.strip(), game.path.strip())

        logger.debug(f"Saved games to config: {[g.name for g in games]}")
        return self._write_config()

    def load_app_settings(self) -> AppSettings:
        self._read_config()
        last_game = self._parser.get(
            CONFIG_SECTION_SETTINGS, CONFIG_KEY_LAST_GAME, fallback=None
        )
        safe_mode = self._parser.getboolean(
            CONFIG_SECTION_SETTINGS, CONFIG_KEY_SAFE_MODE, fallback=False
        )
        safe_mode = safe_mode in ("1", "true", "yes")
        logger.debug(f"Loaded settings: last_game={last_game}, safe_mode={safe_mode}")
        return AppSettings(
            last_selected_game_name=last_game if last_game else None,
            safe_mode_enabled=safe_mode,
        )

    def save_app_settings(self, settings: AppSettings) -> bool:
        if CONFIG_SECTION_SETTINGS not in self._parser:
            self._parser.add_section(CONFIG_SECTION_SETTINGS)

        self._parser.set(
            CONFIG_SECTION_SETTINGS,
            CONFIG_KEY_LAST_GAME,
            settings.last_selected_game_name or "",
        )
        self._parser.set(
            CONFIG_SECTION_SETTINGS,
            CONFIG_KEY_SAFE_MODE,
            str(settings.safe_mode_enabled),
        )

        logger.debug(f"Saved settings: {settings}")
        return self._write_config()

    def _read_config(self) -> None:
        if not self._config_filepath.exists():
            logger.warning(
                f"Config file not found at {self._config_filepath}, initializing empty config."
            )
            self._parser[CONFIG_SECTION_GAMES] = {}
            self._parser[CONFIG_SECTION_SETTINGS] = {}
            return

        try:
            self._parser.read(self._config_filepath, encoding="utf-8")
            if CONFIG_SECTION_GAMES not in self._parser:
                self._parser[CONFIG_SECTION_GAMES] = {}
            if CONFIG_SECTION_SETTINGS not in self._parser:
                self._parser[CONFIG_SECTION_SETTINGS] = {}
            logger.debug(f"Config loaded from {self._config_filepath}")
        except Exception as e:
            raise ConfigError(f"Failed to read config file: {e}")

    def _write_config(self) -> bool:
        try:
            with open(self._config_filepath, "w", encoding="utf-8") as f:
                self._parser.write(f)
            logger.debug(f"Config written to {self._config_filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to write config: {e}")
            return False
