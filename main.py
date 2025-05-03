# Main.py

import sys
from PyQt6.QtWidgets import QApplication
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
from app.viewmodels.settings_vm import SettingsVM
from app.views.sections.object_list_panel import ObjectListPanel
from app.views.sections.folder_grid_panel import FolderGridPanel
from app.views.sections.preview_panel import PreviewPanel
from app.services.file_watcher_service import FileWatcherService
from app.utils.signal_utils import safe_connect


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Enabled Model Mods Manager")
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
        settings_vm = SettingsVM(config_service)
        folder_vm = FolderGridVM(
            data_loader, mod_service, thumbnail_service, file_watcher_service
        )
        object_vm = ObjectListVM(
            data_loader, mod_service, thumbnail_service, file_watcher_service, folder_vm
        )
        preview_vm = PreviewPanelVM(
            data_loader, mod_service, thumbnail_service, image_utils
        )
        main_vm = MainWindowVM(
            config_service,
            mod_service,
            file_watcher_service,
            object_vm,
            folder_vm,
            settings_vm,
        )
        logger.info("View models initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize view models: {e}", exc_info=True)
        return 1

    try:
        # Connect Signals Between VMs
        main_vm.safe_mode_status_changed.connect(folder_vm._on_safe_mode_changed)
        object_vm.pre_mod_status_change.connect(preview_vm.clear_details)
        object_vm.objectItemSelected.connect(folder_vm._on_object_item_selected)
        object_vm.objectItemPathChanged.connect(preview_vm.on_object_path_changed)
        folder_vm.folderItemSelected.connect(preview_vm._on_folder_item_selected)
        object_vm.connect_status_signal()
        folder_vm.connect_status_signal()

        logger.debug("VM signals connected.")
    except AttributeError as e:
        logger.error(
            f"Error connecting VM signals: {e}. Check method names/signatures."
        )

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
        main_vm.initialize_state()
        logger.debug("Initial data loaded.")
    except Exception as e:
        logger.error(f"Error during initial data load: {e}", exc_info=True)
        return 1

    # Start Application Event Loop
    logger.info("Entering event loop...")
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")

    # Clean up file watcher
    try:
        file_watcher_service.stop()
        logger.info("FileWatcherService stopped cleanly.")
    except Exception as e:
        logger.warning(f"Failed to stop FileWatcherService: {e}", exc_info=True)

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
