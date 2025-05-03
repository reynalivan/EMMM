# app/viewmodels/folder_grid_vm.py

import os
from typing import List, Literal, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QPixmap
from app.models.folder_item_model import FolderItemModel
from app.models.object_item_model import ObjectItemModel
from app.services.file_watcher_service import FileChangeEvent, FileWatcherService
from app.services.mod_management_service import ModManagementService
from app.services.data_loader_service import DataLoaderService
from app.services.thumbnail_service import ThumbnailService  # Import ThumbnailService
from app.utils.logger_utils import logger  # Import logger
from app.core.constants import DISABLED_PREFIX
from app.views.components.breadcrumb_widget import BreadcrumbWidget
from .base_item_vm import BaseItemViewModel  # Import base class
from typing import TYPE_CHECKING
from app.utils.signal_utils import safe_connect
from app.utils.async_utils import Debouncer
from app.models.filter_state import FilterState

if TYPE_CHECKING:
    from app.viewmodels.object_list_vm import ObjectListVM
    from app.viewmodels.main_window_vm import MainWindowVM


class FolderGridVM(BaseItemViewModel):
    folderItemSelected = pyqtSignal(object)
    breadcrumbChanged = pyqtSignal(list)
    filterSummaryChanged = pyqtSignal(str, bool)  # (labelText, visible)
    filterButtonStateChanged = pyqtSignal(int)  # active filter count
    batchOperationSummaryReady = pyqtSignal(str, bool)  # message, isError

    def __init__(
        self,
        data_loader: DataLoaderService,
        mod_service: ModManagementService,
        thumbnail_service: ThumbnailService,
        file_watcher_service: FileWatcherService,
        parent: Optional[QObject] = None,
    ):  # Ensure parent is last
        # Call base class constructor with shared services
        super().__init__(data_loader, mod_service, thumbnail_service, parent)
        # FolderGridVM specific state
        self._file_watcher_service = file_watcher_service
        self._debouncer = Debouncer(self)
        self._suppress_next_load: bool = False
        self._filter_state = FilterState()
        self._last_filter_hash: int = 0

        self._is_safe_mode_on: bool = False
        self._current_object_item: Optional[ObjectItemModel] = None
        self._current_parent_path: Optional[str] = None
        self._object_root_path: Optional[str] = None
        self._selected_item: Optional[FolderItemModel] = None
        self._all_folder_items: List[FolderItemModel] = []  # The main data list
        self.displayed_items: List[FolderItemModel] = []  # Filtered/sorted list
        self._breadcrumb_path: List[str] = []

        self._connect_data_loader_signals()
        logger.debug("FolderGridVM initialized.")
        self._sort_key = "display_name"
        self._sort_order = Qt.SortOrder.AscendingOrder

    def _get_item_list(self) -> List[FolderItemModel]:
        """Returns the internal list of folder items."""
        return self._all_folder_items

    def _get_item_type(self) -> Literal["object", "folder"]:
        """Returns the item type handled by this VM."""
        return "folder"

    def _load_items_for_path(self, path: Optional[str]):
        """Loads folder items for the given parent folder path."""
        if path:
            self.load_folders_for(path)
        else:
            logger.debug(f"{self.__class__.__name__}: No valid path to load.")

    def _get_current_path_context(self) -> Optional[str]:
        """Returns the current parent folder path being viewed."""
        logger.debug(
            f"FolderGridVM: Returning current parent path: {self._current_parent_path}"
        )
        return self._current_parent_path

    def _filter_and_sort(self, initial_load: bool = False):
        """Filter + sort folder items, emit result and UI updates only if changed."""
        logger.debug(
            f"FolderGridVM: Filtering and sorting. Safe mode={self._is_safe_mode_on}, "
            f"Text='{self._filter_state.text}', Metadata={self._filter_state.metadata}"
        )

        current_hash = self._filter_state.hash()
        if not initial_load and current_hash == self._last_filter_hash:
            logger.debug("No filter state change, skipping filtering.")
            return

        self._last_filter_hash = current_hash
        result: list[FolderItemModel] = []

        for item in self._all_folder_items:
            # Safe mode filter
            if self._is_safe_mode_on and not item.is_safe:
                continue

            # Status filter
            if self._filter_state.status == "Enabled" and not item.status:
                continue
            if self._filter_state.status == "Disabled" and item.status:
                continue

            # Search text
            if (
                self._filter_state.text
                and self._filter_state.text.lower() not in item.display_name.lower()
            ):
                continue

            # Metadata filter
            if not self._match_metadata(item):
                continue

            result.append(item)

        # Optional: sort on initial load
        if initial_load:
            try:
                result.sort(key=lambda i: (not i.status, i.display_name.lower()))
            except Exception as e:
                logger.warning(f"Sort fallback: {e}")
                result.sort(key=lambda i: i.display_name.lower())

        self.displayed_items = result
        self.displayListChanged.emit(self.displayed_items)

        # Auto reselect if still present
        if self._selected_item and self._selected_item in self.displayed_items:
            self.folderItemSelected.emit(self._selected_item)

        # UI sync (Panel listens)
        label = f"{len(self.displayed_items)} items found"
        visible = bool(self._filter_state.metadata) or bool(
            self._filter_state.text.strip()
        )
        self.filterSummaryChanged.emit(label if visible else "", visible)
        self.filterButtonStateChanged.emit(self._active_filter_count())

    def connect_global_signals(
        self, main_vm: "MainWindowVM", object_list_vm: "ObjectListVM"
    ):
        """Connect to signals from other ViewModels."""
        # logger.debug("Connecting FolderGridVM to global VM signals...") # Keep lean
        try:
            object_list_vm.objectItemSelected.connect(self._on_object_item_selected)
            main_vm.safe_mode_status_changed.connect(self._on_safe_mode_changed)
            object_list_vm.objectItemPathChanged.connect(
                self._handle_object_path_changed
            )

            # TODO: Connect global refresh if needed
            # main_vm.global_refresh_requested.connect(self._handle_global_refresh)
        except AttributeError as e:
            logger.error(f"Error connecting global signals in FolderGridVM: {e}")

    def _connect_data_loader_signals(self):
        """Connects specific data loading signals for this VM."""
        # logger.debug("Connecting FolderGridVM data loader signals...") # Keep lean
        try:
            self._data_loader.folderItemsReady.connect(self._on_folder_items_loaded)
            # Error signal connected in base class init now if showError exists there
        except AttributeError as e:
            logger.error(f"Error connecting data loader signals in FolderGridVM: {e}")

    # bind_mod_service_signals is called from main.py
    def bind_mod_service_signals(self):
        logger.debug("Binding FolderGridVM to ModManagementService signals.")
        if self._mod_manager:
            safe_connect(
                self._mod_manager.modStatusChangeComplete,
                self._on_mod_status_changed,
                self,
            )

    def _match_metadata(self, item: FolderItemModel) -> bool:
        props = item.info or {}
        for key, allowed_vals in self._filter_state.metadata.items():
            val = props.get(key)
            allowed_vals_lower = {str(v).lower() for v in allowed_vals}
            if isinstance(val, list):
                if not any(str(v).lower() in allowed_vals_lower for v in val):
                    return False
            elif isinstance(val, (str, bool)):
                if str(val).lower() not in allowed_vals_lower:
                    return False
            else:
                return False
        return True

    def handle_visible_thumbnail_requests(self, visible_paths: list[str]):
        item_type = self._get_item_type()
        for path in visible_paths:
            self._thumbnail_service.get_thumbnail_async(path, item_type)

    def _after_mod_status_change(self, orig_path: str, new_path: str, result: dict):
        if not result.get("success"):
            return

        found_model = next(
            (
                m
                for m in self._all_folder_items
                if os.path.normpath(m.path)
                in {os.path.normpath(orig_path), os.path.normpath(new_path)}
            ),
            None,
        )

        if not found_model:
            return

        found_model.path = new_path
        found_model.folder_name = os.path.basename(new_path)

        from app.core.constants import DISABLED_PREFIX

        found_model.status = not found_model.folder_name.lower().startswith(
            DISABLED_PREFIX.lower()
        )

        self.request_thumbnail_for(found_model)

        self.updateItemDisplay.emit(
            orig_path,
            {
                "path": new_path,
                "display_name": found_model.display_name,
                "status": found_model.status,
            },
        )

        path_changed = os.path.normpath(orig_path) != os.path.normpath(new_path)

        if not path_changed:
            # Only apply filter/sort when no rename occurred
            self._filter_and_sort()  # No sorting after status switch

    def _emit_batch_summary_if_done(self):
        if self._status_manager.is_all_done():
            success = self._status_manager.get_success_count()
            failed = self._status_manager.get_fail_count()
            self._status_manager.reset_count()

            msg = f"{failed} item(s) failed" if failed else f"{success} item(s) updated"
            is_error = failed > 0
            self.batchOperationSummaryReady.emit(msg, is_error)

    def _on_object_item_selected(self, selected_item: ObjectItemModel | None):
        """Handles selection change from ObjectListVM."""
        if selected_item is None and self._current_object_item is None:
            logger.debug("Skip initial selection, no object yet.")
            return

        logger.debug(
            f"{self.__class__.__name__}: Object item selected -> {selected_item.path if selected_item else 'None'}"
        )

        if selected_item is None:
            if self._current_object_item:
                # Special case: object deselected temporarily due to rename/status change
                logger.info(
                    f"{self.__class__.__name__}: Object deselected temporarily, keeping current grid."
                )
                return

            # No previous object -> normal clear
            self._current_object_item = None
            self._object_root_path = None
            self._current_parent_path = None
            self._breadcrumb_path = []
            self.breadcrumbChanged.emit([])
            self._all_folder_items = []
            self._filter_and_sort()
            self.folderItemSelected.emit(None)
            return

        if self._current_object_item != selected_item:
            self._current_object_item = selected_item
            self._object_root_path = os.path.normpath(selected_item.path)
            self._breadcrumb_path = [os.path.basename(self._object_root_path)]
            self.breadcrumbChanged.emit(self._breadcrumb_path)

            if self._suppress_next_load:
                self._suppress_next_load = False
                logger.debug("FolderGridVM: Skipped double load due to suppress flag.")
                return

            self.load_folders_for(self._object_root_path)
            self.folderItemSelected.emit(None)

    def load_folders_for(self, parent_path: Optional[str]):
        """Loads folder items for the given parent path."""
        self.resetFilterState.emit()

        if parent_path:
            logger.info(f"FolderGridVM: Loading folders for path: {parent_path}")
            self._current_parent_path = os.path.normpath(parent_path)
            self._data_loader.get_folder_items_async(self._current_parent_path)
            self.bind_filewatcher(parent_path, self._file_watcher_service)

        else:
            logger.info(
                "FolderGridVM: load_folders_for called with None path, clearing."
            )
            self._current_parent_path = None
            self._all_folder_items = []
            self._filter_and_sort()  # Emit empty list

    def bind_filewatcher(
        self, parent_path: str, file_watcher_service: FileWatcherService
    ):
        self._file_watcher_service = file_watcher_service

        if not parent_path or not os.path.isdir(parent_path):
            logger.warning(
                f"{self.__class__.__name__}: Invalid parent path: {parent_path}"
            )
            return

        self._unbind_filewatcher()

        watch_paths = set()
        for root, dirs, _ in os.walk(parent_path):
            level = os.path.relpath(root, parent_path).count(os.sep)
            if level > 2:
                continue
            watch_paths.add(os.path.normpath(root))
            for d in dirs:
                full_path = os.path.normpath(os.path.join(root, d))
                watch_paths.add(full_path)

        for p in watch_paths:
            file_watcher_service.add_path(p)

        self._watched_paths = watch_paths
        logger.info(f"{self.__class__.__name__}: Watching {len(watch_paths)} folders.")
        self._connect_file_watcher_signals()

    def _unbind_filewatcher(self):
        if self._file_watcher_service:
            for path in self._watched_paths:
                self._file_watcher_service.remove_path(path)
        self._watched_paths.clear()

    def select_folder_item(self, item: FolderItemModel):
        self.folderItemSelected.emit(item)

    def _on_folder_items_loaded(self, parent_path: str, items: list[FolderItemModel]):
        """Handles the folder items loaded by DataLoaderService."""
        # Check if the result is for the currently viewed path
        if parent_path != self._current_parent_path:
            return

        if not self._current_object_item:
            logger.debug("FolderGridVM: Ignoring folder load — no current object.")
            return

        logger.debug(f"FolderGridVM: Received {len(items)} items for {parent_path}")
        self._all_folder_items = items
        self._filter_and_sort(
            initial_load=True
        )  # Apply filtering/sorting (includes safe mode)
        # Request thumbnails
        for item in self._all_folder_items:
            self.request_thumbnail_for(item)

    def _on_safe_mode_changed(self, is_on: bool):
        """Handles safe mode status changes from MainWindowVM."""
        logger.info(f"FolderGridVM: Safe mode changed to {is_on}")
        if self._is_safe_mode_on != is_on:
            self._is_safe_mode_on = is_on
            self.clear_state()
            # Apply filtering immediately to hide/show items
            self._filter_and_sort()
            # Trigger background task to rename folders if necessary
            if self._all_folder_items:  # Only run if we have items loaded
                logger.debug("Requesting ModManager to apply safe mode changes...")
                # Pass a copy in case the list changes while task runs? Or ensure task handles it.
                self._mod_manager.applySafeModeChanges_async(
                    list(self._all_folder_items), is_on  # Pass a copy
                )

    def handle_item_double_click(self, item_model: FolderItemModel):
        """Handles double-clicking on a folder item (navigate into subfolder)."""

        if not item_model:
            return
        logger.info(f"FolderGridVM: Item double-clicked: {item_model.path}")
        path = os.path.normpath(item_model.path)
        # Only navigate if it's actually a directory
        if not os.path.isdir(path):
            logger.warning(f"Double-clicked item is not a directory: {path}")
            return

        # Update breadcrumb
        # Avoid adding duplicate segment if already navigated
        self._breadcrumb_path.append(item_model.folder_name)
        self.breadcrumbChanged.emit(self._breadcrumb_path)

        # Load content of the new path
        self.load_folders_for(path)
        self.folderItemSelected.emit(
            None
        )  # Deselect item in preview when navigating deeper

    def navigate_to_breadcrumb_index(self, index: int):
        """Navigates to a folder level specified by the breadcrumb index."""
        logger.info(f"FolderGridVM: Received navigation request for index: {index}")

        # --- START PERBAIKAN: Cek jika index adalah yang terakhir/aktif ---
        current_last_index = len(self._breadcrumb_path) - 1
        if index == current_last_index:
            logger.debug(
                f"Navigation ignored: index {index} is the current last segment."
            )
            return

        if (
            not self._object_root_path
            or index < 0
            or index >= len(self._breadcrumb_path)
        ):
            logger.warning(
                f"Invalid breadcrumb index {index}, root path '{self._object_root_path}', or breadcrumb length {len(self._breadcrumb_path)}. Navigation aborted."
            )
            return

        logger.debug(f"Proceeding with navigation to index {index}...")
        # ... (sisa logika: trim breadcrumb, build path, load folders) ...
        self._breadcrumb_path = self._breadcrumb_path[: index + 1]
        self.breadcrumbChanged.emit(self._breadcrumb_path)
        path = self._build_path_from_breadcrumb()
        self.load_folders_for(path)
        self.folderItemSelected.emit(None)
        logger.debug(f"Navigation to index {index} complete.")

    def _build_path_from_breadcrumb(self) -> str:
        """Constructs the absolute path based on the current breadcrumb state."""
        if not self._object_root_path:
            return ""
        # Path starts at the root of the selected object item
        # Breadcrumb[0] is the object item's folder name, so we skip it when joining
        path_parts = [self._object_root_path] + self._breadcrumb_path[1:]
        return os.path.normpath(os.path.join(*path_parts))

    def _handle_global_refresh(self):
        """Handles the global refresh request signal."""
        logger.info("FolderGridVM: Handling global refresh request.")
        if self._current_parent_path:
            self.load_folders_for(self._current_parent_path)
        elif self._current_object_item:  # Fallback if navigated away from parent?
            logger.debug(
                "Refreshing based on current object item path as parent path is not set."
            )
            self.load_folders_for(self._current_object_item.path)
        else:
            logger.debug("Nothing to refresh in FolderGridVM (no current path/object).")

    def find_model_by_path(self, path: str) -> FolderItemModel | None:
        for item in self._all_folder_items:
            if item.path == path:
                return item

    def update_root_path(self, new_path: str):
        """Update object root and reload folder list if still active."""
        norm_new = os.path.normpath(new_path)
        if self._object_root_path == norm_new:
            return  # avoid redundant reload

        self._object_root_path = norm_new
        self._current_parent_path = norm_new
        self._breadcrumb_path = [os.path.basename(new_path)]

        self.breadcrumbChanged.emit(self._breadcrumb_path)

        # Set suppress flag to avoid double load from objectItemSelected
        self._suppress_next_load = True
        self.load_folders_for(norm_new)

    def _handle_object_path_changed(self, old_path: str, new_path: str):
        """Handles when the object root path is changed due to disable/enable/rename."""
        if not self._object_root_path:
            return

        old_path_norm = os.path.normpath(old_path)
        new_path_norm = os.path.normpath(new_path)
        current_parent_norm = (
            os.path.normpath(self._current_parent_path)
            if self._current_parent_path
            else None
        )

        # Update root if match
        if os.path.normpath(self._object_root_path) == old_path_norm:
            logger.info(
                f"FolderGridVM: Detected object root path change -> refreshing to new path: {new_path}"
            )
            self.update_root_path(new_path)

        # Update subfolder view if inside renamed object
        if current_parent_norm and current_parent_norm.startswith(old_path_norm):
            relative = os.path.relpath(current_parent_norm, old_path_norm)
            new_parent_path = os.path.normpath(os.path.join(new_path_norm, relative))

            # Hindari double refresh jika sudah di root
            if new_parent_path != new_path_norm:
                logger.info(
                    f"FolderGridVM: Current view inside renamed object, updating parent path too."
                )
                self._current_parent_path = new_parent_path
                self.load_folders_for(new_parent_path)

            # Update breadcrumb segment
            if self._breadcrumb_path:
                new_segment = os.path.basename(new_path_norm)
                if self._breadcrumb_path[0] != new_segment:
                    self._breadcrumb_path[0] = new_segment
                    self.breadcrumbChanged.emit(self._breadcrumb_path)

    def handle_object_root_about_to_change(self, path: str):
        """Clear FolderGrid view if the given object path is currently active."""
        if self._object_root_path and os.path.normpath(
            self._object_root_path
        ) == os.path.normpath(path):
            logger.info(
                "Object path will change. Clearing FolderGrid state proactively."
            )
            self.clear_state()

    def apply_filter_text(self, text: str):
        self._filter_state.text = text.strip()
        self._debouncer.debounce("folder_search", self._filter_and_sort, delay_ms=300)

    def _set_current_path_context(self, path: str):
        self._current_parent_path = path

    def clear_state(self):
        self._object_root_path = None
        self._current_parent_path = None
        self._breadcrumb_path.clear()
        self._all_folder_items.clear()
        self.displayed_items.clear()
        self._selected_item = None
        self.breadcrumbChanged.emit([])
        self.displayListChanged.emit([])
        self.folderItemSelected.emit(None)

    def set_safe_mode(self, is_on: bool):
        self._on_safe_mode_changed(is_on)

    def get_metadata_filter_options(self) -> dict[str, list[str]]:
        allowed_keys = {"author"}
        result = {}

        for item in self._all_folder_items:
            props = item.info or {}
            for k in allowed_keys:
                v = props.get(k)
                if isinstance(v, str):
                    result.setdefault(k, set()).add(v)
                elif isinstance(v, bool):
                    result.setdefault(k, set()).add(str(v))

        return {k: sorted(list(v)) for k, v in result.items()}

    def apply_metadata_filter(self, key: str, value: str):
        filters = self._filter_state.metadata.setdefault(key, set())
        if value in filters:
            filters.remove(value)
            if not filters:
                del self._filter_state.metadata[key]
        else:
            filters.add(value)
        self._filter_and_sort()

    def clear_all_metadata_filters(self):
        self._filter_state.metadata.clear()

    def set_metadata_filters(self, filters: dict[str, set[str]]):
        self._filter_state.metadata = filters
        self.filterButtonStateChanged.emit(self._active_filter_count())
        self._filter_and_sort()

    def _active_filter_count(self) -> int:
        return sum(len(v) for v in self._filter_state.metadata.values())
