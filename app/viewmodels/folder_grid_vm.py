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

if TYPE_CHECKING:
    from app.viewmodels.object_list_vm import ObjectListVM


class FolderGridVM(BaseItemViewModel):
    folderItemSelected = pyqtSignal(object)
    breadcrumbChanged = pyqtSignal(list)
    filterSummaryChanged = pyqtSignal(str, bool)
    filterButtonStateChanged = pyqtSignal(int)
    batchOperationSummaryReady = pyqtSignal(str, bool)

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
        self._breadcrumb_path: List[str] = []
        self._watched_paths: set[str] = set()
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
        current_hash = self._filter_state.hash()
        if not initial_load and current_hash == self._last_filter_hash:
            return
        self._last_filter_hash = current_hash
        result = [
            item
            for item in self._all_folder_items
            if (not self._is_safe_mode_on or item.is_safe)
            and (
                self._filter_state.status == "All"
                or (self._filter_state.status == "Enabled" and item.status)
                or (self._filter_state.status == "Disabled" and not item.status)
            )
            and (
                not self._filter_state.text
                or self._filter_state.text.lower() in item.display_name.lower()
            )
            and self._match_metadata(item)
        ]
        if initial_load:
            result.sort(key=lambda i: (not i.status, i.display_name.lower()))
        self.displayed_items = result
        self.displayListChanged.emit(self.displayed_items)
        if self._selected_item in self.displayed_items:
            self.folderItemSelected.emit(self._selected_item)
        label = f"{len(self.displayed_items)} items found"
        visible = bool(self._filter_state.metadata) or bool(
            self._filter_state.text.strip()
        )
        self.filterSummaryChanged.emit(label if visible else "", visible)
        self.filterButtonStateChanged.emit(self._active_filter_count())

    def _connect_data_loader_signals(self):
        safe_connect(
            self._data_loader.folderItemsReady, self._on_folder_items_loaded, self
        )

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

    def handle_visible_thumbnail_requests(self, visible_paths: list[str]):
        for path in visible_paths:
            self._thumbnail_service.get_thumbnail_async(path, "folder")

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
            self._filter_and_sort()

    def _on_object_item_selected(self, selected_item: Optional[ObjectItemModel]):
        if selected_item is None:
            self.clear_state()
            return
        if self._current_object_item != selected_item:
            self._current_object_item = selected_item
            self._object_root_path = os.path.normpath(selected_item.path)
            self._breadcrumb_path = [os.path.basename(self._object_root_path)]
            self.breadcrumbChanged.emit(self._breadcrumb_path)
            self.load_folders_for(self._object_root_path)
            self.folderItemSelected.emit(None)

    def load_folders_for(self, parent_path: Optional[str]):
        self.resetFilterState.emit()
        if parent_path:
            self._current_parent_path = os.path.normpath(parent_path)
            self._data_loader.get_folder_items_async(self._current_parent_path)
            self.bind_filewatcher(parent_path, self._file_watcher_service)
        else:
            self._current_parent_path = None
            self._all_folder_items = []
            self._filter_and_sort()

    def bind_filewatcher(
        self, parent_path: str, file_watcher_service: FileWatcherService
    ):
        self._file_watcher_service = file_watcher_service
        if not parent_path or not os.path.isdir(parent_path):
            return
        self._unbind_filewatcher()
        watch_paths = set()
        for root, dirs, _ in os.walk(parent_path):
            level = os.path.relpath(root, parent_path).count(os.sep)
            if level > 2:
                continue
            watch_paths.add(os.path.normpath(root))
            for d in dirs:
                watch_paths.add(os.path.normpath(os.path.join(root, d)))
        for p in watch_paths:
            file_watcher_service.add_path(p, recursive=False)  # Non recursive

        self._watched_paths = watch_paths
        self._connect_file_watcher_signals()

    def _unbind_filewatcher(self):
        for path in self._watched_paths:
            self._file_watcher_service.remove_path(path)
        self._watched_paths.clear()

    def select_folder_item(self, item: FolderItemModel):
        self.folderItemSelected.emit(item)

    def _on_folder_items_loaded(self, parent_path: str, items: list[FolderItemModel]):
        if parent_path != self._current_parent_path:
            return
        self._all_folder_items = items
        self._filter_and_sort(initial_load=True)
        for item in self._all_folder_items:
            self.request_thumbnail_for(item)

    def _on_safe_mode_changed(self, is_on: bool):
        self._is_safe_mode_on = is_on
        self._filter_and_sort()
        if self._all_folder_items:
            self._mod_manager.applySafeModeChanges_async(
                list(self._all_folder_items), is_on
            )

    def handle_item_double_click(self, item_model: FolderItemModel):
        if not item_model or not os.path.isdir(item_model.path):
            return
        self._breadcrumb_path.append(item_model.folder_name)
        self.breadcrumbChanged.emit(self._breadcrumb_path)
        self.load_folders_for(item_model.path)
        self.folderItemSelected.emit(None)

    def navigate_to_breadcrumb_index(self, index: int):
        if index < 0 or index >= len(self._breadcrumb_path):
            return
        self._breadcrumb_path = self._breadcrumb_path[: index + 1]
        self.breadcrumbChanged.emit(self._breadcrumb_path)
        path = self._build_path_from_breadcrumb()
        self.load_folders_for(path)
        self.folderItemSelected.emit(None)

    def _build_path_from_breadcrumb(self) -> str:
        if not self._object_root_path:
            return ""
        path_parts = [self._object_root_path] + self._breadcrumb_path[1:]
        return os.path.normpath(os.path.join(*path_parts))

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
        self._filter_and_sort()

    def clear_all_metadata_filters(self):
        self._filter_state.metadata.clear()
        self._filter_and_sort()

    def set_metadata_filters(self, filters: dict[str, set[str]]):
        self._filter_state.metadata = filters
        self.filterButtonStateChanged.emit(self._active_filter_count())
        self._filter_and_sort()

    def _active_filter_count(self) -> int:
        return sum(len(v) for v in self._filter_state.metadata.values())

    def set_root_path(self, new_path):
        norm_new = os.path.normpath(new_path)
        if self._object_root_path == norm_new:
            return
        self._object_root_path = norm_new
        self._current_parent_path = norm_new
        self._breadcrumb_path = [os.path.basename(new_path)]
        self.breadcrumbChanged.emit(self._breadcrumb_path)
        self._suppress_next_load = True
        self.load_folders_for(norm_new)

    def apply_filter_text(self, text: str):
        self._filter_state.text = text.strip()
        self._debouncer.debounce("folder_search", self._filter_and_sort, delay_ms=300)

    def find_model_by_path(self, path: str) -> FolderItemModel | None:
        for item in self._all_folder_items:
            if item.path == path:
                return item
