# app/views/dialogs/settings_dialog.py
from PyQt6.QtWidgets import QDialog, QWidget
from app.viewmodels.settings_vm import SettingsViewModel

# Import all necessary UI components (e.g., QListView, PushButton, etc.)
# ...


class SettingsDialog(QDialog):
    """
    The main dialog for managing settings. It operates transactionally,
    only committing changes when the user explicitly saves.
    """

    def __init__(self, viewmodel: SettingsViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = viewmodel

        self._init_ui()
        self._connect_signals()
        self._refresh_all_lists()

    def _init_ui(self):
        """Initializes the UI components of the dialog."""
        # Create tabs for "Games" and "Presets".
        # Create QListViews for games and presets.
        # Create buttons: "Add Game", "Edit Game", "Remove Game".
        # Create buttons: "Rename Preset", "Delete Preset".
        # Create main buttons: "Save" and "Cancel".
        pass

    def _connect_signals(self):
        """Connects UI element signals and ViewModel signals to their handlers."""
        # --- Connect UI actions to handler methods ---
        # self.add_game_button.clicked.connect(self._on_add_game)
        # self.edit_game_button.clicked.connect(self._on_edit_game)
        # self.remove_game_button.clicked.connect(self._on_remove_game)
        # self.rename_preset_button.clicked.connect(self._on_rename_preset)
        # self.delete_preset_button.clicked.connect(self._on_delete_preset)

        # self.save_button.clicked.connect(self._on_save)
        # self.cancel_button.clicked.connect(self.reject)

        # --- Connect ViewModel signals to dialog slots ---
        # self.view_model.long_operation_started.connect(self._on_long_op_started)
        # self.view_model.long_operation_finished.connect(self._on_long_op_finished)
        pass

    # --- UI Refresh Methods ---
    def _refresh_all_lists(self):
        """A helper to refresh all lists in the dialog from the ViewModel's temp state."""
        # self._refresh_game_list()
        # self._refresh_preset_list()
        pass

    def _refresh_game_list(self):
        """Populates the game list view from the ViewModel's temp_games."""
        pass

    def _refresh_preset_list(self):
        """Populates the preset list view from the ViewModel's temp_presets."""
        pass

    # --- SLOTS (Responding to ViewModel Signals) ---
    def _on_long_op_started(self, message: str):
        """Flow 6.2.A: Shows a progress overlay when a preset is being managed."""
        # Shows an overlay on the dialog to prevent interaction during preset rename/delete.
        pass

    def _on_long_op_finished(self, result: dict):
        """Flow 6.2.A: Hides the overlay and refreshes lists after a preset operation."""
        # Hides the overlay.
        # Refreshes the preset list to show the changes.
        # If there were failures, shows a message box with the details from the result dict.
        pass

    # --- UI EVENT HANDLERS (Calling ViewModel methods) ---

    def _on_add_game(self):
        """Flow 1.2: Opens a folder dialog and tells the ViewModel to process the path."""
        # 1. Open QFileDialog.
        # 2. If a path is selected, call self.view_model.add_game_from_path(path).
        # 3. Call self._refresh_game_list() to show the newly added temp game.
        pass

    def _on_edit_game(self):
        """Flow 1.2: Opens an edit dialog for the selected game."""
        # 1. Get the selected game from the list view.
        # 2. Open a small dialog to get a new name/path.
        # 3. If saved, call self.view_model.update_temp_game(...) and refresh the list.
        pass

    def _on_remove_game(self):
        """Flow 1.2: Tells the ViewModel to remove the selected game from the temp list."""
        # 1. Get the selected game.
        # 2. Call self.view_model.remove_temp_game(...) and refresh the list.
        pass

    def _on_rename_preset(self):
        """Flow 6.2.A: Opens a dialog to get a new name for a selected preset."""
        # 1. Get the selected preset.
        # 2. Open an input dialog to get the new name (with validation).
        # 3. Call self.view_model.rename_preset(old_name, new_name).
        pass

    def _on_delete_preset(self):
        """Flow 6.2.A: Confirms and tells the ViewModel to delete the selected preset."""
        # 1. Get the selected preset.
        # 2. Show a confirmation dialog.
        # 3. If confirmed, call self.view_model.delete_preset(preset_name).
        pass

    def _on_save(self):
        """Flow 1.2: Tells the ViewModel to commit all changes and closes the dialog on success."""
        if self.view_model.save_all_changes():
            self.accept()
        # If it returns False (due to a validation error), the dialog remains open.
        pass
