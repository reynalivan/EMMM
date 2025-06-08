# app/views/main_window.py
from PyQt6.QtWidgets import QWidget, QSplitter
from qfluentwidgets import FluentWindow, InfoBar, InfoBarPosition
from app.viewmodels.main_window_vm import MainWindowViewModel
from app.viewmodels.settings_vm import SettingsViewModel

# Import ViewModels, Services, and other View components
# ...


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
        # This method remains the same: it creates the widgets.
        # It now also passes the child VMs to the panel constructors.
        # Uncomment and initialize the panels as needed:
        # self.object_list_panel = ObjectListPanel(viewmodel=self.main_window_vm.objectlist_vm)
        # self.folder_grid_panel = FolderGridPanel(viewmodel=self.main_window_vm.foldergrid_vm)
        # self.preview_panel = PreviewPanel(viewmodel=self.main_window_vm.preview_panel_vm)
        # For now, create a placeholder if ObjectListPanel is not implemented:
        self.object_list_panel = QWidget(
            self
        )  # Replace QWidget with ObjectListPanel when available
        pass

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
