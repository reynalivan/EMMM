# app/services/ini_parsing_service.py
from pathlib import Path
from dataclasses import dataclass, field
import uuid


@dataclass
class KeyBinding:
    """A mutable data class holding structured info from a parsed [Key...] section."""

    # --- Source Info ---
    section_name: str
    source_file: Path

    # Unique ID for tracking this specific binding instance in the UI
    binding_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # --- Editable Values ---
    key: str | None = None
    back: str | None = None
    default_value: str | None = None

    # --- Read-only Info ---
    type: str | None = None
    variable: str | None = None
    cycle_options: list[str] = field(default_factory=list)


class IniParsingService:
    """Parses, modifies, and writes 3DMigoto .ini files."""

    def __init__(self):
        # This service can be stateless.
        pass

    def parse_ini_files_in_folder(self, folder_path: Path) -> dict:
        """
        Flow 5.2 Part A: Finds and parses all .ini files within a folder.
        Returns a structured dictionary with the list of KeyBinding objects.
        """
        # 1. Recursively find all .ini files (max 4 levels deep).
        # 2. Parse [Constants] from all files to get default values.
        # 3. Parse [Key...] sections and create KeyBinding objects.
        # 4. Return {'success': True, 'data': [KeyBinding(...)]} or {'success': False, 'error': ...}.
        return {}

    def save_ini_changes(self, modified_bindings: list[KeyBinding]) -> dict:
        """
        Flow 5.2 Part D: Saves changes back to their respective source .ini files.
        Returns a structured dictionary with a list of any errors.
        """
        # 1. Group modified_bindings by source_file.
        # 2. For each file, perform a one-time backup (.ini.backup).
        # 3. Atomically read, modify, and write back the content for each file.
        # 4. Return {'success': True} or {'success': False, 'errors': [...]}.
        return {}
