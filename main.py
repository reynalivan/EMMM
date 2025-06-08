# Main.py
import sys
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# Import All components needed
from app.core.constants import (
    APP_NAME,
    ORG_NAME,
    CONFIG_FILE_NAME,
    DATABASE_FILE_NAME,
    CACHE_DIR_NAME,
    DEFAULT_ICONS,
)
from app.services import (
    ConfigService,
    GameService,
    ModService,
    IniParsingService,
    ThumbnailService,
    DatabaseService,
    WorkflowService,
)
from app.viewmodels import (
    MainWindowViewModel,
    ModListViewModel,
    PreviewPanelViewModel,
    SettingsViewModel,
)
from app.views.main_window import MainWindow
from app.utils import SystemUtils, ImageUtils


def main():
    """The main entry point for the application."""

    # ---1. Qt Application Setup ---
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)

    # ---2. Composition Root: Create and Wire All Dependencies ---
    # Main File and Folder Location
    app_path = Path(".")  # Assuming the application runs from the root folder
    config_path = app_path / CONFIG_FILE_NAME
    db_path = app_path / DATABASE_FILE_NAME
    cache_path = app_path / CACHE_DIR_NAME

    # ---Instantirate Services ---
    # Basic services that do not have dependencies to other services
    config_service = ConfigService(config_path)
    game_service = GameService()
    database_service = DatabaseService(db_path)
    ini_parsing_service = IniParsingService()
    thumbnail_service = ThumbnailService(
        cache_dir=cache_path,
        default_icons={k: Path(v) for k, v in DEFAULT_ICONS.items()},
    )

    # Utilities (Static Class, No need to install, but can be passed if needed)
    system_utils = SystemUtils()
    image_utils = ImageUtils()

    # Services that have dependencies to other services
    mod_service = ModService(
        database_service=database_service,
        system_utils=system_utils,
        image_utils=image_utils,
    )
    workflow_service = WorkflowService(
        mod_service=mod_service, config_service=config_service
    )

    # ---Instantiate ViewModels ---
    # Child ViewModels
    objectlist_vm = ModListViewModel(
        context="objectlist",
        mod_service=mod_service,
        workflow_service=workflow_service,
        database_service=database_service,
        system_utils=system_utils,
    )
    foldergrid_vm = ModListViewModel(
        context="foldergrid",
        mod_service=mod_service,
        workflow_service=workflow_service,
        database_service=database_service,
        system_utils=system_utils,
    )
    preview_panel_vm = PreviewPanelViewModel(
        mod_service=mod_service, ini_parsing_service=ini_parsing_service
    )
    settings_vm = SettingsViewModel(
        config_service=config_service,
        game_service=game_service,
        workflow_service=workflow_service,
    )

    # Main ViewModel (Orchestrator)
    main_window_vm = MainWindowViewModel(
        config_service=config_service,
        workflow_service=workflow_service,
        objectlist_vm=objectlist_vm,
        foldergrid_vm=foldergrid_vm,
        preview_panel_vm=preview_panel_vm,
    )

    # ---3. Instanate the main window ---
    # Inject All VM needed by the mainwindow and its dialogues
    window = MainWindow(main_view_model=main_window_vm, settings_view_model=settings_vm)

    # ---4. Show Window and Start Application ---
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
