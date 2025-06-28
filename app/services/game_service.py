# app/services/game_service.py
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from app.core.constants import KNOWN_XXMI_FOLDERS
from app.utils.logger_utils import logger


@dataclass(frozen=True)
class DetectionResult:
    """A structured result for the XXMI Launcher detection."""

    is_detected: bool
    proposals: list[dict[str, Path]] = field(default_factory=list)


class GameService:
    """Handles game-specific logic, primarily XXMI Launcher detection."""

    LAUNCHER_EXECUTABLE_PATH = "Resources/Bin/XXMI Launcher.exe"
    # Prioritized mod folder names
    MODS_SUBFOLDER_PRIORITY = ["Mods/SkinSelectImpact", "Mods/character", "Mods"]

    def _find_actual_mods_path(self, game_path: Path) -> Optional[Path]:
        """
        Helper function to find the true mods folder based on a priority list.
        """
        if not game_path or not game_path.is_dir():
            return None

        for subfolder in self.MODS_SUBFOLDER_PRIORITY:
            potential_path = game_path / subfolder
            if potential_path.is_dir():
                logger.debug(
                    f"Found prioritized mods path for '{game_path.name}' at: {potential_path}"
                )
                return potential_path

        # If no prioritized subfolder is found, return the base game path
        # as the mods are likely directly inside it.
        logger.debug(
            f"No prioritized subfolder found for '{game_path.name}'. Using base path."
        )
        return game_path

    def _deduce_game_type_from_path(self, path: Path) -> str | None:
        """
        Helper function to deduce the game_type by checking if any known
        game identifier (GIMI, SRMI) is present in the path string.
        """
        path_str_lower = str(path).lower()
        for game_type_key in KNOWN_XXMI_FOLDERS:
            if game_type_key.lower() in path_str_lower:
                return game_type_key  # Return the original key, e.g., "GIMI"
        return None

    def propose_games_from_path(self, path: Path) -> DetectionResult:
        """
        Flow 1.2: Detects XXMI structure using a multi-layered, intelligent approach.
        1. Checks if the selected path is the Launcher's root.
        2. Checks if the selected path is inside a known game folder.
        3. For each found game, finds the actual mods folder using a priority list.
        """
        if not path.is_dir():
            logger.warning(f"Provided path is not a directory: {path}")
            return DetectionResult(is_detected=False, proposals=[])

        logger.info(f"Analyzing path for game proposals: {path}")

        xxmi_root_path: Path | None = None
        proposals: List[Dict[str, Any]] = []

        # --- Detection Method 1: Check for Launcher Root ---
        if (path / self.LAUNCHER_EXECUTABLE_PATH).is_file():
            logger.info(
                f"XXMI Launcher executable found. Treating '{path}' as the root."
            )
            xxmi_root_path = path

        # --- Detection Method 2: Check Path Ancestry (if Method 1 fails) ---
        if not xxmi_root_path:
            # Combine the path itself and its parents for a full check
            paths_to_check = [path] + list(path.parents)
            for p in paths_to_check:
                if p.name in KNOWN_XXMI_FOLDERS:
                    xxmi_root_path = p.parent
                    logger.info(
                        f"Found known game folder '{p.name}'. Deduced XXMI root: {xxmi_root_path}"
                    )
                    break

        # --- Process Proposals if an XXMI Root was found ---
        if xxmi_root_path:
            # Construct potential paths for all known games and validate them.
            for folder_name in sorted(list(KNOWN_XXMI_FOLDERS)):
                potential_game_path = xxmi_root_path / folder_name
                if potential_game_path.is_dir():
                    # Now find the *actual* mods folder using our priority list
                    actual_mods_path = self._find_actual_mods_path(potential_game_path)
                    if actual_mods_path:
                        deduced_game_type = self._deduce_game_type_from_path(potential_game_path)
                        proposals.append({
                            "name": folder_name,
                            "path": actual_mods_path,
                            "game_type": deduced_game_type # Use the deduced type
                        })

            if proposals:
                return DetectionResult(is_detected=True, proposals=proposals)

        # --- Fallback: If no XXMI structure is detected at all ---
        logger.info(
            "No XXMI structure detected. Proposing the selected folder as a single game."
        )
        # Still try to be smart and find the prioritized mods subfolder
        actual_mods_path = self._find_actual_mods_path(path)
        final_path = actual_mods_path if actual_mods_path else path

        # Use the name of the folder containing the mods as the game name
        final_name = final_path.name
        if final_path.name in ["Mods", "character", "SkinSelectImpact"]:
            final_name = final_path.parent.name

        deduced_game_type = self._deduce_game_type_from_path(final_path)
        single_proposal = [{
            "name": final_name,
            "path": final_path,
            "game_type": deduced_game_type # Can be None if not found
        }]
        return DetectionResult(is_detected=False, proposals=single_proposal)
