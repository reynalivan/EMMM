# app/services/game_service.py
from pathlib import Path
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DetectionResult:
    """A structured result for the XXMI Launcher detection."""

    is_detected: bool
    proposals: list[dict[str, Path]] = field(default_factory=list)


class GameService:
    """Handles game-specific logic, primarily XXMI Launcher detection."""

    def __init__(self):
        # This service can be stateless.
        pass

    def propose_games_from_path(self, path: Path) -> DetectionResult:
        """
        Flow 1.2: Detects if a path is part of an XXMI Launcher structure.
        Returns a structured DetectionResult object instead of a raw list.
        """
        # Logic to check for "GIMI", "SRMI" folders or "XXMI Launcher.exe"
        # and build a list of proposed games.
        # Returns DetectionResult(is_detected=True/False, proposals=[...])
        # Placeholder logic: always return not detected with empty proposals
        return DetectionResult(is_detected=False, proposals=[])
