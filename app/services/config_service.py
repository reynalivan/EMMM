# app/services/config_service.py
from pathlib import Path
import configparser
from typing import Any
from app.models.config_model import AppConfig


class ConfigService:
    """Manages all read/write operations for the config.ini file."""

    def __init__(self, config_path: Path):
        # --- Service Setup ---
        self.config_path = config_path

    def load_config(self) -> AppConfig:
        """Flow 1.1: Loads the entire configuration from config.ini."""
        # Handles FileNotFoundError and parsing errors gracefully by returning a default AppConfig.
        # This is the primary method for reading the configuration at startup or refresh.
        return AppConfig()

    def save_config(self, config: AppConfig):
        """
        Flow 1.2: Atomically saves the entire AppConfig object to the config.ini file.
        This is the primary method for transactional saves from SettingsViewModel.
        """
        # 1. Create a new configparser object.
        # 2. Populate all sections ([Games], [Settings], [Presets], [UI]) from the 'config' object.
        # 3. Write the parser object to self.config_path in one operation.
        # 4. Wrap the write operation in a try/except block to handle IO/PermissionError.
        pass

    def save_setting(self, section: str, key: str, value: Any):
        """Saves a single key-value pair to a specific section of the config file."""
        # Used for quick, individual updates like last_active_game_id (Flow 2.1)
        # or safe_mode_enabled (Flow 6.1) that don't require a full transactional save.
        pass
