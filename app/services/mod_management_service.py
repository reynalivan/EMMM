# app/services/mod_management_service.py

import os
import json
import shutil
from typing import Literal, Dict, Any, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool
import ctypes
import time
from app.core import constants
from app.utils.logger_utils import logger
from app.utils.async_utils import Worker


class ModManagementService(QObject):
    """Handles operations like enabling/disabling mods via folder renaming."""

    # --- Signals ---
    modStatusChangeComplete = pyqtSignal(str, dict)
    safeModeApplyComplete = pyqtSignal(dict)
    # TODO: Add signals for CRUD operations later

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        logger.debug("ModManagementService initialized.")

    # --- JSON Helper Methods ---

    def _read_json_safe(self, file_path: str) -> Dict[str, Any] | None:
        """Safely reads and parses a JSON file, returns None on error."""
        if not os.path.isfile(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            logger.warning(
                f"Failed to read/parse JSON '{os.path.basename(file_path)}': {e}"
            )
            return None

    def _write_json_safe(self, file_path: str, data: Dict[str, Any]) -> bool:
        """Safely writes data to a JSON file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)  # Use indent=4 for readability
            return True
        except (OSError, TypeError) as e:
            logger.error(
                f"Failed to write JSON '{os.path.basename(file_path)}': {e}",
                exc_info=True,
            )
            return False

    # --- Enable/Disable Logic ---

    def set_mod_enabled_async(
        self, item_path: str, enable: bool, item_type: Literal["object", "folder"]
    ):
        """Asynchronously enables/disables a mod item via folder rename."""
        logger.info(
            f"Request received: {'Enable' if enable else 'Disable'} '{item_path}' (Type: {item_type})"
        )

        # Basic validation before starting task
        if not item_path or not os.path.isdir(item_path):
            logger.error(f"Path is not a valid directory: {item_path}")
            result = {
                "success": False,
                "new_path": None,
                "new_status": None,
                "original_status": None,
                "actual_name": None,
                "item_type": item_type,
                "error": "Task error: Invalid directory path or other validation failure.",
            }
            # Emit completion signal immediately for invalid input
            self.modStatusChangeComplete.emit(item_path, result)
            return

        # Create and run the background worker
        logger.debug(
            f"Background task for set_mod_enabled_async started for '{item_path}' (Type: {item_type})"
        )
        worker = Worker(self._set_mod_enabled_task, item_path, enable, item_type)

        def _on_result(result_dict):
            logger.info(
                f"set_mod_enabled_async result for '{item_path}': {result_dict}"
            )
            result_dict["item_type"] = item_type  # Tambahkan item_type langsung
            self.modStatusChangeComplete.emit(item_path, result_dict)

        def _on_error(err_info):
            logger.error(
                f"set_mod_enabled_async error for {item_path}: {err_info}",
                exc_info=True,
            )
            self.modStatusChangeComplete.emit(
                item_path,
                {
                    "success": False,
                    "new_path": None,
                    "new_status": None,
                    "original_status": None,
                    "actual_name": None,
                    "item_type": item_type,
                    "error": f"Task Error: {err_info[1]}",
                },
            )

        worker.signals.result.connect(_on_result)
        worker.signals.error.connect(_on_error)
        QThreadPool.globalInstance().start(worker)

    def _set_mod_enabled_task(
        self, original_path: str, enable: bool, item_type: Literal["object", "folder"]
    ) -> Dict[str, Any]:
        """
        Background task for enable/disable via folder rename.
        Handles JSON update for 'actual_name' on disable (best effort).
        Returns detailed result dictionary including original status and item type.
        """
        logger.debug(
            f"Background task _set_mod_enabled_task started for '{original_path}' (Type: {item_type})"
        )
        prefix = constants.DISABLED_PREFIX
        current_folder_name = os.path.basename(original_path)
        is_currently_disabled = current_folder_name.lower().startswith(prefix.lower())
        original_status = not is_currently_disabled  # Status BEFORE operation
        target_status = enable
        actual_name = (  # Base name without prefix
            current_folder_name[len(prefix) :]
            if is_currently_disabled
            else current_folder_name
        )
        new_folder_name = ""
        new_path = None
        error_msg = None
        success = False

        # Check if already in the desired state
        if original_status == target_status:
            logger.debug(
                f"Folder '{current_folder_name}' already has desired state (disable={target_status})."
            )
            return {
                "success": True,
                "new_path": original_path,
                "new_status": target_status,
                "original_status": original_status,
                "actual_name": actual_name,
                "item_type": item_type,
                "error": None,
            }

        # Determine paths and names
        base_dir = os.path.dirname(original_path)
        if target_status is True:  # Enabling: new name is actual_name
            new_folder_name = actual_name
        else:  # Disabling: new name is prefix + actual_name
            new_folder_name = prefix + actual_name
        new_path = os.path.join(base_dir, new_folder_name)
        logger.debug(f"New folder name: {new_folder_name}")

        try:
            # Handle JSON only when disabling (best effort)
            if target_status is False:  # Disabling
                json_filename = (
                    constants.INFO_FILENAME
                    if item_type == "folder"
                    else constants.PROPERTIES_FILENAME
                )
                json_path = os.path.join(
                    original_path, json_filename
                )  # JSON is in the *original* folder path

                json_data = self._read_json_safe(json_path) or {}
                if json_data.get(constants.KEY_ACTUAL_NAME) != actual_name:
                    json_data[constants.KEY_ACTUAL_NAME] = actual_name
                    self._write_json_safe(json_path, json_data)

            # Rename check
            if os.path.exists(new_path):
                error_msg = f"Rename failed: Target '{new_folder_name}' already exists."
            else:
                logger.debug(
                    f"Renaming '{current_folder_name}' to '{new_folder_name}'..."
                )
                # Correct clean actual name first
                clean_actual_name = actual_name.lstrip()  # In case ada spasi sisa

                # New folder name logic
                if target_status is True:  # Enabling
                    new_folder_name = clean_actual_name
                else:  # Disabling
                    new_folder_name = prefix + clean_actual_name

                # Rename folder
                if ModManagementService._is_folder_locked(original_path):
                    error_msg = f"Rename blocked: Folder '{original_path}' is in use."
                    logger.warning(error_msg)
                    return {
                        "success": False,
                        "new_path": None,
                        "new_status": original_status,
                        "original_status": original_status,
                        "actual_name": actual_name,
                        "item_type": item_type,
                        "error": error_msg,
                    }
                os.rename(original_path, new_path)
                success = True
                logger.info(
                    f"Task: Rename successful: '{original_path}' -> '{new_path}'"
                )

        except OSError as e:
            error_msg = f"OS Error during rename: {e}"
            logger.error(error_msg, exc_info=True)
            success = False
        except Exception as e:
            error_msg = f"Unexpected error during rename/JSON handling: {e}"
            logger.error(error_msg, exc_info=True)
            success = False

        # Determine final state for result dict
        final_path = new_path if success else original_path
        final_status = target_status if success else original_status

        return {
            "success": success,
            "new_path": final_path,
            "new_status": final_status,
            "original_status": original_status,  # Include original status
            "actual_name": actual_name,  # Base name (useful for display on disable)
            "item_type": item_type,  # Include item type
            "error": error_msg,
        }

    # --- Safe Mode Logic (Sudah ada sebelumnya, pastikan signature cocok jika perlu) ---
    def applySafeModeChanges_async(
        self, items_to_check: list, new_safe_mode_state: bool
    ):
        logger.info(
            f"Requesting apply safe mode changes. New state: {new_safe_mode_state}"
        )
        # Use the same Worker pattern
        worker = Worker(
            self._applySafeModeChanges_task, items_to_check, new_safe_mode_state
        )
        worker.signals.result.connect(
            lambda summary: self.safeModeApplyComplete.emit(summary)
        )

        worker.signals.error.connect(
            lambda err_info: logger.error(f"Error in safe mode task: {err_info[1]}")
            # Optionally emit a generic error signal? For now just log.
        )
        QThreadPool.globalInstance().start(worker)

    def _applySafeModeChanges_task(self, items: list, enable_safe_mode: bool) -> dict:
        # NOTE: This task might need internal calls to the _set_mod_enabled_task logic
        # or directly perform similar rename/JSON operations based on 'is_safe' key.
        # Reusing _set_mod_enabled_task might be complex due to state checks.
        # Keeping the previous direct implementation for now. Needs review.
        logger.debug(
            f"Task started: Apply safe mode changes (enable={enable_safe_mode})"
        )
        processed = 0
        changed = 0
        errors = 0
        prefix_lower = constants.DISABLED_PREFIX.lower()

        for item in items:  # Assuming item is FolderItemModel
            processed += 1
            info_path = os.path.join(item.path, constants.INFO_FILENAME)
            folder_name = os.path.basename(
                item.path
            )  # item.folder_name should also work

            try:
                info = self._read_json_safe(info_path) or {}
            except Exception as e:
                logger.warning(f"Error reading {info_path} during safe mode task: {e}")
                errors += 1
                continue

            is_marked_safe = info.get(
                constants.KEY_IS_SAFE, False
            )  # Default unsafe if key missing
            last_status = info.get(constants.KEY_LAST_STATUS, None)
            is_folder_disabled = folder_name.lower().startswith(prefix_lower)
            is_folder_enabled = not is_folder_disabled

            needs_rename = False
            make_disabled = False  # Target state for rename helper

            if enable_safe_mode:
                # If safe mode is ON, disable any item marked as NOT safe that is currently enabled
                if not is_marked_safe and is_folder_enabled:
                    logger.debug(f"Safe Mode ON: Disabling unsafe item '{folder_name}'")
                    info[constants.KEY_LAST_STATUS] = True  # Store that it was active
                    self._write_json_safe(info_path, info)  # Save status before rename
                    needs_rename = True
                    make_disabled = True
            else:  # enable_safe_mode is False
                # If safe mode is OFF, re-enable items marked as NOT safe IF they were last active
                if not is_marked_safe and last_status is True and is_folder_disabled:
                    logger.debug(
                        f"Safe Mode OFF: Re-enabling previously active unsafe item '{folder_name}'"
                    )
                    # We don't need to change KEY_LAST_STATUS back here, just rename
                    # Or maybe clear it? Let's leave it as True.
                    needs_rename = True
                    make_disabled = False

            if needs_rename:
                try:
                    # Call internal rename helper
                    success, _ = self._rename_folder_for_status(
                        item.path, make_disabled
                    )
                    if success:
                        changed += 1
                    else:
                        errors += 1
                except Exception as e:
                    logger.error(
                        f"Error renaming folder during safe mode apply for {item.path}: {e}"
                    )
                    errors += 1

        logger.info(
            f"[SafeMode Task] Processed={processed} Changed={changed} Errors={errors}"
        )
        return {"processed": processed, "changed": changed, "errors": errors}

    def _rename_folder_for_status(
        self, item_path: str, disable: bool
    ) -> tuple[bool, Optional[str]]:
        """Internal helper to rename folder based on target status (disable=True/False)."""
        prefix = constants.DISABLED_PREFIX
        is_currently_disabled = (
            os.path.basename(item_path).lower().startswith(prefix.lower())
        )
        base_dir = os.path.dirname(item_path)
        current_name = os.path.basename(item_path)
        new_name = None
        new_path = None

        if disable and not is_currently_disabled:
            # Read JSON first to get potential actual_name, though we use current_name here
            # json_path = os.path.join(item_path, ...) # Determine JSON path based on type? Need item_type here!
            # For simplicity in this helper, just use current_name
            new_name = prefix + current_name
        elif not disable and is_currently_disabled:
            if current_name.lower().startswith(prefix.lower()):
                new_name = current_name[len(prefix) :]
            else:  # Cannot determine original name if prefix varies
                logger.warning(
                    f"Cannot enable '{current_name}', prefix mismatch or non-standard."
                )
                return False, None  # Cannot proceed reliably

        if new_name is None:  # Already in desired state or error case above
            # logger.debug(f"Rename skipped: Folder '{current_name}' already has desired state (disable={disable}).")
            return True, item_path  # Considered success as state matches

        new_path = os.path.join(base_dir, new_name)

        if os.path.exists(new_path):
            logger.error(f"Rename failed: Target path '{new_path}' already exists.")
            return False, None

        try:
            self.retry_rename(item_path, new_path)
            logger.debug(f"Renamed via helper: '{item_path}' -> '{new_path}'")
            return True, os.path.normpath(new_path)

        except OSError as e:
            logger.error(f"Rename failed via helper (OS Error): {e}")
            return False, None

    @staticmethod
    def _is_folder_locked(path: str) -> bool:
        """Check if folder is locked by trying to rename temporarily."""
        try:
            test_path = path + "_lock_test"
            os.rename(path, test_path)
            os.rename(test_path, path)
            return False
        except Exception as e:
            logger.warning(f"Folder lock check failed: {e}")
            return True

    @staticmethod
    def retry_rename(
        src: str, dest: str, max_retries: int = 5, delay: float = 0.5
    ) -> bool:
        """Tries to rename with retries to handle temporary file locks."""
        for attempt in range(max_retries):
            try:
                os.rename(src, dest)
                return True
            except OSError as e:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    raise e
        return False

    # TODO: Implement _ensure_json_exists helper? Might be combined with _read/_write.

    # TODO: Implement methods for create, rename (user initiated), delete, update info/properties
