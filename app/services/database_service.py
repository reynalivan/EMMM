from difflib import SequenceMatcher
import json
from pathlib import Path

from app.utils.logger_utils import logger
from app.core.signals import global_signals

class DatabaseService:
    """
    Manages loading and querying the object_db.json file.
    It's designed to fail gracefully if the database is missing or corrupt.
    """

    def __init__(self, schema_path: Path, app_path: Path):
        # --- Service Setup ---
        self._schema_path = schema_path
        self._app_path = app_path
        self._schema_cache: dict | None = None
        self._original_game_keys: list[str] = []
        self._user_notified_of_error = False

    # --- Private/Internal Logic for Loading ---
    def _ensure_schema_is_loaded(self):
        """A lazy-loader guard clause to ensure the schema is loaded only once."""
        if self._schema_cache is None:
            self._load_schema_data()

    def _load_schema_data(self):
        """
        [REVISED] Loads and caches the schema.json file.
        This is the primary loading operation for this service.
        """
        try:
            logger.info(f"Attempting to load schema from: {self._schema_path}")
            if not self._schema_path.exists():
                raise FileNotFoundError(f"Schema file not found at: {self._schema_path}")

            with open(self._schema_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # Create a case-insensitive cache for the schema
            self._schema_cache = {key.lower(): value for key, value in raw_data.items()}
            self._original_game_keys = list(raw_data.keys())

            logger.info("Schema loaded and cached successfully (case-insensitive).")

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load or parse schema.json. Error: {e}")
            self._schema_cache = {}  # Set to empty dict to prevent further load attempts
            self._original_game_keys = []
            if not self._user_notified_of_error:
                global_signals.toast_requested.emit(
                    "Warning: schema.json is missing or corrupted. App functionality will be limited.",
                    "warning"
                )
                self._user_notified_of_error = True

    def _load_objects_from_file(self, file_path: Path) -> list[dict]:
        """
        [NEW HELPER] Safely loads a list of objects from a single JSON data file.
        """
        if not file_path.is_file():
            logger.warning(f"Object data file not found: {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Each file is expected to have a top-level "objects" key
            return data.get("objects", [])
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read or parse object data file {file_path}: {e}")
            return []

    # --- Public Methods for Schema ---
    def find_best_object_match(self, game_type: str, item_name: str) -> dict | None:
        """
        [NEW] Finds the best partial match for an item name against the database
        using string similarity.
        """
        all_objects = self.get_all_objects_for_game(game_type)
        if not all_objects:
            return None

        best_match = None
        highest_score = 0.0
        item_name_lower = item_name.lower()

        for db_obj in all_objects:
            db_name_lower = db_obj.get("name", "").lower()

            # Calculate similarity score based on name
            score = SequenceMatcher(None, item_name_lower, db_name_lower).ratio()

            # Boost score if tags also match
            tags = db_obj.get("tags", [])
            if any(item_name_lower in tag.lower() for tag in tags):
                score += 0.1 # Small boost for tag match

            if score > highest_score:
                highest_score = score
                best_match = db_obj

        if best_match:
            return {"match": best_match, "score": highest_score}

        return None

    def get_all_game_types(self) -> list[str]:
        """Returns a list of all available game type keys from the schema."""
        self._ensure_schema_is_loaded()
        return self._original_game_keys

    def get_schema_for_game(self, game_type: str) -> dict | None:
        """Returns the entire schema dictionary for a specific game."""
        self._ensure_schema_is_loaded()
        game_key = game_type.lower()

        if not self._schema_cache or game_key not in self._schema_cache:
            logger.warning(f"Schema for game '{game_key}' not found in the database.")
            return None

        return self._schema_cache[game_key].get("schema")

    # --- Stubs for Methods to be Implemented in Step 1.2 & 1.3 ---

    def get_all_objects_for_game(self, game_type: str) -> list[dict]:
        """
        'object_link' from the schema, then loads
        and combines data from all linked JSON files (e.g., char and other).
        """
        self._ensure_schema_is_loaded()
        game_key = game_type.lower()

        if not self._schema_cache or game_key not in self._schema_cache:
            return []

        game_schema_data = self._schema_cache.get(game_key, {})
        object_links = game_schema_data.get("object_link", {})

        if not object_links:
            logger.warning(f"No 'object_link' found in schema for game: {game_type}")
            return []

        all_objects = []
        # The base path for resolving relative paths in the JSON
        base_path = self._schema_path.parent

        for category, file_rel_path in object_links.items():
            # Construct the full, absolute path to the data file
            full_path = self._app_path / Path(file_rel_path)
            logger.info(f"Loading '{category}' objects for '{game_type}' from: {full_path}")

            # Load objects from the file and extend the main list
            objects_from_file = self._load_objects_from_file(full_path)
            all_objects.extend(objects_from_file)

        return all_objects

    def get_metadata_for_object(self, game_type: str, object_name: str) -> dict | None:
        """
        [REVISED] Finds metadata for a specific object, case-insensitively.
        """
        all_objects = self.get_all_objects_for_game(game_type)
        object_name_lower = object_name.lower()

        for obj in all_objects:
            if obj.get("name", "").lower() == object_name_lower:
                return obj

        return None

    def get_alias_for_game(self, game_type: str, key: str, fallback: str = None) -> str:
        """
        [REVISED for Step 1.3] Gets a display alias for a given key from the
        game's schema. Falls back to a capitalized version of the key if not found.
        """
        self._ensure_schema_is_loaded()
        game_key = game_type.lower()

        if self._schema_cache and game_key in self._schema_cache:
            game_schema_data = self._schema_cache.get(game_key, {})
            aliases = game_schema_data.get("alias", {})

            # Return the alias if it exists for the given key
            if key in aliases:
                return aliases[key]

        # Fallback logic if alias is not found
        return fallback if fallback else key.replace("_", " ").capitalize()
