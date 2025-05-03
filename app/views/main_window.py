# App/views/main window.py


# ---Standard Qt Imports ---

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QFrame
from PyQt6.QtCore import Qt, QSize

# ---Fluent Widget Imports ---

from qfluentwidgets import (
    FluentWindow,
    TitleLabel,
    ComboBox,
    SwitchButton,
    PushButton,
    TransparentToolButton,
    FluentIcon,
    BodyLabel,
    setCustomStyleSheet,
)  # Import necessary components


# ---App Imports ---
from app.views.dialogs.settings_dialog import SettingsDialog
from app.viewmodels.settings_vm import SettingsVM
from app.viewmodels.main_window_vm import MainWindowVM
from app.views.sections.object_list_panel import ObjectListPanel
from app.views.sections.folder_grid_panel import FolderGridPanel
from app.views.sections.preview_panel import PreviewPanel
from app.utils.logger_utils import logger
from app.utils.ui_utils import show_error

# ---End Imports ---


class MainWindow(FluentWindow):  # Inherit from FluentWindow

    def __init__(
        self,
        view_model: MainWindowVM,
        obj_list_panel: ObjectListPanel,
        fld_grid_panel: FolderGridPanel,
        prv_panel: PreviewPanel,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.vm = view_model

        # Store references to the panels passed from main.py
        self.obj_list_panel = obj_list_panel
        self.fld_grid_panel = fld_grid_panel
        self.prv_panel = prv_panel
        self.obj_list_panel.setMaximumWidth(320)
        self.prv_panel.setMaximumWidth(300)
        self.setMinimumSize(1280, 760)  # Adjusted minimum height slightly

        self._setup_ui()
        self._connect_signals()

        # Set window title (FluentWindow might handle this differently)
        self.setWindowTitle("EMMM - Enabled Model Mods Manager")

    def _setup_ui(self):
        # ---Header /Toolbar ---

        self.header_widget = QWidget(self)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        header_layout.setSpacing(10)
        self.header_widget.setObjectName("MainWindowHeader")  # For styling if needed

        # Left side of header
        self.title_label = TitleLabel("EMMM v0.1")  # Or get version from VM/constants
        self.gamelist_combo = ComboBox()
        self.gamelist_combo.setPlaceholderText("Select Game")
        self.gamelist_combo.setMinimumWidth(150)
        self.safe_mode_switch = SwitchButton("Safe Mode")

        # TODO: Implement Preset ComboBox later
        self.preset_combo = ComboBox()
        self.preset_combo.setPlaceholderText("No Presets")
        self.preset_combo.setMinimumWidth(150)
        self.preset_combo.setEnabled(False)  # Disable for now

        header_layout.addWidget(self.title_label)
        header_layout.addSpacing(20)
        header_layout.addWidget(self.gamelist_combo)
        header_layout.addWidget(self.safe_mode_switch)
        header_layout.addWidget(self.preset_combo)
        header_layout.addStretch(1)  # Push buttons to the right

        # Right side of header (Action Buttons)
        # TODO: Add Refresh Button if needed based on contract/design
        # self.refresh_button = PushButton("Refresh")
        # header_layout.addWidget(self.refresh_button)

        self.settings_button = PushButton("Settings")
        self.settings_button.setIcon(FluentIcon.SETTING)
        header_layout.addWidget(self.settings_button)

        # TODO: Add Play Button functionality later

        self.play_button = PushButton("Play")  # Or PrimaryPushButton?
        self.play_button.setIcon(FluentIcon.PLAY)
        self.play_button.setEnabled(False)  # Disable for now
        header_layout.addWidget(self.play_button)

        # ---Main Content Area (Resizable Panels) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.obj_list_panel)
        self.splitter.addWidget(self.fld_grid_panel)
        self.splitter.addWidget(self.prv_panel)

        # Set initial sizes or stretch factors for the panels
        self.splitter.setStretchFactor(0, 2)  # Object List smaller
        self.splitter.setStretchFactor(1, 5)  # Folder Grid largest
        self.splitter.setStretchFactor(2, 2)  # Preview medium

        # Apply some styling to the splitter handle (optional)
        self.splitter.setStyleSheet(
            "QSplitter::handle { background-color: #222; width: 3px; }"
        )

        # ---Combine Header and Splitter ---
        central_widget = QWidget()
        central_widget.setObjectName("CentralContentWidget")
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(
            0, 0, 0, 0
        )  # No margins for the main layout itself

        main_layout.setSpacing(0)  # No spacing between header and splitter
        main_layout.addWidget(self.header_widget)

        # Add a small separator line (optional)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("border-top: 1px solid #333;")  # Style the line

        main_layout.addWidget(line)
        main_layout.addWidget(self.splitter, 1)  # Splitter takes remaining space

        # Set the combined widget as the central content
        self.addSubInterface(central_widget, FluentIcon.APPLICATION, self.windowTitle())

        # ---Window Title Bar Customization (Optional) ---
        # FluentWindow allows adding widgets to the title bar
        # self.addTitleBarWidget(self.gamelist_combo, align=Qt.AlignmentFlag.AlignRight) # Example

    def _connect_signals(self):
        logger.debug("Connecting MainWindow signals...")
        try:
            # Connect Header Controls

            self.settings_button.clicked.connect(self._on_settings_clicked)
            self.gamelist_combo.currentIndexChanged.connect(
                self._on_gamelist_selection_changed
            )
            # Use checkedChanged for SwitchButton

            self.safe_mode_switch.checkedChanged.connect(self._on_safe_mode_toggled)
            # TODO: Connect preset_combo, refresh_button, play_button later

            # Connect ViewModel Signals
            self.vm.game_list_updated.connect(self._update_gamelist_dropdown)
            self.vm.current_game_changed.connect(self._select_game_in_dropdown)
            # Use setChecked for SwitchButton state updates

            self.vm.safe_mode_status_changed.connect(self.safe_mode_switch.setChecked)
            self.vm.errorOccurred.connect(self._on_error_occurred)
            # TODO: Connect preset signals later
            # self.vm.presets_list_updated.connect(self._update_preset_dropdown)

        except AttributeError as e:
            logger.error(f"Error connecting signals in MainWindow: {e}")

    def _on_settings_clicked(self):
        logger.info("Settings button clicked.")
        # TODO: Consider using FluentDialog or MessageDialog later
        try:
            settings_vm = self.vm.get_settings_vm()
            dialog = SettingsDialog(
                settings_vm, parent=self
            )  # Standard QDialog for now

            if dialog.exec():
                logger.info("Settings dialog accepted. Updating game list.")
                self.vm._sync_game_list()
            else:
                logger.info("Settings dialog cancelled.")
        except AttributeError:
            logger.error("Could not get config_service from MainWindowVM.")
            # All: Show Error via ui_utils.show_error

    def _update_gamelist_dropdown(self, games: list):
        """Updates the game list ComboBox."""
        logger.debug(f"Updating gamelist dropdown with {len(games)} games.")
        new_items = [game.name for game in games]
        current_items = [
            self.gamelist_combo.itemText(i) for i in range(self.gamelist_combo.count())
        ]

        if new_items == current_items:
            return  # Skip update if identical

        self.gamelist_combo.blockSignals(True)
        current_selection = self.gamelist_combo.currentText()  # Store current text

        self.gamelist_combo.clear()
        items = [game.name for game in games]

        if not items:
            self.gamelist_combo.setPlaceholderText("No games configured")
            self.gamelist_combo.setCurrentIndex(-1)  # Ensure no index is selected

            self.gamelist_combo.setEnabled(False)
        else:
            self.gamelist_combo.addItems(items)
            self.gamelist_combo.setEnabled(True)
            # Try to restore previous selection or select current game from VM

            current_game = self.vm.get_current_game()
            if current_game and current_game.name in items:
                self.gamelist_combo.setCurrentText(current_game.name)
            elif current_selection in items:
                self.gamelist_combo.setCurrentText(
                    current_selection
                )  # Restore if still valid

            else:
                self.gamelist_combo.setCurrentIndex(-1)  # Default to placeholder

                self.gamelist_combo.setPlaceholderText(
                    "Select Game"
                )  # Reset placeholder

        self.gamelist_combo.blockSignals(False)
        # Ensure the VM state is updated if the selection had to be cleared

        if (
            self.gamelist_combo.currentIndex() == -1
            and self.vm.get_current_game() is not None
        ):
            self.vm.select_game_by_name(None)  # Signal that no game is selected

    def _on_gamelist_selection_changed(self, index: int):
        """Handles game selection from the ComboBox."""
        if index >= 0:
            name = self.gamelist_combo.itemText(index)
            logger.debug(f"Game selected from dropdown: '{name}'")
            self.vm.select_game_by_name(name)
        else:
            logger.debug("Gamelist dropdown selection cleared.")
            self.vm.select_game_by_name(None)  # Notify VM that selection is cleared

    def _select_game_in_dropdown(self, game):
        """Programmatically selects a game in the ComboBox based on VM state."""
        self.gamelist_combo.blockSignals(True)

        if game:
            game_name = game.name  # ✅ FIXED: ambil nama
            index = self.gamelist_combo.findText(game_name)
            if index != -1:
                self.gamelist_combo.setCurrentIndex(index)
            else:
                logger.warning(f"Game '{game_name}' not found in ComboBox")
                self.gamelist_combo.setCurrentIndex(-1)
        else:
            self.gamelist_combo.setCurrentIndex(-1)

        self.gamelist_combo.blockSignals(False)

    def _on_safe_mode_toggled(self, checked: bool):
        """Handles toggling the Safe Mode SwitchButton."""
        logger.debug(f"Safe mode switch toggled via UI: {checked}")
        self.vm.set_safe_mode(checked)

    def _on_error_occurred(self, title: str, message: str):
        """Handles errors emitted by the ViewModel."""
        show_error(self, title, message)

    # TODO: Implement other slots (_on_preset_selection_changed, _on_refresh_clicked, _on_play_clicked)
    # TODO: Implement closeEvent if specific save actions are needed on exit
