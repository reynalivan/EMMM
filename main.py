# Main.py
import sys
from pathlib import Path
from PyQt6.QtCore import QThreadPool, Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import SplashScreen, setTheme, Theme
from app.utils.logger_utils import logger
from app.core.constants import APP_ICON_PATH
from app.utils.async_utils import Worker

# Import core constants
from app.core.constants import (
    APP_NAME,
    CACHE_DIR_NAME,
    CONFIG_FILE_NAME,
    DATABASE_FILE_NAME,
    DEFAULT_ICONS,
    LOG_DIR_NAME,
    ORG_NAME,
    CONTEXT_FOLDERGRID,
    CONTEXT_OBJECTLIST,
)

# Import services
from app.services import (
    ConfigService,
    GameService,
    ModService,
    IniParsingService,
    ThumbnailService,
    DatabaseService,
    WorkflowService,
)

# Import utilities
from app.utils import SystemUtils, ImageUtils

# Import view models
from app.viewmodels import (
    MainWindowViewModel,
    ModListViewModel,
    PreviewPanelViewModel,
    SettingsViewModel,
)

# Import the main view
from app.views.main_window import MainWindow


def main():
    """The main entry point for the application."""

    # --- 1. Qt Application Setup ---
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)
    app.setApplicationName("Enabled Model Mods Manager")
    setTheme(Theme.DARK)
    logger.info("Application starting...")

    # --- SPLASH SCREEN SETUP ---
    # 1. Create and configure the splash screen BEFORE heavy work.
    #    The splash screen doesn't need a real parent yet, it will float on top.
    app_icon = QIcon(APP_ICON_PATH)
    app.setWindowIcon(QIcon(":/qfluentwidgets/images/logo.png"))
    splash_screen = SplashScreen(app.windowIcon(), None)  # Parent can be None
    splash_screen.setIconSize(QSize(128, 128))
    splash_screen.show()

    # 2. IMPORTANT: Process events to make sure the splash screen is drawn
    #    before we start the heavy initialization.
    app.processEvents()

    # ---2. Composition Root: Create and Wire All Dependencies ---
    try:
        app_path = Path(".")
        config_path = app_path / CONFIG_FILE_NAME
        db_path = app_path / DATABASE_FILE_NAME
        cache_path = app_path / CACHE_DIR_NAME
        log_path = app_path / LOG_DIR_NAME

        # Ensure necessary directories exist
        cache_path.mkdir(parents=True, exist_ok=True)
        log_path.mkdir(parents=True, exist_ok=True)

        # ---Instantiate Services ---
        # Services with no or minimal dependencies first.
        config_service = ConfigService(config_path)
        game_service = GameService()
        database_service = DatabaseService(db_path)
        ini_parsing_service = IniParsingService()
        thumbnail_service = ThumbnailService(
            cache_dir=cache_path, default_icons=DEFAULT_ICONS
        )

        # --- Run cache cleanup in the background ---
        logger.info("Queueing thumbnail disk cache cleanup task...")
        cleanup_worker = Worker(thumbnail_service.cleanup_disk_cache)

        thread_pool = QThreadPool.globalInstance()
        if thread_pool:
            thread_pool.start(cleanup_worker)
        else:
            logger.critical("Could not get QThreadPool instance to run cache cleanup.")

        # Instantiate utility classes (can be passed as dependencies if needed).
        system_utils = SystemUtils()
        image_utils = ImageUtils()

        # Services that depend on other services.
        mod_service = ModService(
            database_service=database_service,
            image_utils=image_utils,
        )

        workflow_service = WorkflowService(
            mod_service=mod_service, config_service=config_service
        )

        logger.info("Core services and utilities initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize core components: {e}", exc_info=True)
        splash_screen.finish()
        return 1

    # ---Instantiate ViewModels ---
    # Child ViewModels
    objectlist_vm = ModListViewModel(
        context=CONTEXT_OBJECTLIST,
        mod_service=mod_service,
        workflow_service=workflow_service,
        database_service=database_service,
        thumbnail_service=thumbnail_service,
        system_utils=system_utils,
    )

    foldergrid_vm = ModListViewModel(
        context=CONTEXT_FOLDERGRID,
        mod_service=mod_service,
        workflow_service=workflow_service,
        database_service=database_service,
        thumbnail_service=thumbnail_service,
        system_utils=system_utils,
    )
    preview_panel_vm = PreviewPanelViewModel(
        mod_service=mod_service,
        ini_parsing_service=ini_parsing_service,
        thumbnail_service=thumbnail_service,
        foldergrid_vm=foldergrid_vm,
        sys_utils=system_utils,
    )
    settings_vm = SettingsViewModel(
        config_service=config_service,
        game_service=game_service,
        workflow_service=workflow_service,
    )

    # Create the main orchestrator ViewModel, injecting all other components.
    main_window_vm = MainWindowViewModel(
        config_service=config_service,
        workflow_service=workflow_service,
        objectlist_vm=objectlist_vm,
        foldergrid_vm=foldergrid_vm,
        preview_panel_vm=preview_panel_vm,
    )

    # ---3. Instanate the main window ---
    try:
        window = MainWindow(
            main_view_model=main_window_vm, settings_view_model=settings_vm
        )
        window.show()
        logger.debug("Main Window shown.")
    except Exception as e:
        logger.critical(f"Failed to initialize or show Main Window: {e}", exc_info=True)
        return 1

    # --- HIDE SPLASH SCREEN ---
    splash_screen.finish()

    # Start Application Event Loop
    logger.info("Entering event loop...")
    try:
        exit_code = app.exec()
        logger.info(f"Application exiting with code {exit_code}")
    except Exception as e:
        logger.critical(
            f"Unhandled exception in application event loop: {e}", exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
