# App/viewmodels/base item vm.py
import os
from typing import Set, Dict, Any, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from app.models.object_item_model import ObjectItemModel
from app.models.folder_item_model import FolderItemModel
from app.services.data_loader_service import DataLoaderService
from app.services.mod_management_service import ModManagementService
from app.services.thumbnail_service import ThumbnailService
from app.services.file_watcher_service import FileChangeEvent, FileWatcherService
from app.utils.async_utils import AsyncStatusManager
from app.utils.logger_utils import logger
from app.utils.signal_utils import safe_connect


from app.viewmodels.base.abstract_base import QObjectAbstractItemViewModel


class BaseItemViewModel(
    QObjectAbstractItemViewModel,
):
    """
    Base ViewModel for item lists, providing common functionality
    for loading state, enable/disable, and thumbnail handling.
    """

    # ---Signals ---
    batchSummaryReady = pyqtSignal(dict)  # { success: int, failed: int }
    displayListChanged = pyqtSignal(list)  # List[item model type]
    resetFilterState = pyqtSignal()
    loadingStateChanged = pyqtSignal(bool)  # Overall list loading
    pre_mod_status_change = pyqtSignal(str)  # path
    status_changed = pyqtSignal()
    showError = pyqtSignal(str, str)  # title, message
    objectItemPathChanged = pyqtSignal(str, str)  # (old_path, new_path)

    # For InfoBar notifications handled by the Panel
    operation_started = pyqtSignal(str, str)  # item_path (original), operation_title
    operation_finished = pyqtSignal(
        str, str, str, str, bool
    )  # original_path, final_path, title, content, success(bool)

    # For specific item UI state control handled by the Panel
    setItemLoadingState = pyqtSignal(
        str, bool
    )  # item_path (original or final), is_loading (bool)

    updateItemDisplay = pyqtSignal(
        str, dict
    )  # item_path (final), update_payload (dict: status, display_name, path)

    # Specific signal for thumbnail updates
    itemThumbnailNeedsUpdate = pyqtSignal(
        str, dict
    )  # item_path (original), thumbnail_result (dict from service)    # ---End Signals ---

    def __init__(
        self,
        data_loader: DataLoaderService,
        mod_manager: ModManagementService,
        thumbnail_service: ThumbnailService,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._data_loader = data_loader
        self._mod_manager = mod_manager
        self._thumbnail_service = thumbnail_service
        self._is_loading = False  # Overall list loading state
        self._suppressed_renames: Set[str] = set()
        self._is_handling_status_changes: bool = False

        # Temp storage for item state before toggle, used for revert on failure
        self._original_state_on_toggle: Dict[str, Dict[str, Any]] = {}
        self._status_manager = AsyncStatusManager(self)

        # File watcher initialization (moved from FileWatcherMixin)
        self._file_watcher_service: Optional[FileWatcherService] = None
        self._watched_paths: set[str] = set()
        self._pending_refresh_paths: set[str] = set()
        self._refresh_debounce_timer = QTimer(self)
        self._refresh_debounce_timer.setSingleShot(True)
        self._refresh_debounce_timer.setInterval(400)
        self._refresh_debounce_timer.timeout.connect(self._process_pending_refresh)

        self._connect_internal_signals()

    def _connect_internal_signals(self):
        self._connect_mod_status_signal()
        self._connect_thumbnail_signal()

    def _connect_file_watcher_signals(self):
        """Connect to file watcher service signals."""
        if self._file_watcher_service:
            safe_connect(
                self._file_watcher_service.fileBatchChanged,
                self._on_file_batch_changed,
                self,
            )

    def connect_status_signal(self):
        # Call from main.py
        if self._mod_manager:
            safe_connect(
                self._mod_manager.modStatusChangeComplete,
                self._on_mod_status_changed,
                self,
            )

    # File Watcher Methods (migrated from FileWatcherMixin)
    def _process_pending_refresh(self):
        """Debounced refresh executor."""
        if not self._pending_refresh_paths:
            return
        paths = list(self._pending_refresh_paths)
        self._pending_refresh_paths.clear()
        self._refresh_items_async(paths)

    def _refresh_items_async(self, paths: list[str]):
        if not paths:
            return
        context = self._get_current_path_context()
        if not context:
            logger.warning(f"{self.__class__.__name__}: No active context path.")
            return

        context = os.path.normpath(context)

        # refresh specific items
        updated = 0
        for p in paths:
            norm_path = os.path.normpath(p)
            item = next(
                (
                    i
                    for i in self._get_item_list()
                    if os.path.normpath(i.path) == norm_path
                ),
                None,
            )
            if item:
                try:
                    self.request_thumbnail_for(item)
                    self.updateItemDisplay.emit(
                        item.path,
                        {
                            "path": item.path,
                            "display_name": item.display_name,
                            "status": item.status,
                        },
                    )
                    updated += 1
                except Exception as e:
                    logger.warning(f"Failed to update display for {item.path}: {e}")

        if updated == 0:
            logger.info(
                f"{self.__class__.__name__}: No matching items, fallback reload."
            )
            self._load_items_for_path(context)
        else:
            logger.info(
                f"{self.__class__.__name__}: Updated {updated} item(s) directly."
            )

    def _on_file_batch_changed(self, folder_path: str, events: List[FileChangeEvent]):
        logger.info(
            f"{self.__class__.__name__}: Batch file change at {folder_path} ({len(events)} events)"
        )
        if self._get_item_type() != "object":
            logger.debug(
                f"{self.__class__.__name__}: Skipping file batch change – not object type."
            )
            return
        context_path = os.path.normpath(self._get_current_path_context() or "")
        if not os.path.commonpath([context_path, folder_path]) == context_path:
            logger.debug(
                f"{self.__class__.__name__}: Skipping batch – outside current context: {folder_path}"
            )
            return
        for evt in events:
            logger.debug(
                f"[{evt.event_type}] src={evt.src_path} → dest={evt.dest_path}"
            )
            if evt.event_type == "moved" and (
                os.path.normpath(evt.src_path) in self._suppressed_renames
                or os.path.normpath(evt.dest_path or "") in self._suppressed_renames
            ):
                logger.debug(
                    f"Ignoring suppressed rename event: {evt.src_path} → {evt.dest_path}"
                )
                continue
            if evt.event_type == "created":
                self._handle_file_created(evt.src_path)
            elif evt.event_type == "deleted":
                self._handle_file_deleted(evt.src_path)
            elif evt.event_type == "moved":
                self._handle_file_rename(evt.src_path, evt.dest_path)
            elif evt.event_type == "modified":
                self._pending_refresh_paths.add(evt.src_path)
        if not self._refresh_debounce_timer.isActive():
            self._refresh_debounce_timer.start()

    def _handle_file_created(self, path: str):
        logger.info(f"{self.__class__.__name__}: File created: {path}")
        loader = self._data_loader
        item_type = self._get_item_type()

        def _cb(result):
            if result and self._is_path_still_valid(path):
                self._insert_item_to_ui(result)

        if item_type == "object":
            loader.get_single_object_item_async(path, _cb)
        elif item_type == "folder":
            loader.get_single_folder_item_async(path, _cb)

    def _is_path_still_valid(self, path: str) -> bool:
        base = os.path.normpath(path)
        current = getattr(self, "_current_parent_path", None)
        return current and base.startswith(os.path.normpath(current))

    def _handle_file_deleted(self, path: str):
        logger.info(f"{self.__class__.__name__}: File deleted: {path}")
        self._remove_item_from_ui(path)

    def _handle_file_rename(self, src_path: str, dest_path: str):
        src_path_norm = os.path.normpath(src_path)
        dest_path_norm = os.path.normpath(dest_path)
        if not os.path.exists(dest_path_norm):
            logger.warning(f"Rename target is not a directory: {dest_path_norm}")
            return
        if src_path_norm == dest_path_norm:
            return

        if dest_path_norm in self._suppressed_renames:
            logger.debug(f"Watcher rename ignored (self): {dest_path_norm}")
            self._suppressed_renames.remove(dest_path_norm)
            return

        item = next(
            (
                i
                for i in self._get_item_list()
                if os.path.normpath(i.path) == src_path_norm
            ),
            None,
        )
        if not item:
            logger.warning(f"Rename target not found in model: {src_path}")
            return

        item.path = dest_path_norm
        item.folder_name = os.path.basename(dest_path_norm)

        from app.core.constants import DISABLED_PREFIX

        item.status = not item.folder_name.lower().startswith(DISABLED_PREFIX.lower())

        # Emit updates
        self.updateItemDisplay.emit(
            src_path_norm,
            {
                "path": dest_path_norm,
                "display_name": item.display_name,
                "status": item.status,
            },
        )

        if self._get_item_type() == "object":
            self.objectItemPathChanged.emit(src_path_norm, dest_path_norm)

        try:
            self.request_thumbnail_for(item)
        except Exception as e:
            logger.warning(f"Failed to refresh thumbnail for {item.path}: {e}")

        # Update watcher path if changed
        if self._file_watcher_service:
            old_parent = os.path.dirname(src_path_norm)
            new_parent = os.path.dirname(dest_path_norm)
            if old_parent != new_parent:
                self._file_watcher_service.remove_path(src_path_norm)
                self._watched_paths.discard(src_path_norm)
                if os.path.exists(dest_path_norm):
                    self._file_watcher_service.add_path(dest_path_norm)
                    self._watched_paths.add(dest_path_norm)

    def clear_refresh_queue(self, stop_only: bool = True):
        """Stop debounce + optionally clear pending queue."""
        self._refresh_debounce_timer.stop()
        if not stop_only:
            self._pending_refresh_paths.clear()

    # Mod Status Methods (migrated from ModStatusMixin)
    def _connect_mod_status_signal(self):
        """Connect to mod manager signals for status change operations."""
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

    def handle_item_status_toggle_request(self, item_model, enable: bool):
        """Handle mod enable/disable requests with UI feedback."""
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

                    # Handle path changes for object vs folder types
                    if self._get_item_type() == "object":
                        # Only one folder is watched → replace directly
                        self._file_watcher_service.remove_path(
                            os.path.dirname(original_item_path)
                        )
                        self._file_watcher_service.add_path(os.path.dirname(new_path))

                    elif self._get_item_type() == "folder":
                        # Watcher can have multi-path → update watched_paths
                        if os.path.isdir(original_item_path):
                            self._file_watcher_service.remove_path(original_item_path)
                            self._watched_paths.discard(original_item_path)

                        if os.path.isdir(new_path):
                            self._file_watcher_service.add_path(new_path)
                            self._watched_paths.add(new_path)

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

    # End Mod Status Methods

    # Thumbnail Methods (migrated from ThumbnailMixin)
    def _connect_thumbnail_signal(self):
        """Connect to thumbnail service signals."""
        if not self._thumbnail_service:
            logger.warning(
                f"{self.__class__.__name__}: No thumbnail service found in parent class."
            )
            return
        safe_connect(
            self._thumbnail_service.thumbnailReady,
            self._on_thumbnail_ready,
            self,
        )

    def request_thumbnail_for(self, item_model):
        """Request or emit cached thumbnail for a given item."""
        if not item_model or not self._thumbnail_service:
            return

        cached = self._thumbnail_service.get_cached_thumbnail(
            item_model.path, self._get_item_type()
        )
        if cached:
            self.itemThumbnailNeedsUpdate.emit(item_model.path, cached)
            return
        else:
            self._thumbnail_service.request_thumbnail(
                item_model.path, self._get_item_type()
            )

    def _on_thumbnail_ready(self, item_path: str, result: dict):
        """Handles thumbnail results and emits signal for UI update."""
        # logger.debug(f"Thumbnail ready for: {item_path}")
        self.itemThumbnailNeedsUpdate.emit(item_path, result)

    # End Thumbnail Methods

    # Item UI Helper Methods (migrated from ItemUIHelperMixin)
    def _insert_item_to_ui(self, item_model):
        """Insert new item to UI list and display."""
        items = self._get_item_list()
        norm_new = os.path.normpath(item_model.path)

        # check for stale insert
        if hasattr(self, "_current_parent_path"):
            current = getattr(self, "_current_parent_path") or ""
            if not norm_new.startswith(os.path.normpath(current)):
                logger.debug(
                    f"{self.__class__.__name__}: Ignored insert from stale path: {norm_new}"
                )
                return

        if any(os.path.normpath(i.path) == norm_new for i in items):
            logger.debug(
                f"{self.__class__.__name__}: Skip insert, already exists: {item_model.path}"
            )
            return

        items.append(item_model)
        if hasattr(self, "displayed_items"):
            self.displayed_items.append(item_model)

        self.request_thumbnail_for(item_model)
        self.displayListChanged.emit(self.displayed_items)

    def _remove_item_from_ui(self, path: str):
        """Remove item from UI list and display."""
        norm_path = os.path.normpath(path)
        items = self._get_item_list()

        removed = [i for i in items if os.path.normpath(i.path) == norm_path]
        if not removed:
            logger.debug(f"{self.__class__.__name__}: No match to remove: {path}")
            return

        for r in removed:
            items.remove(r)
            if hasattr(self, "displayed_items") and r in self.displayed_items:
                self.displayed_items.remove(r)

        logger.info(f"{self.__class__.__name__}: Removed item(s): {path}")
        self.displayListChanged.emit(self.displayed_items)

    def set_loading(self, is_loading: bool):
        """Emit loading state to UI if state changed."""
        if getattr(self, "_is_loading", False) != is_loading:
            self._is_loading = is_loading
            self.loadingStateChanged.emit(is_loading)

    # End Item UI Helper Methods
