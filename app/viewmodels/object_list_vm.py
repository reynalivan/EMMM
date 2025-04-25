import os
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from app.models.object_item_model import ObjectItemModel
from app.services.data_loader_service import DataLoaderService
from app.services.mod_management_service import ModManagementService
from app.utils.logger_utils import logger
from app.services.thumbnail_service import ThumbnailService
from app.viewmodels.main_window_vm import MainWindowVM


class ObjectListVM(QObject):
    displayListChanged = pyqtSignal(list)  # list[ObjectItemModel]
    loadingStateChanged = pyqtSignal(bool)
    showError = pyqtSignal(str, str)
    itemNeedsUpdate = pyqtSignal(str, dict)
    objectItemSelected = pyqtSignal(ObjectItemModel)

    def __init__(self,
                 data_loader: DataLoaderService,
                 mod_service: ModManagementService,
                 thumbnail_service: ThumbnailService,
                 parent=None):
        super().__init__(parent)
        self._data_loader = data_loader
        self._mod_service = mod_service
        self._thumbnail_service = thumbnail_service
        self._selected_item: ObjectItemModel | None = None
        self._current_game_path: str | None = None
        self._all_object_items: list[ObjectItemModel] = []
        self.displayed_items: list[ObjectItemModel] = []
        thumbnail_path: str | None = None

        self._filter_text = ""
        self._filter_status = "All"  # All / Enabled / Disabled
        self._sort_key = "actual_name"
        self._sort_order = Qt.SortOrder.AscendingOrder

        self._connect_internal_signals()

    def connect_global_signals(self, main_vm: MainWindowVM):
        main_vm.currentGameChanged.connect(self._handle_currentGameChanged)

    def _connect_internal_signals(self):
        self._data_loader.objectItemsReady.connect(self._on_object_items_loaded)
        self._data_loader.errorOccurred.connect(
            lambda name, msg: self.showError.emit(name, msg))
        if hasattr(self, '_thumbnail_service') and self._thumbnail_service:
            self._thumbnail_service.thumbnailReady.connect(
                self._on_thumbnail_ready)
        else:
            logger.warning(
                "ObjectListVM: _thumbnail_service not available for signal connection."
            )

    def _handle_currentGameChanged(self, game_detail):
        game_path = game_detail.path if game_detail else None
        logger.debug(
            f"ObjectListVM: Current game changed to {game_detail.name if game_detail else 'None'}"
        )
        self.load_objects_for_game(game_path)

    def load_objects_for_game(self, game_path: str | None) -> None:
        normlpath = os.path.normpath(game_path)
        self._current_game_path = normlpath
        self.loadingStateChanged.emit(True)

        if not normlpath:
            self._all_object_items = []
            self.displayed_items = []
            self.displayListChanged.emit([])
            self.loadingStateChanged.emit(False)
            return

        self._data_loader.get_object_items_async(normlpath)

    def _on_object_items_loaded(self, game_path: str,
                                result: list[ObjectItemModel]) -> None:
        if self._current_game_path != game_path:
            return  # discard stale result

        self._all_object_items = result
        self._filter_and_sort()
        self.loadingStateChanged.emit(False)

    def request_thumbnail_for(self, item_model: ObjectItemModel):
        """Requests the thumbnail for a specific item from the service."""
        if not item_model:
            return
        # logger.debug(f"ObjectListVM: Requesting thumbnail for {item_model.path}") # Keep lean
        # Call the async method from the thumbnail service
        # Pastikan self._thumbnail_service sudah di-inject dan disimpan di __init__
        try:
            self._thumbnail_service.get_thumbnail_async(item_model.path,
                                                        'object')
        except AttributeError:
            logger.error(
                "ObjectListVM: _thumbnail_service not found or method missing.")
        except Exception as e:
            logger.error(f"Error requesting thumbnail: {e}")

    def _on_thumbnail_ready(self, item_path: str, result: dict):
        """Handles the thumbnailReady signal from ThumbnailService."""
        # logger.debug(f"ObjectListVM: Thumbnail ready for {item_path}, status: {result.get('status')}") # Keep lean
        # Notify the View (Panel) to update the specific item's widget
        self.itemNeedsUpdate.emit(item_path, result)

    def _filter_and_sort(self):
        filtered = []

        for item in self._all_object_items:
            if self._filter_status == "Enabled" and not item.status:
                continue
            if self._filter_status == "Disabled" and item.status:
                continue
            if self._filter_text and self._filter_text.lower(
            ) not in item.display_name.lower():
                continue
            filtered.append(item)

        key = lambda i: getattr(i, self._sort_key)
        reverse = self._sort_order == Qt.SortOrder.DescendingOrder
        filtered.sort(key=key, reverse=reverse)

        self.displayed_items = filtered
        self.displayListChanged.emit(filtered)

    def apply_filter(self, text: str, status: str):
        self._filter_text = text
        self._filter_status = status
        self._filter_and_sort()

    def apply_sort(self, sort_key: str, sort_order: Qt.SortOrder):
        self._sort_key = sort_key
        self._sort_order = sort_order
        self._filter_and_sort()

    def select_object_item(self, item_model: ObjectItemModel | None):
        self._selected_item = item_model
        if item_model:
            self.objectItemSelected.emit(item_model)
