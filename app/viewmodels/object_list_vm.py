# App/viewmodels/object list vm.py


import os
from typing import List, Optional, Literal, Dict, Any  # Import Literal

from PyQt6.QtCore import pyqtSignal, Qt, QObject  # Keep Qt for SortOrder


from app.models.object_item_model import ObjectItemModel
from app.services.data_loader_service import DataLoaderService
from app.services.mod_management_service import ModManagementService
from app.services.thumbnail_service import ThumbnailService
from app.viewmodels.main_window_vm import MainWindowVM
from app.utils.logger_utils import logger
from .base_item_vm import BaseItemViewModel, ItemModelType  # Import base class

from app.core.async_status_manager import AsyncStatusManager


class ObjectListVM(BaseItemViewModel):
    """ViewModel for the Object List panel."""

    objectItemSelected = pyqtSignal(object)

    def __init__(
        self,
        data_loader: DataLoaderService,
        mod_service: ModManagementService,
        thumbnail_service: ThumbnailService,
        parent: Optional[QObject] = None,
    ):
        # Call base class constructor with shared services

        super().__init__(data_loader, mod_service, thumbnail_service, parent)
        self.set_handling_status_changes(True)
        self._status_manager = AsyncStatusManager(self)

        # ObjectListVM specific state

        self._selected_item: Optional[ObjectItemModel] = None
        self._current_game_path: Optional[str] = None
        self._all_object_items: List[ObjectItemModel] = []  # The main data list

        self.displayed_items: List[ObjectItemModel] = []

        # Specific Filter/Sort State (could be moved to base if desired later)

        self._filter_text = ""
        self._filter_status = "All"
        self._sort_key = "display_name"
        self._sort_order = Qt.SortOrder.AscendingOrder

        # Connect signals specific to this VM's data loading

        self._connect_data_loader_signals()
        logger.debug("ObjectListVM initialized (inherits BaseItemViewModel).")

    # ---Implementation of Abstract Methods from Base ---

    def _get_item_list(self) -> List[ObjectItemModel]:
        """Returns the internal list of object items."""
        return self._all_object_items

    def _get_item_type(self) -> Literal["object", "folder"]:
        """Returns the item type handled by this VM."""
        return "object"

    def _load_items_for_path(self, path: str | None):
        """Loads object items for the given game path."""
        self.load_objects_for_game(path)  # Delegate to existing method

    def _get_current_path_context(self) -> str | None:
        """Returns the current game path being viewed."""
        return self._current_game_path

    def _filter_and_sort(self):
        """Filters and sorts the internal object list and emits displayListChanged."""
        # logger.debug("ObjectListVM: Filtering and sorting items...") # Keep lean

        filtered = []
        for item in self._all_object_items:  # Use the internal list
            # Apply filters

            if self._filter_status == "Enabled" and not item.status:
                continue
            if self._filter_status == "Disabled" and item.status:
                continue
            if (
                self._filter_text
                and self._filter_text.lower() not in item.display_name.lower()
            ):
                continue
            filtered.append(item)
        # Apply sorting

        try:
            key_func = lambda i: getattr(i, self._sort_key, i.display_name)
            is_reverse = self._sort_order == Qt.SortOrder.DescendingOrder
            filtered.sort(key=key_func, reverse=is_reverse)
        except Exception as e:
            logger.error(f"Sorting failed: {e}. Falling back to default sort.")
            filtered.sort(key=lambda i: i.display_name)  # Fallback sort

        self.displayed_items = filtered
        self.displayListChanged.emit(filtered)  # Emit the final list

    # ---End Abstract Method Implementations ---

    # ---ObjectListVM Specific Methods ---

    def connect_global_signals(self, main_vm: MainWindowVM):
        """Connect to signals from MainWindowVM."""
        # logger.debug("Connecting ObjectListVM to MainWindowVM signals...") # Keep lean

        try:
            main_vm.current_game_changed.connect(self._handle_current_game_changed)
            # TODO: Connect main_vm.global_refresh_requested to a refresh slot

        except AttributeError as e:
            logger.error(f"Error connecting global signals in ObjectListVM: {e}")

    def _connect_data_loader_signals(self):
        """Connects specific data loading signals for this VM."""
        try:
            # Connect objectItemsReady from data_loader

            self._data_loader.objectItemsReady.connect(self._on_object_items_loaded)
            # showError signal is inherited from BaseItemViewModel, connection check is optional

            if hasattr(self, "showError") and self._data_loader:
                self._data_loader.errorOccurred.connect(
                    lambda name, msg: self.showError.emit(name, msg)
                )
        except AttributeError as e:
            logger.error(f"Error connecting data loader signals in ObjectListVM: {e}")

    def _handle_current_game_changed(self, game_detail):
        """Slot for current_game_changed signal."""
        game_path = game_detail.path if game_detail else None
        self._load_items_for_path(game_path)  # Use the abstract method call wrapper

    # Renamed to match abstract method call pattern

    def load_objects_for_game(self, game_path: str | None) -> None:
        """Implementation for loading object items."""
        normlpath = os.path.normpath(game_path) if game_path else None
        self._current_game_path = normlpath  # Update context path

        self.set_loading(True)  # Use base class method to set loading state

        self.select_object_item(None)  # Deselect previous item

        if not normlpath:
            self._all_object_items = []
            self._filter_and_sort()  # Update display with empty list

            self.set_loading(False)
            # logger.info("ObjectListVM: No game path provided, list cleared.") # Keep lean

            return

        self._data_loader.get_object_items_async(normlpath)

    def _on_object_items_loaded(
        self, game_path: str, result: list[ObjectItemModel]
    ) -> None:
        """Slot for objectItemsReady signal."""
        if self._current_game_path != game_path:
            return  # Stale result

        self._all_object_items = result  # Update internal list

        self._filter_and_sort()  # Update display

        self.set_loading(False)
        # TODO: Trigger initial thumbnail requests?

    def apply_filter(self, text: str, status: str):
        """Applies filter criteria."""
        self._filter_text = text
        self._filter_status = status
        self._filter_and_sort()

    def apply_sort(self, sort_key: str, sort_order: Qt.SortOrder):
        """Applies sorting criteria."""
        self._sort_key = sort_key
        self._sort_order = sort_order
        self._filter_and_sort()

    def select_object_item(self, item_model: Optional[ObjectItemModel]):
        """Selects an object item and emits the signal."""
        if self._selected_item != item_model:
            self._selected_item = item_model
            self.objectItemSelected.emit(item_model)  # Emit model or None

    # Object list vm.py

    def _on_mod_status_changed(self, original_item_path: str, result: dict):
        """Custom handling for ObjectListVM when object root folder renamed."""
        # Call Logic Parent first

        super()._on_mod_status_changed(original_item_path, result)

        # ---Special additional Objectlist ---

        success = result.get("success", False)
        final_item_path = result.get("new_path") or original_item_path

        if success:
            super()._refresh_folder_grid_items()
            super()._refresh_folder_grid_breadcrumbs()
            # TODO refresh breadcrumb if in current game path
