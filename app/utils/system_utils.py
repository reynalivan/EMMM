# app/utils/system_utils.py
import os
import sys
import subprocess
from pathlib import Path
from send2trash import send2trash
from app.utils.logger_utils import logger
from app.core.signals import global_signals


class SystemUtils:
    """A collection of static utility functions for OS-level interactions."""

    @staticmethod
    def open_path_in_explorer(path: Path):
        """
        Flow 4.3: Opens a file or directory path in the default system file explorer.
        This function is cross-platform compatible.
        """
        if not path or not path.exists():
            error_msg = f"Path does not exist: {path}"
            logger.error(error_msg)
            global_signals.toast_requested.emit(error_msg, "error")
            return

        logger.info(f"Opening path: {path}")
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            error_msg = f"Failed to open path '{path}' in file explorer."
            logger.critical(f"{error_msg} Reason: {e}", exc_info=True)
            global_signals.toast_requested.emit(error_msg, "error")

    @staticmethod
    def move_to_recycle_bin(path: Path):
        """
        Flow 4.2.B: Safely moves a file or folder to the system's recycle bin.
        Returns True on success, False on failure.
        """
        if not path.exists():
            # No need to log an error here, the caller should handle it.
            return False
        try:
            send2trash(str(path))
            return True
        except Exception as e:
            # The caller should log this error with more context.
            print(
                f"Error moving {path} to recycle bin: {e}"
            )  # Use logger in production
            return False

    @staticmethod
    def get_initial_name(name: str, length: int = 2) -> str:
        """Flow 4.2.A: Returns the first 'length' characters of a name."""
        # This is used to generate initials for items without thumbnails.
        if not name:
            return "No Image"
        return name[:length].upper()
