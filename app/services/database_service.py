import json
from pathlib import Path

from app.utils.logger_utils import logger
from app.core.signals import global_signals

class DatabaseService:
    """
    Manages loading and querying the object_db.json file.
    It's designed to fail gracefully if the database is missing or corrupt.
    """

    def __init__(self, db_path: Path):
        # --- Service Setup ---
        self._db_path = db_path
        self._cache: dict | None = None
        self._user_notified_of_error = False

    # --- Public Methods ---
    def get_metadata_for_object(self, game_name: str, object_name: str) -> dict | None:
        """
        Flow 2.2: Finds metadata for a specific object, case-insensitively.
        MODIFIED: Searches within the 'objects' list of the specified game.
        """
        all_objects = self.get_all_objects_for_game(game_name)
        object_name_lower = object_name.lower()

        for obj in all_objects:
            if obj.get("name", "").lower() == object_name_lower:
                return obj

        return None


    def get_all_objects_for_game(self, game_name: str) -> list[dict]:
        """
        Flow 4.1.B: Returns a list of all object definitions for a specific game.
        MODIFIED: Now accesses the 'objects' key in the new data structure.
        """
        self._ensure_db_is_loaded()
        game_key = game_name.lower()

        if not self._cache or game_key not in self._cache:
            return []

        return self._cache[game_key].get("objects", [])

    def get_schema_for_game(self, game_name: str) -> dict | None:
        """
        NEW: Returns the entire schema dictionary for a specific game.
        This will be used to populate filter and dialog options.
        """
        self._ensure_db_is_loaded()
        game_key = game_name.lower() # Convert to lowercase for lookup

        if not self._cache or game_key not in self._cache:
            # This warning now only triggers if the key is genuinely not in the cache.
            logger.warning(f"Schema for game '{game_key}' not found in the database.")
            return None

        return self._cache[game_key].get("schema")

    def get_all_filter_options_for_game(self, game_name: str) -> dict[str, set]:
        """Flow 5.1: Gathers all possible values for filters (rarity, element, etc.)."""
        self._ensure_db_is_loaded()
        # Logic to iterate through all objects and collect unique values for each attribute.
        # e.g., returns {'rarity': {'5', '4'}, 'element': {'Pyro', 'Hydro'}, ...}
        return {}

    # --- Private/Internal Logic ---
    def _ensure_db_is_loaded(self):
        """A lazy-loader guard clause to ensure the database is loaded only once."""
        if self._cache is None:
            self._load_and_index_database()

    def get_all_game_types(self) -> list[str]:
        """Returns a list of all available game type keys from the database."""
        self._ensure_db_is_loaded()
        if not self._cache:
            return []
        return list(self._cache.keys())

    def _load_and_index_database(self):
        """
        Flow 6.5: (Private) Loads and indexes the JSON file.
        Handles errors gracefully and notifies the user only once on failure.
        """
        try:
            logger.info(f"Attempting to load database from: {self._db_path}")
            if not self._db_path.exists():
                raise FileNotFoundError(f"Database file not found at: {self._db_path}")

            with open(self._db_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # --- KOREKSI: Buat cache dengan kunci lowercase ---
            self._cache = {key.lower(): value for key, value in raw_data.items()}
            # ------------------------------------------------

            logger.info("Database loaded and cached successfully (case-insensitive).")

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load or parse database file. Error: {e}")
            self._cache = {}

            if not self._user_notified_of_error:
                global_signals.toast_requested.emit(
                    "Warning: database_object.json is missing or corrupted.",
                    "warning"
                )
                self._user_notified_of_error = True
