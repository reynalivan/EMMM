from dataclasses import dataclass
from typing import Optional


@dataclass
class GameDetail:
    name: str  # Unique game name (e.g. "GIMI", "WWMI")
    path: str  # Absolute path to the game root directory

    def __hash__(self):
        return hash((self.name, self.path))

    def __eq__(self, other):
        if not isinstance(other, GameDetail):
            return False
        return self.name == other.name and self.path == other.path


@dataclass
class AppSettings:
    last_selected_game_name: Optional[str] = None
    safe_mode_enabled: bool = False
