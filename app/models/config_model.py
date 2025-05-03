from dataclasses import dataclass
from typing import Optional


@dataclass
class AppSettings:
    last_selected_game_name: Optional[str] = None
    safe_mode_enabled: bool = False
