# app/services/config_service.py
from pathlib import Path
import configparser
from typing import Any
from app.models.config_model import AppConfig
from app.models.game_model import Game
from app.utils.logger_utils import logger


class ConfigSaveError(IOError):
    pass


class ConfigService:
    """Manages all read/write operations for the config.ini file."""

    def __init__(self, config_path: Path):
        # --- Service Setup ---
        self.config_path = config_path

    def load_config(self) -> AppConfig:
        """
        Flow 1.1: Loads the entire configuration from config.ini.
        Handles FileNotFoundError and parsing errors gracefully by returning a default AppConfig.
        """
        parser = configparser.ConfigParser()
        parser.optionxform = lambda optionstr: optionstr

        if not self.config_path.exists():
            logger.warning(
                f"Config file not found at '{self.config_path}'. Returning default config."
            )
            return AppConfig()

        try:
            parser.read(self.config_path)

            # --- Parse [Games] section ---
            games = []
            if parser.has_section("Games"):
                for name, value in parser.items("Games"):
                    try:
                        # Expecting format: path|id
                        path_str, game_id = value.strip().split("|")
                        game_path = Path(path_str)
                        if game_path.is_dir():
                            games.append(Game(id=game_id, name=name, path=game_path))
                        else:
                            logger.warning(
                                f"Path for game '{name}' does not exist: '{path_str}'. Skipping."
                            )
                    except ValueError:
                        logger.error(
                            f"Malformed value for game '{name}' in config.ini. Expected 'path|id'. Skipping."
                        )

            # --- Parse [Settings] section ---
            settings = parser["Settings"] if parser.has_section("Settings") else {}
            last_active_game_id = settings.get("last_active_game_id")
            safe_mode_enabled = settings.get("safe_mode_enabled", "False").lower() in (
                "1",
                "true",
                "yes",
                "on",
            )

            # --- Parse [UI] section ---
            ui_prefs = parser["UI"] if parser.has_section("UI") else {}
            geometry_str = ui_prefs.get("window_geometry")
            geometry = (
                tuple(map(int, geometry_str.split(","))) if geometry_str else None
            )
            if geometry is not None and len(geometry) != 4:
                logger.warning(
                    f"window_geometry should have 4 values, got {len(geometry)}. Ignoring."
                )
                geometry = None

            splitter_str = ui_prefs.get("splitter_sizes")
            if splitter_str:
                splitter_parts = tuple(map(int, splitter_str.split(",")))
                if len(splitter_parts) == 3:
                    splitter_sizes = splitter_parts
                else:
                    logger.warning(
                        f"splitter_sizes should have 3 values, got {len(splitter_parts)}. Ignoring."
                    )
                    splitter_sizes = None
            else:
                splitter_sizes = None

            return AppConfig(
                games=games,
                last_active_game_id=last_active_game_id,
                safe_mode_enabled=safe_mode_enabled,
                window_geometry=geometry,
                splitter_sizes=splitter_sizes,
            )

        except configparser.Error as e:
            logger.error(f"Failed to parse config.ini: {e}. Returning default config.")
            return AppConfig()

    def save_config(self, config: AppConfig):
        """
        Saves the entire AppConfig object to the config.ini file.
        This operation overwrites the existing file.
        """
        logger.info(f"Saving configuration to {self.config_path}...")
        parser = configparser.ConfigParser()
        parser.optionxform = lambda optionstr: optionstr

        # --- [Settings] Section ---
        parser["Settings"] = {
            "last_active_game_id": config.last_active_game_id or "",
            "safe_mode_enabled": str(config.safe_mode_enabled),
        }

        # --- [UI] Section ---
        if config.window_geometry:
            parser["UI"] = {
                "window_geometry": ",".join(map(str, config.window_geometry)),
                "splitter_sizes": ",".join(map(str, config.splitter_sizes or [])),
            }

        # --- [Games] Section ---
        parser["Games"] = {game.name: f"{game.path}|{game.id}" for game in config.games}

        # --- [Presets] Section (Placeholder for now) ---
        # parser['Presets'] = { ... }

        try:
            with open(self.config_path, "w") as config_file:
                parser.write(config_file)
            logger.info("Configuration saved successfully.")
        except IOError as e:
            # Raise a custom error to be caught by the ViewModel
            raise ConfigSaveError(f"Failed to write to config file: {e}") from e

    def save_setting(self, key: str, value: str, section: str = "Settings"):
        """
        Saves a single key-value pair to a specific section of the config file.
        Used for quick, individual updates like last_active_game_id.
        """
        parser = configparser.ConfigParser()

        # Read the existing file to not overwrite other sections
        if self.config_path.exists():
            parser.read(self.config_path)

        # Ensure the section exists
        if not parser.has_section(section):
            parser.add_section(section)

        parser.set(section, key, str(value))

        try:
            with open(self.config_path, "w") as config_file:
                parser.write(config_file)
            logger.info(f"Saved setting: [{section}] {key} = {value}")
        except IOError as e:
            logger.error(f"Failed to save setting '{key}' to config file: {e}")
