# App/viewmodels/base item vm.py


import os
from abc import ABCMeta, abstractmethod
from typing import Literal, Set, Union, Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal

# Adjust import paths as needed

from app.models.object_item_model import ObjectItemModel
from app.models.folder_item_model import FolderItemModel
from app.services.data_loader_service import DataLoaderService
from app.services.mod_management_service import ModManagementService
from app.services.thumbnail_service import ThumbnailService
from app.core import constants
from app.utils.async_utils import AsyncStatusManager
from app.utils.logger_utils import logger
from abc import ABCMeta, abstractmethod
from typing import Optional
from app.services.file_watcher_service import FileChangeEvent, FileWatcherService
from PyQt6.QtCore import QTimer

ItemModelType = Union[ObjectItemModel, FolderItemModel]


class QObjectABCMeta(type(QObject), ABCMeta):
    pass


class BaseItemViewModel(QObject, metaclass=QObjectABCMeta):
    """
    Base ViewModel for item lists, providing common functionality
    for loading state, enable/disable, and thumbnail handling.
    """

    # ---Signals ---

    displayListChanged = pyqtSignal(list)  # List[item model type]

    loadingStateChanged = pyqtSignal(bool)  # Overall list loading

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
    )  # item_path (original), thumbnail_result (dict from service)

    # ---End Signals ---

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

        self._is_handling_status_changes: bool = False

        # Temp storage for item state before toggle, used for revert on failure

        self._original_state_on_toggle: Dict[str, Dict[str, Any]] = {}
        self._status_manager = AsyncStatusManager(self)
        self._connect_internal_signals()

        self._file_watcher_service: Optional[FileWatcherService] = None
        self._watched_paths: set[str] = set()
        self._pending_changed_paths: set[str] = set()
        self._debounce_timer: Optional[QTimer] = None

        self._pending_refresh_paths: Set[str] = set()
        self._refresh_debounce_timer = QTimer(self)
        self._refresh_debounce_timer.setSingleShot(True)
        self._refresh_debounce_timer.timeout.connect(self._process_pending_refresh)

    # ---Abstract Methods ---

    @abstractmethod
    def _get_item_list(self) -> List[ItemModelType]:
        """Return the internal list of all item models for the current view."""
        raise NotImplementedError

    @abstractmethod
    def _get_item_type(self) -> Literal["object", "folder"]:
        """Return 'object' or 'folder' depending on the subclass."""
        raise NotImplementedError

    @abstractmethod
    def _filter_and_sort(self):
        """Apply filters/sorts and emit displayListChanged."""
        raise NotImplementedError

    @abstractmethod
    def _load_items_for_path(self, path: Optional[str]):
        """Load items for the specific context (game path or folder path)."""
        raise NotImplementedError

    @abstractmethod
    def _get_current_path_context(self) -> Optional[str]:
        """Return the current relevant path for context/refresh."""
        raise NotImplementedError

    # ---End Abstract Methods ---

    def _connect_internal_signals(self):
        """Connect internal service signals."""
        try:
            if self._mod_manager:
                self._mod_manager.modStatusChangeComplete.connect(
                    self._on_mod_status_changed
                )

            if self._thumbnail_service:
                self._thumbnail_service.thumbnailReady.connect(self._on_thumbnail_ready)

            if self._file_watcher_service:
                self._file_watcher_service.fileChanged.connect(self._on_file_changed)

            self._file_watcher_service.fileBatchChanged.connect(
                self._on_file_batch_changed
            )

        except Exception as e:
            logger.error(
                f"Error connecting internal signals in {self.__class__.__name__}: {e}",
                exc_info=True,
            )

    # ---Public Slots /Methods ---

    def handle_item_status_toggle_request(
        self, item_model: ItemModelType, enable: bool
    ):
        """Handle UI request to toggle enabled/disabled status of an item."""
        try:
            if not item_model or not hasattr(item_model, "path"):
                logger.error(
                    f"Invalid item_model in handle_item_status_toggle_request: {item_model}"
                )
                return

            path = item_model.path

            if self._status_manager.is_item_pending(path):
                logger.debug(f"Toggle request ignored, item already pending: {path}")
                return  # Ignore duplicate request while pending

            # Save original state for possible revert

            self._original_state_on_toggle[path] = {
                "display_name": item_model.display_name,
                "status": item_model.status,
            }

            # Mark as pending

            self._status_manager.mark_pending(path)

            # Emit loading to UI

            self.setItemLoadingState.emit(path, True)
            self.operation_started.emit(
                path, f"{'Enabling' if enable else 'Disabling'}..."
            )

            # Call async service

            self._mod_manager.set_mod_enabled_async(path, enable, self._get_item_type())

        except Exception as e:
            logger.error(
                f"Error in handle_item_status_toggle_request: {e}", exc_info=True
            )

    def request_thumbnail_for(self, item_model: ItemModelType):
        """Requests thumbnail for a specific item."""
        if not item_model or not self._thumbnail_service:
            return
        item_type = self._get_item_type()
        self._thumbnail_service.get_thumbnail_async(item_model.path, item_type)

    # ---Internal Slots ---

    def _on_mod_status_changed(self, original_item_path: str, result: dict):
        """
        Handles async status change results. Updates UI and internal model accordingly.
        """

        if not self._is_handling_status_changes:
            logger.debug(f"{self.__class__.__name__}: Mod status change ignored.")
            return

        if self._get_item_type() != result.get("item_type"):
            logger.debug(
                f"{self.__class__.__name__}: Type mismatch, ignoring mod change."
            )
            return

        success = result.get("success", False)
        new_path = result.get("new_path") or original_item_path
        final_status = result.get("new_status", False)
        original_status = result.get("original_status", False)
        actual_name = result.get("actual_name")
        error_msg = result.get("error")

        logger.debug(
            f"{self.__class__.__name__}: Processing mod result: {original_item_path} ➔ {new_path}, success={success}"
        )

        if success:
            self._status_manager.mark_success(original_item_path)
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

        # ---Emit UI Update ---

        self.updateItemDisplay.emit(
            original_item_path,
            {
                "status": definitive_status,
                "display_name": definitive_display_name,
                "path": new_path,
            },
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

        if not success:
            return

        # ---Update Model ---

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
                self._update_item_thumbnail(found_model)

                # ---Important: Rebind file watcher after rename ---

                if self._file_watcher_service:
                    logger.info(
                        f"{self.__class__.__name__}: Path changed, rebinding watcher."
                    )
                    self.bind_filewatcher(self._file_watcher_service)

                # ---Emit notification for others (optional) ---

                self.objectItemPathChanged.emit(original_item_path, new_path)

        else:
            logger.warning(
                f"{self.__class__.__name__}: Updated model not found for {original_item_path}."
            )

    def _on_thumbnail_ready(self, item_path: str, result: dict):
        """Handles thumbnail results and emits signal for UI update."""
        # Emit specific signal for thumbnails

        self.itemThumbnailNeedsUpdate.emit(item_path, result)

    def set_loading(self, is_loading: bool):
        """Sets the overall loading state for the list/grid."""
        # Manages the loading state for the whole list (e.g., when changing games)

        if self._is_loading != is_loading:
            self._is_loading = is_loading
            self.loadingStateChanged.emit(is_loading)

    def set_handling_status_changes(self, enabled: bool):
        """Enable or disable handling of mod status changes."""
        self._is_handling_status_changes = enabled
        logger.debug(
            f"{self.__class__.__name__}: set_handling_status_changes({enabled})"
        )

    def _refresh_folder_grid_items(self):
        """Refreshes the list of folder grid items."""
        logger.debug(f"{self.__class__.__name__}: Refreshing folder grid items.")
        # TODO Implement refresh logic for folder grid items

    def _refresh_folder_grid_breadcrumbs(self):
        """Refreshes the list of folder grid breadcrumbs."""
        logger.debug(f"{self.__class__.__name__}: Refreshing folder grid breadcrumbs.")
        # TODO Implement refresh logic for folder grid breadcrumbs

    def _update_item_thumbnail(self, item_model: ItemModelType):
        """Helper method to request reloading thumbnail for a specific item."""
        if item_model and self._thumbnail_service:
            self.request_thumbnail_for(item_model)

    def bind_filewatcher(self, file_watcher_service: FileWatcherService):
        """Setup file watcher based on current active path."""
        if not file_watcher_service:
            logger.warning(f"{self.__class__.__name__}: No file watcher service.")
            return

        self._file_watcher_service = file_watcher_service

        active_path = self._get_current_path_context()
        if not active_path or not os.path.exists(active_path):
            logger.warning(
                f"{self.__class__.__name__}: Invalid context path for watcher."
            )
            return

        if file_watcher_service.is_watching_path(active_path):
            logger.debug(f"{self.__class__.__name__}: Already watching {active_path}.")
            return

        # Start the thread if needed

        if (
            not file_watcher_service._thread
            or not file_watcher_service._thread.isRunning()
        ):
            logger.info(f"{self.__class__.__name__}: Starting file watcher thread.")
            file_watcher_service.start()

        # ---Important: Connect batch changed handler! ---

        file_watcher_service.fileBatchChanged.connect(self._on_file_batch_changed)

        # Clear old watched paths

        for path in self._watched_paths.copy():
            file_watcher_service.remove_path(path)
        self._watched_paths.clear()

        # Add new watch

        file_watcher_service.add_path(active_path)
        self._watched_paths.add(active_path)

        logger.info(f"{self.__class__.__name__}: Watching {active_path}")

    def unbind_filewatcher(self):
        """Unbinds the file watcher and clears watched paths."""
        logger.info(f"{self.__class__.__name__}: Unbinding file watcher...")
        if self._file_watcher_service:
            for path in self._watched_paths:
                self._file_watcher_service.remove_path(path)
            self._watched_paths.clear()
            try:
                self._file_watcher_service.fileChanged.disconnect(self._on_file_changed)
            except Exception:
                pass  # Safe ignore

            logger.info(f"{self.__class__.__name__}: Unbound file watcher.")

    def _on_file_changed(self, path: str):
        """Handles when a file is created, deleted, or modified."""
        logger.debug(f"{self.__class__.__name__}: Detected file change at {path}")
        if not path:
            return

        # Save the Path String Ordinary

        self._pending_changed_paths.add(path)

        # Setup debounce timer

        if self._debounce_timer is None:
            self._debounce_timer = QTimer(self)
            self._debounce_timer.setSingleShot(True)
            self._debounce_timer.setInterval(500)
            self._debounce_timer.timeout.connect(self._process_pending_file_changes)

        # Start timer

        if not self._debounce_timer.isActive():
            self._debounce_timer.start()

    def _process_pending_file_changes(self):
        """Processes pending file change events after debounce."""
        if not self._pending_changed_paths:
            return

        paths_to_process = list(self._pending_changed_paths)
        self._pending_changed_paths.clear()

        logger.debug(
            f"{self.__class__.__name__}: Processing {len(paths_to_process)} changed paths."
        )

        self._refresh_object_items(paths_to_process)
        self._refresh_folder_grid_if_needed(paths_to_process)

    def _refresh_object_items(self, paths: list[str]):
        """Refresh object items if their path matches any changed paths."""
        if not paths:
            return

        logger.debug(
            f"{self.__class__.__name__}: Checking object items against {len(paths)} changed paths."
        )

        updated = False
        normalized_changed_paths = {os.path.normpath(p) for p in paths}

        for item in self._get_item_list():
            item_path = os.path.normpath(item.path)

            # Check whether item_path is in normalized_changed_paths

            for changed_path in normalized_changed_paths:
                if changed_path == item_path or changed_path.startswith(item_path):
                    logger.debug(
                        f"{self.__class__.__name__}: Updating item {item_path}"
                    )
                    self._update_item_thumbnail(item)  # Update thumbnail

                    updated = True
                    break  # No need to check anymore for this item

        if updated:
            self._filter_and_sort()  # Emit updated list ke UI

    def _refresh_folder_grid_if_needed(self, paths: list[str]):
        """Refresh folder grid view if the active folder is impacted."""
        if not paths:
            return

        logger.debug(
            f"{self.__class__.__name__}: Checking folder grid against changed paths."
        )

        active_folder_path = self._get_current_path_context()
        if not active_folder_path:
            logger.debug(f"{self.__class__.__name__}: No active folder, skip refresh.")
            return

        active_folder_path = os.path.normpath(active_folder_path)
        normalized_changed_paths = {os.path.normpath(p) for p in paths}

        for changed_path in normalized_changed_paths:
            if changed_path.startswith(active_folder_path):
                logger.info(
                    f"{self.__class__.__name__}: Active folder impacted, refreshing grid."
                )
                self._load_items_for_path(
                    active_folder_path
                )  # Reload content dari active folder

                return  # Just have to refresh once

    def _refresh_breadcrumbs_if_needed(self, src_path: str, dest_path: str):
        """Update breadcrumb if current folder path was renamed."""
        active_path = self._get_current_path_context()

        if not active_path:
            return

        src_path = os.path.normpath(src_path)
        dest_path = os.path.normpath(dest_path)
        active_path = os.path.normpath(active_path)

        if active_path.startswith(src_path):
            # If breadcrumb is active impacted

            new_active_path = active_path.replace(src_path, dest_path, 1)
            self._set_current_path_context(new_active_path)

            logger.info(
                f"{self.__class__.__name__}: Breadcrumb updated to {new_active_path}"
            )

            self._refresh_folder_grid_items()
            self._refresh_folder_grid_breadcrumbs()

    def _refresh_items_async(self, paths: list[str]):
        """Refresh object/folder items selectively based on changed paths."""
        if not paths:
            return

        logger.debug(f"{self.__class__.__name__}: Checking refresh for paths: {paths}")

        active_context = self._get_current_path_context()
        if not active_context:
            logger.warning(f"{self.__class__.__name__}: No active path context.")
            return

        active_context = os.path.normpath(active_context)
        affected_folders = {os.path.normpath(os.path.dirname(p)) for p in paths}

        should_reload = any(
            folder.startswith(active_context) for folder in affected_folders
        )

        if should_reload:
            logger.info(f"{self.__class__.__name__}: Changes detected, reloading...")
            self._load_items_for_path(active_context)
        else:
            logger.debug(
                f"{self.__class__.__name__}: No changes relevant to current view."
            )

    def _handle_file_rename(self, src_path: str, dest_path: str):
        """Handles when a file or folder is renamed externally, including breadcrumb update."""
        logger.info(
            f"{self.__class__.__name__}: Rename detected: {src_path} ➔ {dest_path}"
        )

        src_path_norm = os.path.normpath(src_path)
        dest_path_norm = os.path.normpath(dest_path)

        # 1. Find a path model match

        target_model = next(
            (
                item
                for item in self._get_item_list()
                if os.path.normpath(item.path) == src_path_norm
            ),
            None,
        )

        if not target_model:
            logger.warning(
                f"{self.__class__.__name__}: No matching model for {src_path}"
            )
            return

        # 2. Update the path model and name

        target_model.path = dest_path_norm
        target_model.folder_name = os.path.basename(dest_path_norm)

        logger.debug(f"{self.__class__.__name__}: Model updated to {dest_path_norm}")

        if hasattr(self, "gridWidget") and self.gridWidget:
            self.gridWidget.updateItemPath(src_path_norm, dest_path_norm)

        # 3. UI Signal Emit for Specific Item Update

        self.updateItemDisplay.emit(
            src_path_norm,
            {
                "path": dest_path_norm,
                "display_name": os.path.basename(dest_path_norm),
                "status": target_model.status,
            },
        )

        # 4. Refresh thumbnail

        self._update_item_thumbnail(target_model)

        # 5. Update file watcher paths

        if self._file_watcher_service:
            old_parent = os.path.dirname(src_path_norm)
            new_parent = os.path.dirname(dest_path_norm)

            # Only rebind watcher if you move the parent folder

            if old_parent != new_parent:
                if src_path_norm in self._watched_paths:
                    self._file_watcher_service.remove_path(src_path_norm)
                    self._watched_paths.remove(src_path_norm)
                    logger.info(
                        f"{self.__class__.__name__}: Removed old watch {src_path_norm}"
                    )

                if os.path.exists(dest_path_norm):
                    self._file_watcher_service.add_path(dest_path_norm)
                    self._watched_paths.add(dest_path_norm)
                    logger.info(
                        f"{self.__class__.__name__}: Added new watch {dest_path_norm}"
                    )
            else:
                logger.debug(
                    f"{self.__class__.__name__}: Rename within same parent folder, no watcher rebind needed."
                )

        # 6. Update Breadcrumb if necessary

        self._refresh_breadcrumbs_if_needed(src_path_norm, dest_path_norm)

        logger.info(
            f"{self.__class__.__name__}: Rename and breadcrumb update complete."
        )

    def unbind_filewatcher_service(self):
        if self._file_watcher_service:
            for path in self._watched_paths:
                self._file_watcher_service.remove_path(path)
            self._watched_paths.clear()

    def _handle_file_changes(self, changes: list[FileChangeEvent]):
        """Handle batch file changes, debounce actual reload."""
        logger.debug(f"Received {len(changes)} file changes.")

        for evt in changes:
            if evt.src_path:
                parent = os.path.dirname(evt.src_path)
                self._pending_refresh_paths.add(parent)
            if evt.dest_path:
                parent = os.path.dirname(evt.dest_path)
                self._pending_refresh_paths.add(parent)

        if not self._refresh_debounce_timer.isActive():
            self._refresh_debounce_timer.start(400)  # Debounce reload 400ms

    def _process_pending_refresh(self):
        """Called after debounce timeout to actually refresh."""
        if not self._pending_refresh_paths:
            logger.debug("No pending paths to refresh after debounce.")
            return

        paths_to_check = list(self._pending_refresh_paths)
        self._pending_refresh_paths.clear()

        logger.debug(f"Processing {len(paths_to_check)} pending refresh paths...")
        self._refresh_items_async(paths_to_check)

    def _on_file_batch_changed(self, folder_path: str, events: List[FileChangeEvent]):
        """Handles batch file change events."""
        logger.debug(
            f"{self.__class__.__name__}: Batch changed detected at {folder_path} with {len(events)} events."
        )

        for evt in events:
            if evt.event_type == "moved":
                logger.info(
                    f"{self.__class__.__name__}: Detected rename from {evt.src_path} to {evt.dest_path}"
                )
                self._handle_file_rename(evt.src_path, evt.dest_path)
            else:
                # Other types (created, deleted, modified)

                self._pending_changed_paths.add(evt.src_path)

        # Start the debounce timer (re-use same logic dari _on_file_changed)

        if not self._debounce_timer:
            self._debounce_timer = QTimer(self)
            self._debounce_timer.setSingleShot(True)
            self._debounce_timer.setInterval(500)
            self._debounce_timer.timeout.connect(self._process_pending_file_changes)

        if not self._debounce_timer.isActive():
            self._debounce_timer.start()
