# app/core/constants.py
import re

# --- Application Info ---
APP_NAME: str = "EMM Manager"
ORG_NAME: str = "reynalivan"
APP_ICON_PATH: str = "app/assets/icons/logo.png"
APP_VERSION: str = "0.0.1"

# --- Folder Naming Conventions ---
DISABLED_PREFIX_PATTERN = re.compile(r"^(disabled)[\s_]+", re.IGNORECASE)
DEFAULT_DISABLED_PREFIX: str = "DISABLED "
PIN_SUFFIX: str = "_pin"

# --- File & Directory Names ---
CONFIG_FILE_NAME: str = "config.ini"
DATABASE_FILE_NAME: str = "database_object.json"
CACHE_DIR_NAME: str = "cache"
LOG_DIR_NAME: str = "logs"
PROPERTIES_JSON_NAME: str = "properties.json"  # For objectlist items
INFO_JSON_NAME: str = "info.json"  # For foldergrid items
INI_BACKUP_EXTENSION: str = ".backup"

# --- Thumbnail & Image Constants ---
PREVIEW_IMAGE_BASE_NAME: str = "preview"
OBJECT_THUMBNAIL_NAME: str = "thumb"
SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")
DEFAULT_ICONS: dict[str, str] = {
    "mod": "app/assets/images/default_mod_icon.png",
    "folder": "app/assets/images/default_folder_icon.png",
    "object": "app/assets/images/default_object_icon.png",
}

# --- UI & Interaction Constants ---
DEBOUNCE_DELAY_MS: int = 300
CONTEXT_OBJECTLIST: str = "objectlist"
CONTEXT_FOLDERGRID: str = "foldergrid"

# --- .ini File Parsing Constants ---
INI_CONSTANTS_SECTION: str = "Constants"
