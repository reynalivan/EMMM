# app/viewmodels/mixins/mod_status_mixin.py

import os
from typing import Union, Optional, Literal, Dict, Any
from PyQt6.QtCore import QTimer, pyqtSignal

from app.models.object_item_model import ObjectItemModel
from app.models.folder_item_model import FolderItemModel
from app.utils.logger_utils import logger
from app.utils.async_utils import AsyncStatusManager
from app.utils.signal_utils import safe_connect

ItemModelType = Union[ObjectItemModel, FolderItemModel]


class ModStatusMixin:
    """Mixin to handle mod enable/disable logic with UI feedback and status tracking."""

    def _connect_mod_status_signal(self):
        if not self._mod_manager:
            logger.warning(
                f"{self.__class__.__name__}: modManager not set. Status change ops disabled."
            )
            return

        safe_connect(
            self._mod_manager.modStatusChangeComplete,
            self._on_mod_status_changed,
            self,
        )

    def handle_item_status_toggle_request(
        self, item_model: ItemModelType, enable: bool
    ):
        if not item_model or not hasattr(item_model, "path"):
            logger.error(f"Invalid item_model in toggle request: {item_model}")
            return

        path = item_model.path
        if self._status_manager.is_item_pending(path):
            logger.debug(f"Toggle request ignored, already pending: {path}")
            return

        self._original_state_on_toggle[path] = {
            "display_name": item_model.display_name,
            "status": item_model.status,
        }

        self.pre_mod_status_change.emit(path)

        # Unwatch any subpaths before rename
        if self._file_watcher_service:
            for watched in list(self._file_watcher_service._watched_paths):
                if watched.startswith(path):
                    self._file_watcher_service.remove_path(watched)

        self._status_manager.mark_pending(path)
        self.setItemLoadingState.emit(path, True)
        self.operation_started.emit(path, f"{'Enabling' if enable else 'Disabling'}...")

        self._mod_manager.set_mod_enabled_async(path, enable, self._get_item_type())

    def _on_mod_status_changed(self, original_item_path: str, result: dict):
        """Handles async mod enable/disable result from ModManagementService."""
        if not getattr(self, "_is_handling_status_changes", False):
            logger.debug(f"{self.__class__.__name__}: Mod status change ignored.")
            return

        if self._get_item_type() != result.get("item_type"):
            logger.debug(f"{self.__class__.__name__}: Type mismatch; skipping result.")
            return

        success = result.get("success", False)
        new_path = result.get("new_path") or original_item_path
        final_status = result.get("new_status", False)
        original_status = result.get("original_status", False)
        actual_name = result.get("actual_name")
        error_msg = result.get("error")

        logger.debug(
            f"{self.__class__.__name__}: Mod result: {original_item_path} ➔ {new_path}, success={success}"
        )

        if success:
            self._status_manager.mark_success(original_item_path)
            self._suppressed_renames.add(os.path.normpath(new_path))
        else:
            self._status_manager.mark_failed(
                original_item_path, error_msg or "Unknown error"
            )

        original_state = self._original_state_on_toggle.pop(original_item_path, None)
        original_display_name = (
            original_state["display_name"]
            if original_state
            else os.path.basename(original_item_path)
        )

        definitive_status = final_status if success else original_status
        definitive_display_name = (
            os.path.basename(new_path)
            if definitive_status
            else (actual_name or original_display_name)
        )

        self.setItemLoadingState.emit(original_item_path, False)

        self.operation_finished.emit(
            original_item_path,
            new_path,
            (
                "Operation Failed"
                if not success
                else f"Mod {'Enabled' if definitive_status else 'Disabled'}"
            ),
            error_msg
            or f"'{definitive_display_name}' successfully {'enabled' if definitive_status else 'disabled'}.",
            success,
        )

        # After operation_finished emit
        if self._status_manager.is_all_done():
            if hasattr(self, "_emit_batch_summary_if_done"):
                self._emit_batch_summary_if_done()
            self.batchSummaryReady.emit(
                {
                    "success": self._status_manager.get_success_count(),
                    "failed": self._status_manager.get_fail_count(),
                }
            )
            self._status_manager.reset_count()

        if not success:
            if original_state:
                self.updateItemDisplay.emit(
                    original_item_path,
                    {
                        "path": original_item_path,
                        "display_name": original_state["display_name"],
                        "status": original_state["status"],
                    },
                )
            return

        # Update the model state
        found_model = next(
            (
                m
                for m in self._get_item_list()
                if os.path.normpath(m.path)
                in (os.path.normpath(original_item_path), os.path.normpath(new_path))
            ),
            None,
        )

        if found_model:
            found_model.status = definitive_status
            if os.path.normpath(found_model.path) != os.path.normpath(new_path):
                found_model.path = new_path
                found_model.folder_name = os.path.basename(new_path)
                self.request_thumbnail_for(found_model)

                if self._file_watcher_service:
                    logger.info(
                        f"{self.__class__.__name__}: Rebinding watcher after rename."
                    )
                    self.bind_filewatcher(self._file_watcher_service)

                if self._get_item_type() == "object":
                    self.objectItemPathChanged.emit(original_item_path, new_path)
        else:
            logger.warning(
                f"{self.__class__.__name__}: Model not found for {original_item_path}"
            )

        self._after_mod_status_change(original_item_path, new_path, result)
        QTimer.singleShot(1000, lambda: self._suppressed_renames.discard(new_path))

    def set_handling_status_changes(self, enabled: bool):
        """Enable/disable mod status change handler logic."""
        self._is_handling_status_changes = enabled
        logger.debug(f"{self.__class__.__name__}: Handling status change = {enabled}")
