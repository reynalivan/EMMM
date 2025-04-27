from dataclasses import dataclass
from typing import Optional


@dataclass
class GameDetail:
    name: str  # Unique game name (e.g. "GIMI", "WWMI")
    path: str  # Absolute path to the game root directory


@dataclass
class AppSettings:
    last_selected_game_name: Optional[str] = None
    safe_mode_enabled: bool = False
