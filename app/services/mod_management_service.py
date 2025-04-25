import os
import json
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Literal
from app.models.folder_item_model import FolderItemModel
from app.utils.async_utils import Worker, run_in_background
from app.core.constants import DISABLED_PREFIX, INFO_FILENAME
from app.utils.logger_utils import logger


class ModManagementService(QObject):
    # Sinyal
    safeModeApplyComplete = pyqtSignal(
        dict)  # summary{processed, changed, errors}
    modStatusChangeComplete = pyqtSignal(
        str, dict)  # item_path, result{success, new_path?, new_status?, error?}

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("ModManagementService initialized.")

    def applySafeModeChanges_async(self, items_to_check: list[FolderItemModel],
                                   new_safe_mode_state: bool):
        """
        Apply safe mode logic by renaming folders & updating last_status_active.
        """
        worker = Worker(self._applySafeModeChanges_task, items_to_check,
                        new_safe_mode_state)
        worker.result.connect(
            lambda summary: self.safeModeApplyComplete.emit(summary))
        run_in_background(worker)

    def _applySafeModeChanges_task(self, items: list[FolderItemModel],
                                   enable_safe_mode: bool) -> dict:
        processed = 0
        changed = 0
        errors = 0

        for item in items:
            processed += 1
            info_path = os.path.join(item.path, INFO_FILENAME)
            folder_name = os.path.basename(item.path)

            try:
                info = self._read_json_safe(info_path) or {}
            except Exception as e:
                logger.warning(f"Error reading {info_path}: {e}")
                errors += 1
                continue

            is_safe = info.get("is_safe", False)
            last_status = info.get("last_status_active", None)
            is_disabled = folder_name.lower().startswith(
                DISABLED_PREFIX.lower())

            # Enable Safe Mode → Disable Unsafe Items
            if enable_safe_mode and not is_safe and not is_disabled:
                info["last_status_active"] = True
                self._write_json_safe(info_path, info)
                self._rename_folder(item.path, True)
                changed += 1

            # Disable Safe Mode → Restore Last Status
            elif not enable_safe_mode and not is_safe and last_status is True and is_disabled:
                info["last_status_active"] = True
                self._write_json_safe(info_path, info)
                self._rename_folder(item.path, False)
                changed += 1

        logger.info(
            f"[SafeMode] Processed={processed} Changed={changed} Errors={errors}"
        )
        return {"processed": processed, "changed": changed, "errors": errors}

    def _rename_folder(self, item_path: str, to_disabled: bool):
        base_dir = os.path.dirname(item_path)
        current_name = os.path.basename(item_path)

        if to_disabled and not current_name.lower().startswith(
                DISABLED_PREFIX.lower()):
            new_name = DISABLED_PREFIX + current_name
        elif not to_disabled and current_name.lower().startswith(
                DISABLED_PREFIX.lower()):
            new_name = current_name[len(DISABLED_PREFIX):]
        else:
            logger.debug(f"[Rename] Skipped: {current_name}")
            return  # No change needed

        new_path = os.path.join(base_dir, new_name)

        if not os.path.exists(new_path):
            try:
                os.rename(item_path, new_path)
                logger.debug(f"[Rename] {item_path} → {new_path}")
            except Exception as e:
                logger.error(f"[Rename] Failed: {e}")
        else:
            logger.warning(f"[Rename] Target already exists: {new_path}")

    def _read_json_safe(self, file_path: str) -> dict | None:
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read JSON: {file_path} — {e}")
            return None

    def _write_json_safe(self, file_path: str, data: dict) -> bool:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to write JSON: {file_path} — {e}")
            return False
