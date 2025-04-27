# app/viewmodels/folder_grid_vm.py

import os
from typing import List, Literal, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from app.models.folder_item_model import FolderItemModel
from app.models.object_item_model import ObjectItemModel
from app.services.mod_management_service import ModManagementService
from app.services.data_loader_service import DataLoaderService
from app.services.thumbnail_service import ThumbnailService  # Import ThumbnailService
from app.viewmodels.object_list_vm import ObjectListVM
from app.viewmodels.main_window_vm import MainWindowVM  # Import MainWindowVM
from app.utils.logger_utils import logger  # Import logger
from app.core.constants import DISABLED_PREFIX
from .base_item_vm import BaseItemViewModel, ItemModelType  # Import base class


class FolderGridVM(BaseItemViewModel):
    folderItemSelected = pyqtSignal(object)
    breadcrumbChanged = pyqtSignal(list)

    def __init__(
        self,
        data_loader: DataLoaderService,
        mod_service: ModManagementService,
        thumbnail_service: ThumbnailService,
        parent: Optional[QObject] = None,
    ):  # Ensure parent is last
        # Call base class constructor with shared services
        super().__init__(data_loader, mod_service, thumbnail_service, parent)
        # FolderGridVM specific state
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

    def _get_item_list(self) -> List[FolderItemModel]:
        """Returns the internal list of folder items."""
        return self._all_folder_items

    def _get_item_type(self) -> Literal["object", "folder"]:
        """Returns the item type handled by this VM."""
        return "folder"

    def _load_items_for_path(self, path: str | None):
        """Implementation for loading folder items."""
        self.load_folders_for(path)

    def _get_current_path_context(self) -> str | None:
        """Returns the current parent folder path being viewed."""
        return self._current_parent_path

    def _filter_and_sort(self):
        """Filters and sorts the internal list (_all_folder_items)"""
        logger.debug(
            f"FolderGridVM: Filtering and sorting items. Safe mode: {self._is_safe_mode_on}"
        )
        # TODO: Implement actual filtering based on text, status dropdown
        # TODO: Implement sorting based on selected criteria

        filtered_items = []
        for item in self._all_folder_items:
            # Safe Mode Filter
            if self._is_safe_mode_on and not item.is_safe:
                continue  # Skip unsafe items when safe mode is ON

            # TODO: Add other filters (text search, status dropdown) here
            # if self._filter_status == "Enabled" and not item.status: continue
            # if self._filter_status == "Disabled" and item.status: continue
            # if self._filter_text and self._filter_text.lower() not in item.display_name.lower(): continue

            filtered_items.append(item)

        # TODO: Add sorting logic here
        # key = lambda i: getattr(i, self._sort_key, i.display_name)
        # reverse = self._sort_order == Qt.SortOrder.DescendingOrder
        # filtered_items.sort(key=key, reverse=reverse)
        filtered_items.sort(
            key=lambda item: item.display_name
        )  # Simple sort by name for now

        self.displayed_items = filtered_items
        logger.debug(
            f"FolderGridVM: Emitting {len(self.displayed_items)} items after filter/sort."
        )
        self.displayListChanged.emit(self.displayed_items)

    def connect_global_signals(
        self, main_vm: MainWindowVM, object_list_vm: ObjectListVM
    ):
        """Connect to signals from other ViewModels."""
        # logger.debug("Connecting FolderGridVM to global VM signals...") # Keep lean
        try:
            object_list_vm.objectItemSelected.connect(self._on_object_item_selected)
            main_vm.safe_mode_status_changed.connect(self._on_safe_mode_changed)
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
        """Connects to signals from ModManagementService."""
        logger.debug("Binding FolderGridVM to ModManagementService signals.")
        # safeModeApplyComplete is connected here
        # TODO: Connect other signals from mod_service (CRUD results etc.) when implemented

    def _on_object_item_selected(self, selected_item: ObjectItemModel | None):
        """Handles selection change from ObjectListVM."""
        logger.debug(
            f"FolderGridVM: Object item selected -> {selected_item.path if selected_item else 'None'}"
        )
        if selected_item is None:
            # Clear grid if object is deselected
            self._current_object_item = None
            self._object_root_path = None
            self._current_parent_path = None
            self._breadcrumb_path = []
            self.breadcrumbChanged.emit([])
            self._all_folder_items = []
            self._filter_and_sort()  # Will emit empty list
            self.folderItemSelected.emit(None)  # Deselect item in preview
            return

        # Only reload if the selected object actually changed
        if self._current_object_item != selected_item:
            self._current_object_item = selected_item
            self._object_root_path = os.path.normpath(selected_item.path)
            self._breadcrumb_path = [
                os.path.basename(self._object_root_path)
            ]  # Start breadcrumb with object folder name
            self.breadcrumbChanged.emit(self._breadcrumb_path)
            self.load_folders_for(self._object_root_path)  # Load top-level items
            self.folderItemSelected.emit(
                None
            )  # Deselect previous folder item when object changes

    def load_folders_for(self, parent_path: str | None):
        """Loads folder items for the given parent path."""
        if parent_path:
            logger.info(f"FolderGridVM: Loading folders for path: {parent_path}")
            self._current_parent_path = os.path.normpath(parent_path)

            self._data_loader.get_folder_items_async(self._current_parent_path)
        else:
            logger.info(
                "FolderGridVM: load_folders_for called with None path, clearing."
            )
            self._current_parent_path = None
            self._all_folder_items = []
            self._filter_and_sort()  # Emit empty list

    def _on_folder_items_loaded(self, parent_path: str, items: list[FolderItemModel]):
        """Handles the folder items loaded by DataLoaderService."""
        # Check if the result is for the currently viewed path
        if parent_path == self._current_parent_path:
            logger.debug(f"FolderGridVM: Received {len(items)} items for {parent_path}")
            self._all_folder_items = items
            self._filter_and_sort()  # Apply filtering/sorting (includes safe mode)
        else:
            logger.debug(
                f"FolderGridVM: Received stale folder items for {parent_path}, ignoring."
            )

    def _on_safe_mode_changed(self, is_on: bool):
        """Handles safe mode status changes from MainWindowVM."""
        logger.info(f"FolderGridVM: Safe mode changed to {is_on}")
        if self._is_safe_mode_on != is_on:
            self._is_safe_mode_on = is_on
            # Apply filtering immediately to hide/show items
            self._filter_and_sort()
            # Trigger background task to rename folders if necessary
            if self._all_folder_items:  # Only run if we have items loaded
                logger.debug("Requesting ModManager to apply safe mode changes...")
                # Pass a copy in case the list changes while task runs? Or ensure task handles it.
                self._mod_service.applySafeModeChanges_async(
                    list(self._all_folder_items), is_on  # Pass a copy
                )

    def _onSafeModeApplied(self, summary: dict):
        """Handles completion of the safe mode renaming task."""
        # The renaming might have happened, reload data to reflect FS changes
        logger.info(
            f"FolderGridVM: Safe mode apply task completed: {summary}. Refreshing folder list."
        )
        if self._current_parent_path:
            # Reloading might cause flicker, but ensures consistency with FS
            self.load_folders_for(self._current_parent_path)
            # Breadcrumb shouldn't change just from safe mode toggle
            # self.breadcrumbChanged.emit(self._breadcrumb_path) # Probably not needed here
        else:
            logger.warning(
                "Safe mode applied but current_parent_path is None. Cannot refresh."
            )

    def select_folder_item(self, item_model: FolderItemModel | None):
        """Selects a folder item and notifies the PreviewPanel."""
        if self._selected_item != item_model:
            logger.debug(
                f"FolderGridVM: Selecting folder item -> {item_model.path if item_model else 'None'}"
            )
            self._selected_item = item_model
            # Pemanggilan ini sekarang valid untuk item_model=None juga
            self.folderItemSelected.emit(item_model)

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

    def handle_item_status_toggle_request(
        self, item_model: FolderItemModel, enable: bool
    ):
        """Handle toggle request from Grid Panel."""
        if not item_model or not hasattr(item_model, "path"):
            logger.error(
                f"FolderGridVM: Invalid item_model in handle_item_status_toggle_request: {item_model}"
            )
            return

        path = item_model.path

        if self._status_manager.is_item_pending(path):
            logger.debug(f"Toggle request ignored, item already pending: {path}")
            return

        # Save original state
        self._original_state_on_toggle[path] = {
            "display_name": item_model.display_name,
            "status": item_model.status,
        }

        self._status_manager.mark_pending(path)

        self.operation_started.emit(path, f"{'Enabling' if enable else 'Disabling'}...")

        # Start async task
        self._mod_manager.set_mod_enabled_async(path, enable, self._get_item_type())

        self.setItemLoadingState.emit(path, True)

    def update_root_path(self, new_path: str):
        """Update object root and reload folder list if still active."""
        self._object_root_path = os.path.normpath(new_path)
        self._current_parent_path = os.path.normpath(new_path)
        self._breadcrumb_path = [os.path.basename(new_path)]

        self.breadcrumbChanged.emit(self._breadcrumb_path)
        self.load_folders_for(new_path)
