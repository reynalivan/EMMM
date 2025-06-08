from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QSplitter, QHBoxLayout, QVBoxLayout, QFrame

from qfluentwidgets import (
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    TitleLabel,
    ComboBox,
    SwitchButton,
    PushButton,
    FluentIcon,
)

# Import ViewModels
from app.viewmodels.main_window_vm import MainWindowViewModel
from app.viewmodels.settings_vm import SettingsViewModel

# Import Custom Panels (Views)
from app.views.sections.objectlist_panel import ObjectListPanel
from app.views.sections.foldergrid_panel import FolderGridPanel
from app.views.sections.preview_panel import PreviewPanel
from app.services.thumbnail_service import ThumbnailService

# Import Dialogs (Views)
# from app.views.dialogs.settings_dialog import SettingsDialog # Will be used later


class MainWindow(FluentWindow):
    """The main application window. It receives fully constructed ViewModels."""

    def __init__(
        self,
        main_view_model: MainWindowViewModel,
        settings_view_model: SettingsViewModel,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        # Store the injected ViewModels
        self.main_window_vm = main_view_model
        self.settings_vm = settings_view_model

        # --- Initialize UI and connect signals ---
        self._init_ui()
        self._bind_view_models()

        # Flow 1.1: Trigger the initial data loading sequence after setup.
        self.main_window_vm.start_initial_load()

    def _init_ui(self):
        """Initializes the main UI layout, toolbars, and panels."""

        # --- Window Settings ---
        self.setWindowTitle("Mods Manager")
        self.setMinimumSize(1324, 760)

        # --- Create Panels ---
        # As per the new architecture, MainWindow creates the panels and injects the child VMs.
        self.object_list_panel = ObjectListPanel(
            viewmodel=self.main_window_vm.objectlist_vm
        )
        self.folder_grid_panel = FolderGridPanel(
            viewmodel=self.main_window_vm.foldergrid_vm
        )
        self.preview_panel = PreviewPanel(
            viewmodel=self.main_window_vm.preview_panel_vm,
        )

        # Apply size constraints from the old code
        self.object_list_panel.setMaximumWidth(380)
        self.object_list_panel.setMinimumWidth(320)
        self.preview_panel.setMaximumWidth(320)
        self.preview_panel.setMinimumWidth(280)

        # --- Header / Toolbar ---
        self.header_widget = QWidget(self)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        header_layout.setSpacing(10)

        # Left side of header
        self.title_label = TitleLabel("EMM Manager")
        self.gamelist_combo = ComboBox()
        self.gamelist_combo.setPlaceholderText("Select Game")
        self.gamelist_combo.setMinimumWidth(180)
        self.gamelist_combo.setEnabled(False)

        self.safe_mode_switch = SwitchButton(text="Safe Mode")
        self.safe_mode_switch.setOnText("Safe Mode")
        self.safe_mode_switch.setOffText("Safe Mode")

        header_layout.addWidget(self.title_label)
        header_layout.addSpacing(20)
        header_layout.addWidget(self.gamelist_combo)
        header_layout.addWidget(self.safe_mode_switch)
        header_layout.addStretch(1)  # Push subsequent widgets to the right

        # Right side of header (Action Buttons)
        self.refresh_button = PushButton("Refresh")
        self.refresh_button.setIcon(FluentIcon.SYNC)

        self.settings_button = PushButton("Settings")
        self.settings_button.setIcon(FluentIcon.SETTING)

        self.play_button = PushButton("Play")
        self.play_button.setIcon(FluentIcon.PLAY)
        self.play_button.setEnabled(False)  # Disabled until a game is active

        header_layout.addWidget(self.refresh_button)
        header_layout.addWidget(self.settings_button)
        header_layout.addWidget(self.play_button)

        # --- Main Content Area (Resizable Panels) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.object_list_panel)
        self.splitter.addWidget(self.folder_grid_panel)
        self.splitter.addWidget(self.preview_panel)

        # Set initial proportions for the panels
        self.splitter.setStretchFactor(0, 2)  # Object List
        self.splitter.setStretchFactor(1, 5)  # Folder Grid
        self.splitter.setStretchFactor(2, 2)  # Preview Panel

        # --- Combine Header and Splitter into the main layout ---
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self.header_widget)

        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        # A subtle line color for dark theme
        line.setStyleSheet("border-top: 1px solid rgba(255, 255, 255, 0.1);")

        main_layout.addWidget(line)
        main_layout.addWidget(
            self.splitter, 1
        )  # The '1' makes the splitter take all available space

        # Set the central widget for the FluentWindow
        central_widget.setObjectName("mainCentralWidget")
        self.addSubInterface(central_widget, FluentIcon.APPLICATION, self.windowTitle())

        # --- Final Touches ---
        # Navigate to the created interface
        self.navigationInterface.setCurrentItem(central_widget.objectName())

    def _bind_view_models(self):
        """Connects signals and slots between this main view and its viewmodels."""
        # This method remains largely the same, but it no longer needs to bind
        # child panels since that can be done in their own __init__.
        # It primarily connects the main_window_vm to this window's slots.
        self.main_window_vm.game_list_updated.connect(self._on_game_list_updated)
        self.main_window_vm.settings_dialog_requested.connect(
            self._on_settings_dialog_requested
        )
        # self.object_list_panel.active_object_requested.connect(
        #    self.main_window_vm.set_active_object
        # )
        # ... other connections ...
        pass

    # --- SLOTS (Responding to global ViewModel signals) ---

    def _on_game_list_updated(self, games: list):
        """Flow 1.3: Updates the game list UI with new data."""
        # This method updates the game list UI, e.g., populating a combobox.
        # self.game_combobox.clear()
        # self.game_combobox.addItems([game.name for game in games])
        # Optionally, set the active game if it was changed.
        # if self.main_window_vm.active_game:
        #     self.game_combobox.setCurrentText(self.main_window_vm.active_game.name)
        pass

    def _on_settings_dialog_requested(self):
        """Flow 1.2: Creates and shows the SettingsDialog."""
        # The settings_vm is already created, just pass it to the dialog.
        # dialog = SettingsDialog(viewmodel=self.settings_vm, parent=self)
        # if dialog.exec():
        #     self.main_window_vm.refresh_all_from_config()
        pass

    def closeEvent(self, event):
        # ... This logic remains the same ...
        super().closeEvent(event)
        pass
