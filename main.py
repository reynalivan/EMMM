# Main.py

import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
)  # Make sure Qwidget is there

from typing import Dict, Optional
from qfluentwidgets import setTheme, Theme
from app.utils.logger_utils import logger
from app.views.main_window import MainWindow
from app.services.config_service import ConfigService
from app.services.data_loader_service import DataLoaderService
from app.services.mod_management_service import ModManagementService
from app.services.thumbnail_service import ThumbnailService
from app.utils.image_cache import ImageCache
from app.utils.image_utils import ImageUtils
from app.core import constants
from app.viewmodels.main_window_vm import MainWindowVM
from app.viewmodels.object_list_vm import ObjectListVM
from app.viewmodels.preview_panel_vm import PreviewPanelVM
from app.viewmodels.folder_grid_vm import FolderGridVM
from app.views.sections.object_list_panel import ObjectListPanel
from app.views.sections.folder_grid_panel import FolderGridPanel
from app.views.sections.preview_panel import PreviewPanel
from app.services.file_watcher_service import FileWatcherService


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Apply Fluent Theme
    setTheme(Theme.DARK)
    logger.info("Application starting...")

    # Initialize Services & Utilities
    try:
        config_service = ConfigService(config_filepath=constants.CONFIG_FILENAME)
        mod_service = ModManagementService()
        data_loader = DataLoaderService()
        image_cache = ImageCache(
            cache_dir=constants.CACHE_DIR,
            max_size_mb=constants.DEFAULT_CACHE_MAX_MB,
            expiry_days=constants.DEFAULT_CACHE_EXPIRY_DAYS,
        )
        image_utils = ImageUtils()
        thumbnail_service = ThumbnailService(image_cache, image_utils)
        file_watcher_service = FileWatcherService()
        logger.info("Core services and utilities initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize core services: {e}", exc_info=True)
        # TODO: Show critical error message to user
        return 1

    # Initialize ViewModels
    try:
        folder_vm = FolderGridVM(data_loader, mod_service, thumbnail_service)
        object_vm = ObjectListVM(
            data_loader, mod_service, thumbnail_service, FolderGridVM
        )
        preview_vm = PreviewPanelVM(
            data_loader, mod_service, thumbnail_service, image_utils
        )
        main_vm = MainWindowVM(config_service, object_vm, folder_vm)

        # === Set file watcher explicitly ===
        main_vm.bind_filewatcher_service(file_watcher_service)
        object_vm.set_filewatcher_service(file_watcher_service)
        folder_vm.set_filewatcher_service(file_watcher_service)

        file_watcher_service.enable()
        file_watcher_service.start()

        # Rebind file watcher
        object_vm.rebind_filewatcher()

        logger.info("View models initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize view models: {e}", exc_info=True)
        # TODO: Show critical error message to user

        return 1

    # Connect Signals Between VMs

    try:
        # Signature assumes main_vm needed for safe mode check in FolderGridVM

        folder_vm.connect_global_signals(main_vm, object_vm)
        object_vm.connect_global_signals(main_vm)
        preview_vm.connect_folder_grid_vm(folder_vm)
        folder_vm.bind_mod_service_signals()
        logger.debug("VM signals connected.")
    except AttributeError as e:
        logger.error(
            f"Error connecting VM signals: {e}. Check method names/signatures."
        )

    # File Watcher related TODOs removed

    # Initialize UI Panels

    try:
        obj_panel = ObjectListPanel(object_vm)
        fld_panel = FolderGridPanel(folder_vm)
        prv_panel = PreviewPanel(preview_vm)
        logger.debug("UI Panels initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize UI panels: {e}", exc_info=True)
        return 1

    # Initialize Main Window (UI)

    try:
        win = MainWindow(main_vm, obj_panel, fld_panel, prv_panel)
        win.show()
        logger.debug("Main Window shown.")
    except Exception as e:
        logger.critical(f"Failed to initialize or show Main Window: {e}", exc_info=True)
        return 1

    # Load Initial Application Data
    try:
        main_vm.load_initial_data()
        logger.debug("Initial data loaded.")
    except Exception as e:
        logger.error(f"Error during initial data load: {e}", exc_info=True)
        return 1

    # Start Application Event Loop

    logger.info("Entering event loop...")
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")

    # TODO: Add cleanup code here if needed

    return exit_code


if __name__ == "__main__":
    # Basic top-level exception handler

    try:
        result = main()
        sys.exit(result)
    except Exception as e:
        logger.critical(f"Unhandled exception occurred in __main__: {e}", exc_info=True)
        # TODO: Show critical error message box to user if possible

        sys.exit(1)
