# app/viewmodels/base_item_vm.py

import os
from abc import ABCMeta, abstractmethod
from typing import Literal, Union, Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal

# Adjust import paths as needed
from app.models.object_item_model import ObjectItemModel
from app.models.folder_item_model import FolderItemModel
from app.services.data_loader_service import DataLoaderService
from app.services.mod_management_service import ModManagementService
from app.services.thumbnail_service import ThumbnailService
from app.core import constants
from app.core.async_status_manager import AsyncStatusManager
from app.utils.logger_utils import logger
from abc import ABCMeta, abstractmethod

ItemModelType = Union[ObjectItemModel, FolderItemModel]


class QObjectABCMeta(type(QObject), ABCMeta):
    pass


class BaseItemViewModel(QObject, metaclass=QObjectABCMeta):
    """
    Base ViewModel for item lists, providing common functionality
    for loading state, enable/disable, and thumbnail handling.
    """

    # --- Signals ---
    displayListChanged = pyqtSignal(list)  # list[ItemModelType]
    loadingStateChanged = pyqtSignal(bool)  # Overall list loading
    showError = pyqtSignal(str, str)  # title, message

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
    # --- End Signals ---

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

    # --- Abstract Methods ---
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
    def _load_items_for_path(self, path: str | None):
        """Load items for the specific context (game path or folder path)."""
        raise NotImplementedError

    @abstractmethod
    def _get_current_path_context(self) -> str | None:
        """Return the current relevant path for context/refresh."""
        raise NotImplementedError

    # --- End Abstract Methods ---

    def _connect_internal_signals(self):
        """Connect internal service signals."""
        try:
            if self._mod_manager:
                self._mod_manager.modStatusChangeComplete.connect(
                    self._on_mod_status_changed
                )

            if self._thumbnail_service:
                self._thumbnail_service.thumbnailReady.connect(self._on_thumbnail_ready)

        except Exception as e:
            logger.error(
                f"Error connecting internal signals in {self.__class__.__name__}: {e}",
                exc_info=True,
            )

    # --- Public Slots / Methods ---
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

    # --- Internal Slots ---

    def _on_mod_status_changed(self, original_item_path: str, result: dict):
        """
        Handles async status change results. Updates UI and internal model accordingly.
        """
        if not self._is_handling_status_changes:
            logger.debug(
                f"{self.__class__.__name__}: Mod status change ignored, handling disabled."
            )
            return

        # --- 1. Filter by Item Type ---
        if self._get_item_type() != result.get("item_type"):
            logger.debug(
                f"{self.__class__.__name__}: Skipping mod status change for {original_item_path} due to VM type mismatch."
            )
            return

        success = result.get("success", False)
        new_path: str | None = result.get("new_path")
        final_status: bool = result.get("new_status")
        original_status: bool = result.get("original_status")
        actual_name: str | None = result.get("actual_name")
        error_msg: str | None = result.get("error")
        final_item_path: str = new_path if success and new_path else original_item_path

        logger.debug(
            f"{self.__class__.__name__}: Processing mod result for {original_item_path}. Success: {success}"
        )

        # --- 2. Update Status Manager ---
        if success:
            self._status_manager.mark_success(original_item_path)
        else:
            self._status_manager.mark_failed(
                original_item_path, error_msg or "Unknown error"
            )

        # --- 3. Retrieve Original State ---
        original_state = self._original_state_on_toggle.pop(original_item_path, None)
        original_display_name = (
            original_state["display_name"]
            if original_state
            else os.path.basename(original_item_path)
        )

        if not original_state:
            logger.warning(
                f"Original pre-toggle state for {original_item_path} not found!"
            )

        # --- 4. Determine Final UI Payload ---
        definitive_status = final_status if success else original_status
        definitive_display_name = (
            os.path.basename(final_item_path)
            if definitive_status
            else (actual_name or original_display_name)
        )
        definitive_path = final_item_path

        update_payload = {
            "status": definitive_status,
            "display_name": definitive_display_name,
            "path": definitive_path,
        }

        # --- 5. Emit UI Signals ---
        self.updateItemDisplay.emit(original_item_path, update_payload)
        self.setItemLoadingState.emit(original_item_path, False)

        result_title = (
            "Operation Failed"
            if not success
            else f"Mod {'Enabled' if definitive_status else 'Disabled'}"
        )
        result_content = (
            error_msg
            or f"'{definitive_display_name}' successfully {'enabled' if definitive_status else 'disabled'}."
        )

        self.operation_finished.emit(
            original_item_path, final_item_path, result_title, result_content, success
        )

        # --- 6. Update Internal Model (Best Effort) ---
        if success:
            found_model = next(
                (
                    m
                    for m in self._get_item_list()
                    if os.path.normpath(m.path) == os.path.normpath(original_item_path)
                    or (
                        new_path is not None
                        and os.path.normpath(m.path) == os.path.normpath(new_path)
                    )
                ),
                None,
            )
            if found_model:
                found_model.status = definitive_status
                if new_path and os.path.normpath(found_model.path) != os.path.normpath(
                    new_path
                ):
                    found_model.path = new_path
                    found_model.folder_name = os.path.basename(new_path)
            else:
                logger.warning(
                    f"{self.__class__.__name__}: Model for {original_item_path} updated, but not found in internal list."
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
