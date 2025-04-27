class ModManagerError(Exception):
    """Base exception for all custom mod manager errors."""
    pass


class ConfigError(ModManagerError):
    """Raised when configuration file is missing or malformed."""
    pass
