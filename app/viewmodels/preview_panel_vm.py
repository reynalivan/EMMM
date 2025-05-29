# app/viewmodels/preview_panel_vm.py

import os
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPixmap
from app.services.data_loader_service import DataLoaderService
from app.services.mod_management_service import ModManagementService
from app.services.thumbnail_service import ThumbnailService
from app.viewmodels.folder_grid_vm import FolderGridVM
from app.models.folder_item_model import FolderItemModel
from app.core import constants
from app.utils.logger_utils import logger


class PreviewPanelVM(QObject):
    # --- Signals ---

    display_data_updated = pyqtSignal(dict)
    thumbnail_paths_updated = pyqtSignal(list)

    ini_list_updated = pyqtSignal(list)
    status_updated = pyqtSignal(bool)

    show_error = pyqtSignal(str, str)
    status_update_finished = pyqtSignal(bool)
    description_save_finished = pyqtSignal(bool)
    thumbnail_operation_finished = pyqtSignal(bool)
    operation_started = pyqtSignal(str, str)  # item_path, title
    operation_finished = pyqtSignal(
        str, str, str, str, bool
    )  # original_path, final_path, title, content, success

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

        self._current_item: FolderItemModel | None = None
        self._title: str = ""
        self._description: str = ""
        self._is_enabled: bool = False
        self._thumbnail_image_paths: list[str] = []
        self._ini_file_list: list[str] = []
        self._preview_pixmap: QPixmap | None = None

        self._connect_internal_signals()
        logger.debug("PreviewPanelVM initialized.")

    def _connect_internal_signals(self):
        """Connect internal service signals."""
        logger.debug("Connecting PreviewPanelVM internal signals...")
        try:
            self._data_loader.iniFilesReady.connect(self._on_ini_files_loaded)
            self._thumbnail_service.previewThumbnailsFound.connect(
                self._on_preview_thumbnails_found
            )

        except AttributeError as e:
            logger.error(f"Error connecting internal signals in PreviewPanelVM: {e}")

    def connect_folder_grid_vm(self, folder_grid_vm: FolderGridVM):
        """Connect to signals from FolderGridVM."""
        logger.debug("Connecting PreviewPanelVM to FolderGridVM signals.")
        try:
            folder_grid_vm.folderItemSelected.connect(self._on_folder_item_selected)
        except AttributeError as e:
            logger.error(f"Error connecting to FolderGridVM signals: {e}")

    # --- Public Methods ---

    def clear_details(self):
        """Clears preview panel details."""
        logger.debug("Clearing preview panel details.")
        self._current_item = None
        self._title = "No Selection"
        self._description = ""
        self._is_enabled = False
        self._thumbnail_image_paths = []
        self._ini_file_list = []
        if self._preview_pixmap:
            self._preview_pixmap = None  # Auto-release
        self.display_data_updated.emit({})
        self.thumbnail_paths_updated.emit([])
        self.ini_list_updated.emit([])

    def set_status(self, is_enabled: bool):
        """Manually updates current item's status and notifies view."""
        if self._current_item is None:
            logger.warning("PreviewPanelVM: No current item to set status for.")
            return

        logger.debug(
            f"PreviewPanelVM: Setting status to {'ENABLED' if is_enabled else 'DISABLED'}"
        )

        self._is_enabled = is_enabled
        self._current_item.status = is_enabled

        # Emit signals to update UI
        self.status_updated.emit(is_enabled)
        self.status_update_finished.emit(True)

    # --- Private Slots ---

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

        self._title = item_model.display_name
        self._description = item_model.description
        self._is_enabled = item_model.status

        self.display_data_updated.emit(
            {
                "title": self._title,
                "description": self._description,
                "is_enabled": self._is_enabled,
            }
        )

        self._thumbnail_image_paths = []
        self._ini_file_list = []
        self.thumbnail_paths_updated.emit([])
        self.ini_list_updated.emit([])

        self._data_loader.get_ini_files_async(item_model.path)
        self._thumbnail_service.find_preview_thumbnails_async(item_model.path)

    def _on_ini_files_loaded(self, folder_path: str, ini_list: list[str]):
        """Handles INI files loaded by DataLoaderService."""
        if self._current_item and folder_path == self._current_item.path:
            logger.debug(
                f"PreviewPanelVM: Received {len(ini_list)} INI files for {folder_path}"
            )
            self._ini_file_list = sorted(ini_list)
            self.ini_list_updated.emit(self._ini_file_list)
        else:
            logger.debug(
                f"PreviewPanelVM: Received stale INI files for {folder_path}, ignoring."
            )

    def _on_preview_thumbnails_found(self, folder_path: str, image_paths: list[str]):
        """Handles preview thumbnail paths found by ThumbnailService."""
        if self._current_item and folder_path == self._current_item.path:
            logger.debug(
                f"PreviewPanelVM: Received {len(image_paths)} preview paths for {folder_path}"
            )

            self._thumbnail_image_paths = image_paths

            # Optional: preload first image to RAM via QPixmap to prevent disk lock
            if image_paths:
                first_image = image_paths[0]
                pixmap = QPixmap(first_image)
                self._preview_pixmap = pixmap  # Simpan biar bisa release nanti
            else:
                self._preview_pixmap = None

            self.thumbnail_paths_updated.emit(self._thumbnail_image_paths)
        else:
            logger.debug(
                f"PreviewPanelVM: Received stale preview paths for {folder_path}, ignoring."
            )

    def _on_item_operation_started(self, item_path: str, title: str):
        """Handles item operation started: Disable UI temporarily if needed."""
        self.setEnabled(False)
        # Optional: bisa tampilkan processing info di preview jika mau
        logger.debug(f"PreviewPanel: Operation started for {item_path}")

    def _on_item_operation_finished(
        self,
        original_item_path: str,
        final_item_path: str,
        title: str,
        content: str,
        success: bool,
    ):
        """Handles item operation finished: Re-enable UI."""
        self.setEnabled(True)
        logger.debug(
            f"PreviewPanel: Operation finished for {original_item_path} -> {final_item_path}. Success: {success}"
        )

    def on_object_path_changed(self, old_path: str, new_path: str):
        """Update preview panel if current item path has changed."""
        if not self._current_item:
            return
        if os.path.normpath(old_path) != os.path.normpath(self._current_item.path):
            return

        logger.info(f"PreviewPanelVM: Current item path updated to {new_path}")
        self._current_item.path = new_path

        self._data_loader.get_ini_files_async(new_path)
        self._thumbnail_service.find_preview_thumbnails_async(new_path)
