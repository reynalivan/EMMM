# app/viewmodels/folder_grid_vm.py

import os
from PyQt6.QtCore import QObject, pyqtSignal
from app.models.folder_item_model import FolderItemModel
from app.models.object_item_model import ObjectItemModel
from app.services.mod_management_service import ModManagementService
from app.services.data_loader_service import DataLoaderService
from app.services.thumbnail_service import ThumbnailService  # Import ThumbnailService
from app.viewmodels.object_list_vm import ObjectListVM
from app.viewmodels.main_window_vm import MainWindowVM  # Import MainWindowVM
from app.utils.logger_utils import logger  # Import logger


class FolderGridVM(QObject):
    displayListChanged = pyqtSignal(list)
    loadingStateChanged = pyqtSignal(bool)
    folderItemSelected = pyqtSignal(object)
    breadcrumbChanged = pyqtSignal(list)

    # TODO: Add itemNeedsUpdate signal if needed for thumbnail updates

    def __init__(
        self,
        data_loader: DataLoaderService,
        mod_manager: ModManagementService,
        # Add ThumbnailService injection
        thumbnail_service: ThumbnailService,
        # BatchProcessingService removed earlier, keep it out for now
        parent: QObject | None = None,
    ):  # Ensure parent is last
        super().__init__(parent)
        self._data_loader = data_loader
        self._mod_manager = mod_manager
        # Store injected ThumbnailService
        self._thumbnail_service = thumbnail_service

        # Internal state... (keep as is)
        self._is_safe_mode_on = False
        self._current_object_item: ObjectItemModel | None = None
        self._current_parent_path: str | None = None
        self._object_root_path: str | None = None
        self._selected_item: FolderItemModel | None = None
        self._all_folder_items: list[FolderItemModel] = []
        self.displayed_items: list[FolderItemModel] = []
        self._breadcrumb_path: list[str] = []
        # TODO: Add filter/sort state variables

        self._connect_internal_signals()
        logger.debug("FolderGridVM initialized.")

    def _connect_internal_signals(self):
        """Connect to signals from injected services."""
        logger.debug("Connecting FolderGridVM internal signals...")
        try:
            self._data_loader.folderItemsReady.connect(self._on_folder_items_loaded)
            self._mod_manager.safeModeApplyComplete.connect(self._onSafeModeApplied)
            # TODO: Connect to thumbnail_service signals if needed directly by VM
            # self._thumbnail_service.thumbnailReady.connect(self._on_thumbnail_ready)
            # TODO: Connect to other ModManagementService signals (CRUD, etc.)
        except AttributeError as e:
            logger.error(f"Error connecting internal signals in FolderGridVM: {e}")

    # --- Start Modification: Update connect_global_signals signature ---
    def connect_global_signals(
        self, main_vm: MainWindowVM, object_list_vm: ObjectListVM
    ):
        """Connect to signals from other ViewModels."""
        logger.debug("Connecting FolderGridVM to global VM signals...")
        try:
            # Connect to ObjectListVM for selection changes
            object_list_vm.objectItemSelected.connect(self._on_object_item_selected)

            # Connect to MainWindowVM for global state changes
            main_vm.safeModeStatusChanged.connect(self._on_safe_mode_changed)
            main_vm.globalRefreshRequested.connect(self._handle_global_refresh)
            # TODO: Connect to main_vm.currentPresetChanged if presets are implemented
        except AttributeError as e:
            logger.error(f"Error connecting global signals in FolderGridVM: {e}")

    # --- End Modification ---

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
            self.loadingStateChanged.emit(True)
            self._data_loader.get_folder_items_async(self._current_parent_path)
        else:
            logger.info(
                "FolderGridVM: load_folders_for called with None path, clearing."
            )
            self._current_parent_path = None
            self._all_folder_items = []
            self._filter_and_sort()  # Emit empty list
            self.loadingStateChanged.emit(False)

    def _on_folder_items_loaded(self, parent_path: str, items: list[FolderItemModel]):
        """Handles the folder items loaded by DataLoaderService."""
        # Check if the result is for the currently viewed path
        if parent_path == self._current_parent_path:
            logger.debug(f"FolderGridVM: Received {len(items)} items for {parent_path}")
            self._all_folder_items = items
            self._filter_and_sort()  # Apply filtering/sorting (includes safe mode)
            self.loadingStateChanged.emit(False)
        else:
            logger.debug(
                f"FolderGridVM: Received stale folder items for {parent_path}, ignoring."
            )

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
                self._mod_manager.applySafeModeChanges_async(
                    list(self._all_folder_items), is_on  # Pass a copy
                )

    # bind_mod_service_signals is called from main.py
    def bind_mod_service_signals(self):
        """Connects to signals from ModManagementService."""
        logger.debug("Binding FolderGridVM to ModManagementService signals.")
        # safeModeApplyComplete is connected here
        # TODO: Connect other signals from mod_service (CRUD results etc.) when implemented

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

    # --- Start Modification: Add Refresh Slot ---
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

    # --- End Modification ---

    # --- TODO: Add methods for thumbnail requests ---
    def request_thumbnail_for(self, item_model: FolderItemModel):
        """Requests thumbnail for a specific FolderItemModel."""
        logger.debug(f"FolderGridVM: Requesting thumbnail for {item_model.path}")
        self._thumbnail_service.get_thumbnail_async(item_model.path, "folder")

    def _on_thumbnail_ready(self, item_path: str, result: dict):
        """Handles the thumbnailReady signal from ThumbnailService."""
        # This VM might not need to do anything directly with the thumbnail data itself,
        # as the View (Panel/Delegate) will likely request it and update the specific ItemWidget.
        # However, we might emit an itemNeedsUpdate signal if the View relies on it.
        logger.debug(
            f"FolderGridVM: Thumbnail ready for {item_path}, result: {result.get('status')}"
        )
        # TODO: Emit itemNeedsUpdate(item_path) if needed by the View's update mechanism
        # self.itemNeedsUpdate.emit(item_path)

    # --- TODO: Add methods for CRUD, batch processing etc. ---
