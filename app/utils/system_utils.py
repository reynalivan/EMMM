# app/utils/system_utils.py
import os
import sys
import subprocess
from pathlib import Path


class SystemUtils:
    """A collection of static utility functions for OS-level interactions."""

    @staticmethod
    def open_path_in_explorer(path: Path):
        """Flow 4.3: Opens a directory path in the default system file explorer."""
        # Contains OS-specific logic (os.startfile for win32, open for darwin, etc.).
        # Wrapped in a try/except block to handle OS-level errors.
        pass

    @staticmethod
    def move_to_recycle_bin(path: Path):
        """Flow 4.2.B: Safely moves a file or folder to the system's recycle bin."""
        # This will use the 'send2trash' library for a safe, cross-platform delete.
        # This function will handle its own exceptions and return a success/error dict.
        pass
