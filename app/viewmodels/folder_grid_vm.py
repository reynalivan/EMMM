# App/viewmodels/folder grid vm.py


import os
from typing import List, Literal, Optional
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from app.models.folder_item_model import FolderItemModel
from app.models.object_item_model import ObjectItemModel
from app.services.file_watcher_service import FileWatcherService
from app.services.mod_management_service import ModManagementService
from app.services.data_loader_service import DataLoaderService
from app.services.thumbnail_service import ThumbnailService
from app.utils.logger_utils import logger
from app.core.constants import DISABLED_PREFIX
from .base_item_vm import BaseItemViewModel
from typing import TYPE_CHECKING
from app.utils.signal_utils import safe_connect
from app.utils.async_utils import Debouncer
from app.models.filter_state import FilterState
from bisect import bisect_left
from PyQt6.QtCore import QTimer

if TYPE_CHECKING:
    from app.viewmodels.object_list_vm import ObjectListVM


class FolderGridVM(BaseItemViewModel):
    folderItemSelected = pyqtSignal(object)
    breadcrumbChanged = pyqtSignal(list)
    filterSummaryChanged = pyqtSignal(str, bool)
    filterButtonStateChanged = pyqtSignal(int)
    batchOperationSummaryReady = pyqtSignal(str, bool)
    resultSummaryUpdated = pyqtSignal(str, bool)

    def __init__(
        self,
        data_loader: DataLoaderService,
        mod_service: ModManagementService,
        thumbnail_service: ThumbnailService,
        file_watcher_service: FileWatcherService,
        parent: Optional[QObject] = None,
    ):
        super().__init__(data_loader, mod_service, thumbnail_service, parent)
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
        self._all_folder_items: List[FolderItemModel] = []
        self.displayed_items: List[FolderItemModel] = []
        self._breadcrumb_path: list[tuple[str, str]] = []
        self._next_breadcrumb_pending: Optional[tuple[str, str]] = None
        self._visible_thumb_requested: set[str] = set()
        self._watched_paths: set[str] = set()
        self._pending_emit_timer = QTimer(self, interval=0, singleShot=True)
        self._pending_emit_timer.timeout.connect(self._flush_emit)
        self._MAX_VISIBLE_ITEMS = 10
        self._current_display_limit = self._MAX_VISIBLE_ITEMS

        self._connect_data_loader_signals()
        logger.debug("FolderGridVM initialized.")
        self._sort_key = "display_name"
        self._sort_order = Qt.SortOrder.AscendingOrder

    def _get_item_list(self) -> List[FolderItemModel]:
        return self._all_folder_items

    def _get_item_type(self) -> Literal["object", "folder"]:
        return "folder"

    def _load_items_for_path(self, path: Optional[str]):
        # Validation if Path is None
        if path is None:
            logger.debug("FolderGridVM: No valid path to load.")
            return

        # Normalization of path and validation whether the directory is valid
        norm_path = os.path.normpath(path)
        if not os.path.isdir(norm_path):
            logger.warning(f"FolderGridVM: Path is not a valid directory: {norm_path}")
            return

        # Check whether path is being supplied
        if self._file_watcher_service.is_suppressed(norm_path):
            logger.debug(
                f"FolderGridVM: Path is suppressed, skipping load: {norm_path}"
            )
            return

        # Item type validation

        if self._get_item_type() != "folder":
            logger.warning(f"FolderGridVM: Invalid item type for this VM.")
            return

        # Loading process if all validation passes

        self.load_folders_for(norm_path)

    def _get_current_path_context(self) -> Optional[str]:
        return self._current_parent_path

    def _filter_and_sort(self, initial_load: bool = False):
        """Deprecated in streaming mode. Use _filter_and_sort_item per chunk."""
        pass

    def _refilter_all_items(self):
        self._current_display_limit = self._MAX_VISIBLE_ITEMS

        self.displayed_items = [
            it for it in self._all_folder_items if self._passes_filter(it)
        ]
        self.displayed_items.sort(key=lambda i: (not i.status, i.display_name.lower()))

        self._flush_emit()

    def _sort_compare(self, a: FolderItemModel, b: FolderItemModel) -> int:
        """Sorting comparator: Enabled first, then by display_name."""
        a_key = (not a.status, a.display_name.lower())
        b_key = (not b.status, b.display_name.lower())
        return (a_key > b_key) - (a_key < b_key)

    def _connect_data_loader_signals(self):
        if not hasattr(self, "_is_signals_connected"):
            safe_connect(
                self._data_loader.folderItemChunkReady,
                self._on_folder_item_chunk_ready,
                self,
            )
            self._is_signals_connected = True
        safe_connect(
            self._data_loader.folderItemsReady,
            self._on_folder_items_ready,
            self,
        )
        safe_connect(self._data_loader.errorOccurred, self._on_folder_load_error, self)

    def _match_metadata(self, item: FolderItemModel) -> bool:
        props = item.info or {}
        for key, allowed_vals in self._filter_state.metadata.items():
            val = props.get(key)
            if isinstance(val, list):
                if not any(
                    str(v).lower() in {str(a).lower() for a in allowed_vals}
                    for v in val
                ):
                    return False
            elif val is not None:
                if str(val).lower() not in {str(a).lower() for a in allowed_vals}:
                    return False
        return True

    def _on_folder_item_chunk_ready(self, parent_path: str, item: FolderItemModel):
        if os.path.normpath(parent_path) != os.path.normpath(
            self._current_parent_path or ""
        ):
            return

        self._all_folder_items.append(item)

        if not self._passes_filter(item):
            return

        self._insert_sorted(item)

        if not self._pending_emit_timer.isActive():
            self._pending_emit_timer.start()  # emit di event-loop berikut

    def _passes_filter(self, item: FolderItemModel) -> bool:
        if self._is_safe_mode_on and not item.is_safe:
            return False

        if self._filter_state.status == "Enabled" and not item.status:
            return False
        if self._filter_state.status == "Disabled" and item.status:
            return False

        if (
            self._filter_state.text
            and self._filter_state.text.lower() not in item.display_name.lower()
        ):
            return False

        return self._match_metadata(item)

    def _insert_sorted(self, item: FolderItemModel):
        """Masukkan item ke self.displayed_items berdasar sort key tanpa resort global."""
        key = (not item.status, item.display_name.lower())
        keys = [(not it.status, it.display_name.lower()) for it in self.displayed_items]
        idx = bisect_left(keys, key)
        self.displayed_items.insert(idx, item)

    def _flush_emit(self):
        visible = self.displayed_items[: self._current_display_limit]

        # (1) kabari UI
        self.displayListChanged.emit(visible)

        # (2) kabari hasil ringkas
        self._emit_result_summary()

        # (3) minta thumbnail untuk item YANG BENAR-BENAR terlihat
        self.handle_visible_thumbnail_requests([m.path for m in visible])

    def _emit_result_summary(self):
        total = len(self._all_folder_items)
        shown = len(self.displayed_items)
        text = f"{shown} of {total} folders" if shown < total else f"{shown} folders"
        visible = (
            shown < total
            or bool(self._filter_state.text)
            or bool(self._filter_state.metadata)
        )
        self.resultSummaryUpdated.emit(text, visible)

    def try_load_more(self):
        if self._current_display_limit >= len(self.displayed_items):
            return  # no more to load

        self._current_display_limit += self._MAX_VISIBLE_ITEMS
        logger.debug(f"FolderGridVM: Loading more items: {self._current_display_limit}")
        self._flush_emit()

    def handle_visible_thumbnail_requests(self, visible_paths: list[str]):
        if not self._thumbnail_service:
            return

        for p in visible_paths:
            # Check cache
            cached = self._thumbnail_service.get_cached_thumbnail(p, "folder")
            if cached:
                self.itemThumbnailNeedsUpdate.emit(p, cached)
                continue

            # if not have cache, request
            self._thumbnail_service.request_thumbnail(p, "folder")

    def _after_mod_status_change(self, orig_path: str, new_path: str, result: dict):
        if not result.get("success") or result.get("source") != "folder":
            return
        found_model = next(
            (m for m in self._all_folder_items if m.path == orig_path), None
        )
        if found_model:
            # Suppress Event Rename so as not to trigger Reload in ObjectlistVM

            self._file_watcher_service.suppress_path(new_path)
            found_model.path = new_path
            found_model.folder_name = os.path.basename(new_path)
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
            self._refilter_all_items()

    def _on_object_item_selected(self, selected_item: Optional[ObjectItemModel]):
        if selected_item is None:
            self.clear_state()
            self._flush_emit()
            return

        if self._current_object_item != selected_item:
            self.clear_state()
            self._flush_emit()
            self._current_object_item = selected_item
            root_path = os.path.normpath(selected_item.path)
            self._object_root_path = root_path
            self._breadcrumb_path = [(os.path.basename(root_path), root_path)]
            self.breadcrumbChanged.emit([os.path.basename(root_path)])
            self.load_folders_for(root_path)
            self.folderItemSelected.emit(None)

    def load_folders_for(self, parent_path: Optional[str]):
        self.resetFilterState.emit()
        self.handle_visible_thumbnail_requests([])

        # Clean up first
        self._all_folder_items.clear()
        self.displayed_items.clear()
        self._visible_thumb_requested.clear()
        self._current_display_limit = self._MAX_VISIBLE_ITEMS
        self._flush_emit()

        if parent_path:
            self._current_parent_path = os.path.normpath(parent_path)
            self._data_loader.get_folder_items_async(self._current_parent_path)
            self.bind_filewatcher(parent_path, self._file_watcher_service)
        else:
            self._current_parent_path = None
            # self._refilter_all_items()

    def bind_filewatcher(
        self, parent_path: str, file_watcher_service: FileWatcherService
    ):
        """Bind the file watcher to monitor valid files and 1-level subfolders."""
        self._file_watcher_service = file_watcher_service
        if not parent_path or not os.path.isdir(parent_path):
            logger.warning(
                f"{self.__class__.__name__}: Invalid parent path: {parent_path}"
            )
            return

        # Unbind previous watchers
        self._unbind_filewatcher()

        # Normalize the path and gather subfolders
        norm_path = os.path.normpath(parent_path)
        watch_paths = {norm_path}
        try:
            for entry in os.scandir(norm_path):
                if entry.is_dir():
                    watch_paths.add(os.path.normpath(entry.path))
        except OSError as e:
            logger.error(
                f"{self.__class__.__name__}: Failed to scan path {norm_path}: {e}"
            )

        # Update watcher with valid paths
        file_watcher_service.update_watched_paths(watch_paths)
        logger.info(f"{self.__class__.__name__}: Watching {len(watch_paths)} paths.")

    def _unbind_filewatcher(self):
        """Unbind the file watcher to stop monitoring."""
        if self._file_watcher_service:
            self._file_watcher_service.clear_all_watches()
            logger.info(f"{self.__class__.__name__}: Cleared all watches.")

    def select_folder_item(self, item: FolderItemModel):
        self.folderItemSelected.emit(item)

    def _on_safe_mode_changed(self, is_on: bool):
        self._is_safe_mode_on = is_on
        self._refilter_all_items()
        if self._all_folder_items:
            self._mod_manager.applySafeModeChanges_async(
                list(self._all_folder_items), is_on
            )

    def handle_item_double_click(self, item_model: FolderItemModel):
        if not item_model or not os.path.isdir(item_model.path):
            return

        full_path = os.path.normpath(item_model.path)
        folder_name = item_model.folder_name

        self._next_breadcrumb_pending = (folder_name, full_path)

        # Clear items before new load (but retain root info & breadcrumb path)
        self._all_folder_items.clear()
        self.displayed_items.clear()
        self._flush_emit()

        # Set as tentative path, wait until _on_folder_items_ready confirms it
        self._data_loader.get_folder_items_async(full_path)
        self.bind_filewatcher(full_path, self._file_watcher_service)

    def navigate_to_breadcrumb_index(self, index: int):
        if index < 0 or index >= len(self._breadcrumb_path):
            return

        self._breadcrumb_path = self._breadcrumb_path[: index + 1]
        self.breadcrumbChanged.emit([name for name, _ in self._breadcrumb_path])

        _, path = self._breadcrumb_path[-1]
        self.load_folders_for(path)
        self.folderItemSelected.emit(None)

    def _on_folder_items_ready(self, path: str, items: list[FolderItemModel]):
        if not self._next_breadcrumb_pending:
            return

        name, expected_path = self._next_breadcrumb_pending
        if os.path.normpath(path) != os.path.normpath(expected_path):
            return

        self._current_parent_path = expected_path
        self._next_breadcrumb_pending = None

        self._breadcrumb_path.append((name, expected_path))
        self.breadcrumbChanged.emit([n for n, _ in self._breadcrumb_path])

        self._all_folder_items = []
        self.displayed_items = []

        for item in items:
            self._on_folder_item_chunk_ready(expected_path, item)

    def _on_folder_load_error(self, operation_name: str, error_message: str):
        # Only act if we're waiting on a breadcrumb push
        if self._next_breadcrumb_pending:
            logger.warning(
                f"Load failed for {self._next_breadcrumb_pending[1]}: {error_message}"
            )
            self._next_breadcrumb_pending = None

            # Revert parent path to previous one
            self._current_parent_path = self._build_path_from_breadcrumb()
            self.bind_filewatcher(self._current_parent_path, self._file_watcher_service)

            # Optional: inform user (signal or toast if integrated)

    def clear_state(self):
        self._object_root_path = None
        self._current_parent_path = None
        self._breadcrumb_path.clear()
        self._all_folder_items.clear()
        self.displayed_items.clear()
        self._selected_item = None
        self._pending_emit_timer.stop()
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
                if v is not None:
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
        self._refilter_all_items()

    def clear_all_metadata_filters(self):
        self._filter_state.metadata.clear()
        self._refilter_all_items()

    def set_metadata_filters(self, filters: dict[str, set[str]]):
        self._filter_state.metadata = filters
        self.filterButtonStateChanged.emit(self._active_filter_count())
        self._refilter_all_items()

    def _active_filter_count(self) -> int:
        return sum(len(v) for v in self._filter_state.metadata.values())

    def set_root_path(self, new_path):
        norm_new = os.path.normpath(new_path)
        if self._object_root_path == norm_new:
            return
        self.clear_state()
        self._object_root_path = norm_new
        self._current_parent_path = norm_new
        self._breadcrumb_path = [(os.path.basename(new_path), norm_new)]
        self.breadcrumbChanged.emit([os.path.basename(new_path)])
        self._suppress_next_load = True
        self.load_folders_for(norm_new)

    def apply_filter_text(self, text: str):
        self._filter_state.text = text.strip()
        self._debouncer.debounce("folder_search", self._refilter_all_items, 200)

    def find_model_by_path(self, path: str) -> FolderItemModel | None:
        for item in self._all_folder_items:
            if item.path == path:
                return item
