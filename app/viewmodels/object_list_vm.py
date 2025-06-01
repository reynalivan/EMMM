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
    loadMoreRequested = pyqtSignal()

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
        self._selected_item: Optional[ObjectItemModel] = None
        self._current_game_path: Optional[str] = None
        self._all_object_items: List[ObjectItemModel] = []
        self._pending_object_items_for_emit: list[ObjectItemModel] = []
        self._incremental_render_debouncer = Debouncer(self)
        self.displayed_items: List[ObjectItemModel] = []
        self._visible_thumb_requested: set[str] = set()
        self._MAX_VISIBLE_ITEMS = 10
        self._is_loading_more = False
        self._current_display_limit = self._MAX_VISIBLE_ITEMS
        self._sort_key = "display_name"  # BEFORE logger.debug(...)
        self._sort_order = Qt.SortOrder.AscendingOrder
        logger.debug("ObjectListVM initialized.")
        self._connect_data_loader_signals()

    def _connect_data_loader_signals(self):
        try:
            dl = self._data_loader
            dl.objectItemChunkReady.connect(self._on_object_item_chunk_ready)
            dl.objectItemsReady.connect(self._on_object_items_ready)
            if hasattr(dl, "errorOccurred"):
                dl.errorOccurred.connect(
                    lambda name, msg: self.showError.emit(name, msg)
                )
        except AttributeError as e:
            logger.error(f"{self.__class__.__name__}: connect signals error {e}")

    def load_object_items(self, path):
        logger.debug(f"Handling game change: {path}")
        self._current_game_path = os.path.normpath(path)
        self.clear_state()
        if self._folder_grid_vm:
            self._folder_grid_vm.clear_state()
        self._load_items_for_path(self._current_game_path)
        self.bind_filewatcher(self._current_game_path, self._file_watcher_service)

    def _reset_paging(self):
        self._current_display_limit = self._MAX_VISIBLE_ITEMS
        self._pending_object_items_for_emit.clear()

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

    def set_metadata_filters(self, new_filters: dict[str, set[str]]):
        self._filter_state.metadata = new_filters

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

    def clear_all_filters_and_search(self):
        self._filter_state.metadata.clear()
        self._filter_state.text = ""

    def _on_object_items_ready(
        self, game_path: str, items: list[ObjectItemModel]
    ) -> None:
        if os.path.normpath(game_path) != os.path.normpath(self._current_game_path):
            return

        # ① reset semua state tampilan
        self._visible_thumb_requested.clear()
        self._pending_object_items_for_emit.clear()
        self._reset_paging()

        # ② simpan & SORT sekali (status → nama)  ➜ sama dgn FolderGrid
        self._all_object_items = sorted(
            items, key=lambda m: (not m.status, m.display_name.lower())
        )

        # ③ rebuild displayed_items + paging awal
        self.displayed_items = [
            m for m in self._all_object_items if self._passes_filter(m)
        ]
        first_batch = self.displayed_items[: self._current_display_limit]

        # ④ kirim ke UI + langsung minta thumbnail utk batch pertama
        self.displayListChanged.emit(first_batch)  # bisa [] jika 0 match
        self.handle_visible_thumbnail_requests([m.path for m in first_batch])

        # ⑤ bookkeeping UI
        self._emit_filtered_summary()
        self.set_loading(False)
        self.loadCompleted.emit(f"Loaded {len(self._all_object_items)} items")

    def try_load_more(self):
        if self._is_loading_more or self._current_display_limit >= len(
            self.displayed_items
        ):
            return
        self._is_loading_more = True

        prev_limit = self._current_display_limit
        self._current_display_limit += self._MAX_VISIBLE_ITEMS

        visible_now = self.displayed_items[: self._current_display_limit]
        newly_visible = visible_now[prev_limit:]

        self.displayListChanged.emit(visible_now)
        self.handle_visible_thumbnail_requests([m.path for m in newly_visible])
        self._emit_filtered_summary()

        self._is_loading_more = False

    def _filter_and_sort(self):
        self.displayed_items.clear()
        for item in self._all_object_items:
            self._filter_and_sort_item(item)
        self._emit_filtered_summary()

    def _filter_and_sort_item(self, item: ObjectItemModel):
        if not self._passes_filter(item):
            return
        if item in self.displayed_items:
            return

        idx = next(
            (
                i
                for i, ex in enumerate(self.displayed_items)
                if self._sort_compare(item, ex) < 0
            ),
            len(self.displayed_items),
        )
        self.displayed_items.insert(idx, item)

        # queue item if it is inside the *current* limit
        if idx < self._current_display_limit:
            self._pending_object_items_for_emit.append(item)

        self._incremental_render_debouncer.debounce(
            "object_emit_batch", self._emit_object_items_batch, 80
        )

    def _sort_compare(self, a: ObjectItemModel, b: ObjectItemModel) -> int:
        """Basic 2-kunci sort : status (enabled duluan) + nama.
        Hargai self._sort_order."""
        a_key = (not a.status, getattr(a, self._sort_key, a.display_name).lower())
        b_key = (not b.status, getattr(b, self._sort_key, b.display_name).lower())

        if self._sort_order == Qt.SortOrder.DescendingOrder:
            a_key, b_key = b_key, a_key

        return (a_key > b_key) - (a_key < b_key)

    def _emit_object_items_batch(self):
        if not self._pending_object_items_for_emit:
            return

        visible = self.displayed_items[: self._current_display_limit]
        self.displayListChanged.emit(visible)

        # minta thumbnail HANYA utk item pending
        self.handle_visible_thumbnail_requests(
            [m.path for m in self._pending_object_items_for_emit]
        )
        self._pending_object_items_for_emit.clear()

        self._emit_filtered_summary()

    def _passes_filter(self, item: ObjectItemModel) -> bool:
        if self._filter_state.status == "Enabled" and not item.status:
            return False
        if self._filter_state.status == "Disabled" and item.status:
            return False
        if (
            self._filter_state.text
            and self._filter_state.text.lower() not in item.display_name.lower()
        ):
            return False
        for cat, allowed_values in self._filter_state.metadata.items():
            item_values = item.metadata_index.get(cat, set())
            if not item_values.intersection(allowed_values):
                return False
        return True

    def _emit_filtered_summary(self):
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
            self.set_loading(False)
            return
        self._data_loader.get_object_items_async(norm_path)

    def _on_object_item_chunk_ready(self, game_path: str, item: ObjectItemModel):
        if os.path.normpath(game_path) != os.path.normpath(self._current_game_path):
            return
        self._all_object_items.append(item)
        if not self._passes_filter(item):
            return
        self.displayed_items.append(item)

        if len(self.displayed_items) <= self._current_display_limit:
            self._pending_object_items_for_emit.append(item)
            self._incremental_render_debouncer.debounce(
                "emit", self._emit_object_items_batch, 60
            )

    def apply_filter_text(self, text: str):
        self._filter_state.text = text
        self._debouncer.debounce(
            key="filter_text", func=self._refilter_all_items, delay_ms=200
        )

    def _refilter_all_items(self):
        self._visible_thumb_requested.clear()
        self._reset_paging()
        self.displayed_items = []

        for m in self._all_object_items:  # tetap pakai sort_compare
            self._filter_and_sort_item(m)

        first_batch = self.displayed_items[: self._current_display_limit]
        self.displayListChanged.emit(first_batch)  # ← kosong? UI bersih
        self.handle_visible_thumbnail_requests([m.path for m in first_batch])
        self._emit_filtered_summary()

    def apply_sort(self, sort_key: str, sort_order: Qt.SortOrder):
        self._sort_key = sort_key
        self._sort_order = sort_order

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

    def bind_filewatcher(
        self, game_path: str, file_watcher_service: FileWatcherService
    ):
        """Bind the file watcher to monitor the root game folder."""
        self._file_watcher_service = file_watcher_service
        if not game_path or not os.path.isdir(game_path):
            logger.warning(f"{self.__class__.__name__}: Invalid game path: {game_path}")
            return

        # Unbind previous watchers
        self._unbind_filewatcher()

        # Normalize the path and add to watcher
        norm_path = os.path.normpath(game_path)
        file_watcher_service.update_watched_paths({norm_path})
        logger.info(
            f"{self.__class__.__name__}: Watching root game folder: {norm_path}"
        )

    def handle_visible_thumbnail_requests(self, visible_paths: list[str]) -> None:
        """
        Dipanggil panel setelah mem-render batch baru.
        Minta thumbnail hanya untuk item yang benar-benar tampak
        dan belum pernah diminta pada sesi tampilan ini.
        """
        if not self._thumbnail_service:
            return

        for p in visible_paths:
            norm = os.path.normpath(p)
            if norm in self._visible_thumb_requested:
                continue  # sudah pernah diminta
            self._visible_thumb_requested.add(norm)
            # antrikan di ThumbnailService (pakai pool/queue internal)
            self._thumbnail_service.request_thumbnail(norm, "object")

    def _unbind_filewatcher(self):
        """Unbind the file watcher to stop monitoring."""
        if self._file_watcher_service:
            self._file_watcher_service.clear_all_watches()
            logger.info(f"{self.__class__.__name__}: Cleared all watches.")

    def clear_state(self):
        self._selected_item = None
        self._all_object_items.clear()
        self.displayed_items.clear()
        self._filter_state.text = ""
        self._filter_state.status = "all"
        self.displayListChanged.emit([])
