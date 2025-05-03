# App/viewmodels/object list vm.py


import os
from typing import List, Optional, Literal, Dict, Any
from PyQt6.QtCore import pyqtSignal, Qt, QObject, QTimer
from PyQt6.QtGui import QPixmap
from app.models.object_item_model import ObjectItemModel
from app.services.data_loader_service import DataLoaderService
from app.services.file_watcher_service import FileChangeEvent, FileWatcherService
from app.services.mod_management_service import ModManagementService
from app.services.thumbnail_service import ThumbnailService
from app.utils.logger_utils import logger
from .base_item_vm import BaseItemViewModel
from app.utils.async_utils import AsyncStatusManager, Debouncer
from app.viewmodels.folder_grid_vm import FolderGridVM
from typing import TYPE_CHECKING
from app.models.filter_state import FilterState
from app.models.game_model import GameDetail

if TYPE_CHECKING:
    from app.viewmodels.main_window_vm import MainWindowVM


class ObjectListVM(BaseItemViewModel):
    objectItemSelected = pyqtSignal(object)
    filterButtonStateChanged = pyqtSignal(int)
    resultSummaryUpdated = pyqtSignal(str)
    loadCompleted = pyqtSignal(str)

    def __init__(
        self,
        data_loader: DataLoaderService,
        mod_service: ModManagementService,
        thumbnail_service: ThumbnailService,
        file_watcher_service: FileWatcherService,
        folder_grid_vm: FolderGridVM,
        parent: Optional[QObject] = None,
    ):
        super().__init__(data_loader, mod_service, thumbnail_service, parent)
        self.set_handling_status_changes(True)
        self._folder_grid_vm = folder_grid_vm
        self._file_watcher_service = file_watcher_service
        self._debouncer = Debouncer(self)
        self._filter_state = FilterState()
        self._last_filter_state: Optional[FilterState] = None
        self._selected_item: Optional[ObjectItemModel] = None
        self._current_game_path: Optional[str] = None
        self._all_object_items: List[ObjectItemModel] = []
        self.displayed_items: List[ObjectItemModel] = []
        self._sort_key = "display_name"
        self._sort_order = Qt.SortOrder.AscendingOrder
        logger.debug("ObjectListVM initialized.")
        self._connect_data_loader_signals()

    def _connect_data_loader_signals(self):
        try:
            self._data_loader.objectItemsReady.connect(self._on_object_items_loaded)
            if hasattr(self, "showError") and self._data_loader:
                self._data_loader.errorOccurred.connect(
                    lambda name, msg: self.showError.emit(name, msg)
                )
        except AttributeError as e:
            logger.error(f"Error connecting data loader signals in ObjectListVM: {e}")

    def load_object_items(self, path):
        logger.debug(f"Handling game change: {path}")
        self._current_game_path = os.path.normpath(path)
        self.clear_state()
        if self._folder_grid_vm:
            self._folder_grid_vm.clear_state()
        self._load_items_for_path(self._current_game_path)
        self.bind_filewatcher(self._current_game_path, self._file_watcher_service)

    def _load_items_for_path(self, path: Optional[str]):
        # Validation if Path is None

        if path is None:
            logger.debug(f"{self.__class__.__name__}: No valid path to load.")
            return

        # Normalization of path and validation whether the directory is valid
        norm_path = os.path.normpath(path)
        if not os.path.isdir(norm_path):
            logger.warning(
                f"{self.__class__.__name__}: Path is not a valid directory: {norm_path}"
            )
            return

        # Check whether path is being supplied
        if self._file_watcher_service.is_suppressed(norm_path):
            logger.debug(
                f"{self.__class__.__name__}: Path is suppressed, skipping load: {norm_path}"
            )
            return

        # Item type validation
        if self._get_item_type() != "object":
            logger.warning(f"{self.__class__.__name__}: Invalid item type for this VM.")
            return

        # Loading process if all validation passes

        logger.debug(f"Loading object items for path: {norm_path}")
        self._current_game_path = norm_path
        self.load_objects_for_game(self._current_game_path)

    def _get_item_list(self) -> List[ObjectItemModel]:
        return self._all_object_items

    def _get_item_type(self) -> Literal["object", "folder"]:
        return "object"

    def _get_current_path_context(self) -> Optional[str]:
        return self._current_game_path

    def _filter_and_sort(self):
        self._debouncer.debounce(
            key="object_filter_sort", func=self._filter_and_sort_logic, delay_ms=300
        )

    def set_metadata_filters(self, new_filters: dict[str, set[str]]):
        self._filter_state.metadata = new_filters
        self._filter_and_sort()

    def get_metadata_filter_options(self) -> dict[str, list[str]]:
        allowed_keys = {"element", "region", "rarity", "gender", "weapon", "roles"}
        result: dict[str, set[str]] = {}
        for item in self._all_object_items:
            props = item.properties or {}
            for k in allowed_keys:
                val = props.get(k)
                if isinstance(val, str):
                    result.setdefault(k, set()).add(val)
                elif isinstance(val, list):
                    result.setdefault(k, set()).update(val)
        return {k: sorted(v) for k, v in result.items()}

    def clear_metadata_filter(self):
        self._filter_state.metadata.clear()
        self._filter_and_sort()

    def clear_all_filters_and_search(self):
        self._filter_state.metadata.clear()
        self._filter_state.text = ""
        self._filter_and_sort()

    def _filter_and_sort_logic(self):
        logger.debug("Filtering and sorting...")
        filtered = []
        for item in self._all_object_items:
            if self._filter_state.status == "Enabled" and not item.status:
                continue
            if self._filter_state.status == "Disabled" and item.status:
                continue
            if (
                self._filter_state.text
                and self._filter_state.text.lower() not in item.display_name.lower()
            ):
                continue
            metadata_ok = True
            for cat, allowed_values in self._filter_state.metadata.items():
                item_values = item.metadata_index.get(cat, set())
                if not item_values.intersection(allowed_values):
                    metadata_ok = False
                    break
                prop_value = item.properties.get(cat)
                if isinstance(prop_value, list):
                    if not any(v in allowed_values for v in prop_value):
                        metadata_ok = False
                        break
                elif prop_value not in allowed_values:
                    metadata_ok = False
                    break
            if not metadata_ok:
                continue
            filtered.append(item)
        try:
            is_reverse = self._sort_order == Qt.SortOrder.DescendingOrder
            prepared = [
                ((not i.status, getattr(i, self._sort_key, i.display_name)), i)
                for i in filtered
            ]
            prepared.sort(key=lambda x: x[0])
            self.displayed_items = [i for _, i in prepared]
        except Exception as e:
            logger.error(f"Sorting failed: {e}. Falling back to default sort.")
            self.displayed_items = sorted(filtered, key=lambda i: i.display_name)
        self.displayListChanged.emit(self.displayed_items)
        active_filter_count = sum(len(v) for v in self._filter_state.metadata.values())
        self.filterButtonStateChanged.emit(active_filter_count)
        show_summary = bool(self._filter_state.text.strip() or active_filter_count)
        summary = f"{len(self.displayed_items)} items found" if show_summary else ""
        self.resultSummaryUpdated.emit(summary)

    def load_objects_for_game(self, game_path: Optional[str]) -> None:
        norm_path = os.path.normpath(game_path) if game_path else None
        if norm_path != self._current_game_path:
            self.select_object_item(None)
        self._current_game_path = norm_path
        self.set_loading(True)
        self.select_object_item(None)
        if not norm_path:
            self._all_object_items = []
            self._filter_and_sort()
            self.set_loading(False)
            return
        self._data_loader.get_object_items_async(norm_path)

    def _on_object_items_loaded(
        self, game_path: str, result: list[ObjectItemModel]
    ) -> None:
        if os.path.normpath(self._current_game_path or "") != os.path.normpath(
            game_path
        ):
            logger.debug(
                f"[ObjectListVM] Ignored async result: path mismatch: {game_path}"
            )
            return
        logger.debug(f"[ObjectListVM] Received {len(result)} items for {game_path}")
        self._all_object_items = result
        self._filter_and_sort()
        self.loadCompleted.emit(f"Successfully loaded {len(result)} items")
        self.set_loading(False)
        for item in self._all_object_items:
            self.request_thumbnail_for(item)

    def apply_filter_text(self, text: str):
        self._filter_state.text = text
        self._debouncer.debounce(
            key="filter_text", func=self._filter_and_sort, delay_ms=200
        )

    def apply_sort(self, sort_key: str, sort_order: Qt.SortOrder):
        self._sort_key = sort_key
        self._sort_order = sort_order
        self._filter_and_sort()

    def select_object_item(self, item_model: Optional[ObjectItemModel]):
        if self._selected_item != item_model:
            self._selected_item = item_model
            self.objectItemSelected.emit(item_model)

    def _on_mod_status_changed(self, original_item_path: str, result: dict):
        if not getattr(self, "_is_handling_status_changes", False):
            logger.debug(f"{self.__class__.__name__}: Mod status change ignored.")
            return
        if result.get("item_type") != "object" or result.get("source") != "object":
            logger.debug(
                f"{self.__class__.__name__}: Ignoring foldergrid status change."
            )
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
            self._file_watcher_service.suppress_path(
                new_path
            )  # Suppress di FileWatcherService

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
        found_model = next(
            (
                m
                for m in self._all_object_items
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
                    self._file_watcher_service.remove_path(
                        os.path.dirname(original_item_path)
                    )
                    self._file_watcher_service.add_path(os.path.dirname(new_path))
                self.objectItemPathChanged.emit(original_item_path, new_path)
        else:
            logger.warning(
                f"{self.__class__.__name__}: Model not found for {original_item_path}"
            )
        self._after_mod_status_change(original_item_path, new_path, result)
        QTimer.singleShot(1000, lambda: self._suppressed_renames.discard(new_path))

    def _after_mod_status_change(self, orig_path: str, new_path: str, result: dict):
        if not result.get("success"):
            return
        affected_item = next(
            (item for item in self._all_object_items if item.path == orig_path),
            None,
        )
        if affected_item:
            affected_item.path = new_path
            affected_item.status = result.get("new_status", affected_item.status)
            self.updateItemDisplay.emit(
                orig_path,
                {
                    "status": affected_item.status,
                    "display_name": affected_item.display_name,
                    "path": new_path,
                },
            )
        if self._selected_item and os.path.normpath(self._selected_item.path) in {
            os.path.normpath(orig_path),
            os.path.normpath(new_path),
        }:
            logger.info(
                f"ObjectListVM: Selected item was toggled, updating FolderGrid to {new_path}"
            )
            self._selected_item.path = new_path
            self._folder_grid_vm.set_root_path(new_path)

    def _set_current_path_context(self, path: str):
        self._current_game_path = path

    def apply_metadata_filter(self, category: str, value: str):
        meta = self._filter_state.metadata.setdefault(category, set())
        if value in meta:
            meta.remove(value)
            if not meta:
                del self._filter_state.metadata[category]
        else:
            meta.add(value)
        self._filter_and_sort()

    def bind_filewatcher(
        self, game_path: str, file_watcher_service: FileWatcherService
    ):
        self._file_watcher_service = file_watcher_service
        if not game_path or not os.path.isdir(game_path):
            logger.warning(f"{self.__class__.__name__}: Invalid game path: {game_path}")
            return
        self._unbind_filewatcher()
        norm_path = os.path.normpath(game_path)
        watch_paths = {norm_path}
        try:
            for entry in os.scandir(norm_path):
                if entry.is_dir():
                    watch_paths.add(os.path.normpath(entry.path))
        except OSError as e:
            logger.error(f"Failed to scan game path {norm_path}: {e}")
        for path in watch_paths:
            file_watcher_service.add_path(path, recursive=False)  # Non recursive

        self._watched_paths = watch_paths
        logger.info(f"{self.__class__.__name__}: Watching {len(watch_paths)} folders.")
        self._connect_file_watcher_signals()

    def _unbind_filewatcher(self):
        if self._file_watcher_service:
            for path in self._watched_paths:
                self._file_watcher_service.remove_path(path)
        self._watched_paths.clear()

    def clear_state(self):
        self._selected_item = None
        self._all_object_items.clear()
        self.displayed_items.clear()
        self._filter_state.text = ""
        self._filter_state.status = "all"
        self._sort_key = "name"
        self._sort_order = Qt.SortOrder.AscendingOrder
        self.displayListChanged.emit([])
