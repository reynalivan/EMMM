# app/core/constants.py

# === APP INFO ===
APP_NAME: str = "Mods Manager"
APP_VERSION: str = "0.1.0"  # TODO: Consider fetching from a version file or build process

# === CONFIG ===
CONFIG_FILENAME: str = "config.ini"

# === DIRECTORIES ===
CACHE_DIR: str = "cache"
LOGS_DIR: str = "logs"

# === FILENAMES ===
LOG_FILENAME: str = "mods_manager.log"
PROPERTIES_FILENAME: str = "properties.json"  # For ObjectList items
INFO_FILENAME: str = "info.json"  # For FolderGrid items

# === THUMBNAILS ===
# Suffix for object thumbnails (used by service to search like *<SUFFIX>.<EXT>)
THUMBNAIL_OBJECT_SUFFIX: str = "thumb"
# Prefix for folder/preview thumbnails (used by service to search like <PREFIX>*.<EXT> with priority)
THUMBNAIL_FOLDER_PREFIX: str = "preview"
# Supported extensions for thumbnail image files
SUPPORTED_THUMB_EXTENSIONS: tuple[str,
                                  ...] = ("png", "jpg", "jpeg", "gif", "webp")
# Default name for generated/pasted preview thumbnails
DEFAULT_PREVIEW_FILENAME: str = "preview.png"  # Or use THUMBNAIL_FOLDER_PREFIX + .png

# === FILE SYSTEM RULES ===
DISABLED_PREFIX: str = "DISABLED "  # Note the trailing space

# === JSON KEYS (used for reading/writing properties.json and info.json) ===
KEY_ACTUAL_NAME: str = "actual_name"
KEY_IS_SAFE: str = "is_safe"
KEY_LAST_STATUS: str = "last_status_active"
KEY_PRESET_NAME: str = "preset_name"
KEY_DESCRIPTION: str = "description"
KEY_AUTHOR: str = "author"
# Metadata keys primarily for properties.json (ObjectList)
KEY_GENDER: str = "gender"
KEY_ROLES: str = "roles"
KEY_ELEMENT_TYPE: str = "element_type"
KEY_REGION: str = "region"
KEY_RELEASE_DATE: str = "release_date"

# === CONFIG SECTIONS/KEYS (for config.ini) ===
CONFIG_SECTION_GAMES: str = "Games"
CONFIG_SECTION_SETTINGS: str = "Settings"
CONFIG_KEY_LAST_GAME: str = "last_selected_game_name"
CONFIG_KEY_SAFE_MODE: str = "safe_mode_enabled"
# TODO: Add keys for future settings (e.g., window size, theme)

# === UI DEFAULTS ===
OBJECT_THUMB_SIZE_W: int = 64
OBJECT_THUMB_SIZE_H: int = 64
DEFAULT_THUMB_SIZE_W: int = 96  # Increased default size slightly
DEFAULT_THUMB_SIZE_H: int = 96
PLACEHOLDER_ICON_PATH: str = "app/assets/placeholder/placeholder.png"  # Define path for placeholder

# === CACHE SETTINGS ===
DEFAULT_CACHE_MAX_MB: int = 100
DEFAULT_CACHE_EXPIRY_DAYS: int = 30

# === LOGGING LEVELS (using string for Loguru compatibility) ===
LOG_LEVEL_FILE: str = "DEBUG"
LOG_LEVEL_CONSOLE: str = "INFO"
LOG_ROTATION: str = "10 MB"
LOG_RETENTION: str = "7 days"

# === TIMEOUT / DELAY ===
DEBOUNCE_INTERVAL_MS: int = 500  # Debounce for file watcher events
