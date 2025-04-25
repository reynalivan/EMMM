# App/viewmodels/preview panel vm.py


# ---Imports ---

from PyQt6.QtCore import QObject, pyqtSignal
from app.services.data_loader_service import DataLoaderService
from app.services.mod_management_service import ModManagementService
from app.services.thumbnail_service import ThumbnailService
from app.utils.image_utils import ImageUtils  # Make sure to import
from app.viewmodels.folder_grid_vm import FolderGridVM
from app.models.folder_item_model import FolderItemModel
from app.core import constants  # Import Constants if needed (eg Key_Description)
from app.utils.logger_utils import logger

# ---End Imports ---


class PreviewPanelVM(QObject):
    # ---Signals (according to the contract) ---

    display_data_updated = pyqtSignal(dict)
    thumbnail_paths_updated = pyqtSignal(list)  # List[str]

    ini_list_updated = pyqtSignal(list)  # list[str] (kontrak: list[str])

    show_error = pyqtSignal(str, str)
    status_update_finished = pyqtSignal(bool)
    description_save_finished = pyqtSignal(bool)
    thumbnail_operation_finished = pyqtSignal(bool)

    # ---End Signals ---

    # ---Init Method (improvement here) ---

    def __init__(
        self,
        data_loader: DataLoaderService,
        mod_manager: ModManagementService,
        thumbnail_service: ThumbnailService,
        image_utils: ImageUtils,
        parent: QObject | None = None,
    ):  # Add parent = none at the end

        super().__init__(parent)  # Call Super () only with Parent

        # Save dependencies

        self._data_loader = data_loader
        self._mod_manager = mod_manager
        self._thumbnail_service = thumbnail_service
        self._image_utils = image_utils  # Simple Instance Image_utils

        # Internal State Initialization

        self._current_item: FolderItemModel | None = None
        self._title: str = ""
        self._description: str = ""
        self._is_enabled: bool = False
        self._thumbnail_image_paths: list[str] = []
        self._ini_file_list: list[str] = []  # According to contract: List of strings

        # Connect to the internal signal of the service if needed

        self._connect_internal_signals()
        logger.debug("PreviewPanelVM initialized.")

    def _connect_internal_signals(self):
        """Connect to signals from injected services."""
        logger.debug("Connecting PreviewPanelVM internal signals...")
        try:
            # Make sure this signal is in the related service

            self._data_loader.iniFilesReady.connect(self._on_ini_files_loaded)
            self._thumbnail_service.previewThumbnailsFound.connect(
                self._on_preview_thumbnails_found
            )
            self._mod_manager.modStatusChangeComplete.connect(
                self._on_mod_status_changed
            )
            # Todo: Make sure ModmanagementService has a ModinfoUpDateCompelet signal
            # Self
            # TODO: Make sure the thumbnail service has a signal to save (eg Savethumbnailcomplete)
            # Self._Thumbnail_Service

        except AttributeError as e:
            logger.error(f"Error connecting internal signals in PreviewPanelVM: {e}")

    def connect_folder_grid_vm(self, folder_grid_vm: FolderGridVM):
        """Connect to signals from FolderGridVM."""
        logger.debug("Connecting PreviewPanelVM to FolderGridVM signals.")
        try:
            folder_grid_vm.folderItemSelected.connect(self._on_folder_item_selected)
        except AttributeError as e:
            logger.error(f"Error connecting to FolderGridVM signals: {e}")

    # ---Public methods /slots (implementation according to contract) ---

    # (Add implementation to set_status, save_description, paste_thumbnail, upload_thumbnail, clear_details)
    # ... (implementation of other public methods such as in the previous Thought Process) ...

    # ---Private Slots ---

    def _on_folder_item_selected(self, item_model: FolderItemModel | None):
        """Handles selection changes from FolderGridVM."""
        if item_model == self._current_item:
            return  # No change

        if item_model is None:
            logger.debug("PreviewPanelVM: Folder item selection cleared.")
            self.clear_details()
            return

        logger.debug(f"PreviewPanelVM: Folder item selected: {item_model.path}")
        self._current_item = item_model

        # Update internal state from the model

        self._title = item_model.display_name
        self._description = item_model.description  # Use property from model

        self._is_enabled = item_model.status

        # Emit updated data to the view

        self.display_data_updated.emit(
            {
                "title": self._title,
                "description": self._description,
                "is_enabled": self._is_enabled,  # Use the key name according to the signal contract
            }
        )

        # Reset and request additional details

        self._thumbnail_image_paths = []
        self._ini_file_list = []
        self.thumbnail_paths_updated.emit(self._thumbnail_image_paths)
        self.ini_list_updated.emit(self._ini_file_list)  # Emit list kosong

        # Trigger async loading

        self._data_loader.get_ini_files_async(item_model.path)
        self._thumbnail_service.find_preview_thumbnails_async(item_model.path)

    def _on_ini_files_loaded(self, folder_path: str, ini_list: list[str]):
        """Handles the list of INI files loaded by DataLoaderService."""
        if self._current_item and folder_path == self._current_item.path:
            logger.debug(
                f"PreviewPanelVM: Received {len(ini_list)} INI files for {folder_path}"
            )
            self._ini_file_list = sorted(ini_list)  # Contract: List [STR]

            self.ini_list_updated.emit(self._ini_file_list)
        else:
            logger.debug(
                f"PreviewPanelVM: Received stale INI files for {folder_path}, ignoring."
            )

    def _on_preview_thumbnails_found(self, folder_path: str, image_paths: list[str]):
        """Handles the list of preview thumbnail paths found by ThumbnailService."""
        if self._current_item and folder_path == self._current_item.path:
            logger.debug(
                f"PreviewPanelVM: Received {len(image_paths)} preview paths for {folder_path}"
            )
            self._thumbnail_image_paths = image_paths
            self.thumbnail_paths_updated.emit(self._thumbnail_image_paths)
        else:
            logger.debug(
                f"PreviewPanelVM: Received stale preview paths for {folder_path}, ignoring."
            )

    def _on_mod_status_changed(self, item_path: str, result: dict):
        """Handles completion of enable/disable operation."""
        if self._current_item and item_path == self._current_item.path:
            success = result.get("success", False)
            logger.debug(
                f"PreviewPanelVM: Mod status change result for {item_path}. Success: {success}"
            )
            self.status_update_finished.emit(success)
            if success:
                new_status = result.get("new_status")
                if new_status is not None:
                    self._is_enabled = new_status
                    # Re-emit data to ensure view reflects latest status

                    self.display_data_updated.emit(
                        {
                            "title": self._title,
                            "description": self._description,
                            "is_enabled": self._is_enabled,
                        }
                    )
            else:
                self.show_error.emit(
                    "Status Change Failed", result.get("error", "Unknown error")
                )

    # TODO: Implement other slots like _on_mod_info_updated, _on_thumbnail_saved etc.
    # TODO: Implement public methods like clear_details, set_status, save_description etc.

    def clear_details(self):  # Added basic implementation
        """Clears the preview panel details."""
        logger.debug("Clearing preview panel details.")
        self._current_item = None
        self._title = "No Selection"
        self._description = ""
        self._is_enabled = False
        self._thumbnail_image_paths = []
        self._ini_file_list = []
        self.display_data_updated.emit({})  # Emit empty dict

        self.thumbnail_paths_updated.emit([])
        self.ini_list_updated.emit([])
