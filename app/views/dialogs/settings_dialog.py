# App/views/dialogs/settings dialog.py

from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QStackedWidget,
    QTableWidgetItem,
    QFileDialog,
)

from qfluentwidgets import (
    Pivot,
    TableWidget,
    ListWidget,
    PrimaryPushButton,
    PushButton,
    FluentIcon,
    SubtitleLabel,
    Dialog,
)
from app.utils.ui_utils import UiUtils
from app.utils.logger_utils import logger
from app.viewmodels.settings_vm import SettingsViewModel


class SettingsDialog(QDialog):  # Inherit from fluent Dialog
    """
    The main dialog for managing settings. It operates transactionally,
    only committing changes when the user explicitly saves.
    """

    def __init__(self, viewmodel: SettingsViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = viewmodel

        self._init_ui()
        self._connect_signals()  # To be implemented later

        self._refresh_all_lists()  # To be implemented later

    def _init_ui(self):
        """Initializes the UI components of the dialog."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 500)

        # REVISED: Create one main layout and apply it directly to the dialog

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(15, 15, 15, 15)
        dialog_layout.setSpacing(10)

        # ---Pivot for Tab Navigation ---

        self.pivot = Pivot(self)

        # ---Stacked Widget for Tab Content ---

        self.stack = QStackedWidget(self)

        # ---Create and Add Tab Contents ---
        # Call these methods FIRST to populate the pivot and stack

        self._create_games_tab()
        self._create_presets_tab()

        # Set initial tab AFTER items have been added

        self.pivot.setCurrentItem("games_tab")

        # ---Assemble Layout ---

        dialog_layout.addWidget(self.pivot)
        dialog_layout.addWidget(
            self.stack, 1
        )  # The '1' makes the stack take available space

        # ---Bottom Buttons (Save/Cancel) ---

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)  # Push buttons to the right

        self.cancel_button = PushButton("Cancel")
        self.save_button = PrimaryPushButton("Save")
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        dialog_layout.addLayout(button_layout)

    def _create_games_tab(self):
        """Creates the UI for the 'Games' management tab."""
        games_widget = QWidget()
        layout = QVBoxLayout(games_widget)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(SubtitleLabel("Manage Mods Paths"))

        toolbar_layout = QHBoxLayout()
        self.remove_game_button = PushButton(FluentIcon.DELETE, "Remove Selected")
        self.edit_game_button = PushButton(FluentIcon.EDIT, "Edit Selected")
        self.add_game_button = PushButton(FluentIcon.ADD, "Add Game")
        toolbar_layout.addWidget(self.remove_game_button)
        toolbar_layout.addWidget(self.edit_game_button)
        toolbar_layout.addWidget(self.add_game_button)
        toolbar_layout.addStretch(1)

        # Table to display games

        self.games_table = TableWidget(self)
        self.games_table.setColumnCount(2)
        self.games_table.setHorizontalHeaderLabels(["Game Name", "Mods Path"])

        # ---REVISED SECTION: Apply fluent styles ---

        self.games_table.setBorderVisible(True)
        self.games_table.setBorderRadius(8)
        self.games_table.setSelectRightClickedRow(True)  # Good UX for context menus
        # ---END REVISED SECTION ---

        vertical_header = self.games_table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
        self.games_table.setWordWrap(False)
        self.games_table.setAlternatingRowColors(True)
        header = self.games_table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)

        layout.addLayout(toolbar_layout)
        layout.addWidget(self.games_table, 1)

        self.stack.addWidget(games_widget)
        self.pivot.addItem(
            routeKey="games_tab",
            text="Games",
            onClick=lambda: self.stack.setCurrentWidget(games_widget),
            icon=FluentIcon.GAME,
        )

    def _create_presets_tab(self):
        """Creates the UI for the 'Presets' management tab."""
        # This part of your code is also good

        presets_widget = QWidget()
        layout = QVBoxLayout(presets_widget)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        toolbar_layout = QHBoxLayout()
        self.rename_preset_button = PushButton(FluentIcon.EDIT, "Rename Selected")
        self.delete_preset_button = PushButton(FluentIcon.DELETE, "Delete Selected")
        toolbar_layout.addWidget(self.rename_preset_button)
        toolbar_layout.addWidget(self.delete_preset_button)
        toolbar_layout.addStretch(1)

        self.presets_list = ListWidget(self)
        self.presets_list.setObjectName("PresetsList")

        layout.addWidget(SubtitleLabel("Manage Saved Presets"))
        layout.addLayout(toolbar_layout)
        layout.addWidget(self.presets_list, 1)

        self.stack.addWidget(presets_widget)
        self.pivot.addItem(
            routeKey="presets_tab",
            text="Presets",
            onClick=lambda: self.stack.setCurrentWidget(presets_widget),
            icon=FluentIcon.SAVE,
        )

    def _connect_signals(self):
        """Connects UI element signals and ViewModel signals to their handlers."""
        # ---ViewModel -> View ---

        self.view_model.games_list_refreshed.connect(self._refresh_game_list)
        self.view_model.toast_requested.connect(self._on_toast_requested)
        self.view_model.confirmation_requested.connect(self._on_confirmation_requested)
        self.view_model.error_dialog_requested.connect(self._on_error_dialog_requested)

        # ---View -> ViewModel ---

        self.add_game_button.clicked.connect(self._on_add_game)
        # self.edit_game_button.clicked.connect(self._on_edit_game)
        # self.remove_game_button.clicked.connect(self._on_remove_game)
        # self.rename_preset_button.clicked.connect(self._on_rename_preset)
        # self.delete_preset_button.clicked.connect(self._on_delete_preset)

        # Connect Save and Cancel buttons
        self.save_button.clicked.connect(self._on_save)
        self.cancel_button.clicked.connect(self.reject)

        # ---Connect ViewModel signals to dialog slots ---
        # self.view_model.long_operation_started.connect(self._on_long_op_started)
        # self.view_model.long_operation_finished.connect(self._on_long_op_finished)

        pass

    def _on_confirmation_requested(self, params: dict):
        """Membuat dan menampilkan dialog konfirmasi fluent."""
        title = params.get("title", "Confirmation")
        text = params.get("text", "")
        context = params.get("context", {})

        # Using dialogue from QFluentwidgets as in your reference
        if UiUtils.show_confirm_dialog(self, title, text, "Yes", "No"):
            # Users press "yes" or "ok"
            self.view_model.on_confirmation_result(True, context)
        else:
            # The user presses "no", "cancel", or closes dialogue
            self.view_model.on_confirmation_result(False, context)

    def _on_toast_requested(self, message: str, level: str):
        """Creates a non-blocking InfoBar notification inside the dialog."""
        # Call Master's Functions from Uiutils

        UiUtils.show_toast(
            parent=self,  # Toast will appear above this dialogue
            message=message,
            level=level,
        )

    # ---UI Refresh Methods ---

    def _refresh_all_lists(self):
        """A helper to refresh all lists in the dialog from the ViewModel's temp state."""
        view_data = [
            {"id": g.id, "name": g.name, "path": str(g.path)}
            for g in self.view_model.temp_games
        ]
        self._refresh_game_list(view_data)

    def _refresh_game_list(self, games_data: list[dict]):
        """Populates the game list view from the ViewModel's pre-formatted data."""
        logger.debug(f"Refreshing game list with {len(games_data)} items.")
        self.games_table.setRowCount(0)
        self.games_table.setRowCount(len(games_data))

        for row, game_dict in enumerate(games_data):
            # Use dictionary keys instead of object attributes

            name_item = QTableWidgetItem(game_dict["name"])
            path_item = QTableWidgetItem(game_dict["path"])

            # Store the game ID in the first item for easy retrieval

            name_item.setData(Qt.ItemDataRole.UserRole, game_dict["id"])
            self.games_table.setItem(row, 0, name_item)
            self.games_table.setItem(row, 1, path_item)

        # Resize path column to fit content

        self.games_table.resizeColumnToContents(1)

    def _refresh_preset_list(self):
        """Populates the preset list view from the ViewModel's temp_presets."""
        pass

    # ---SLOTS (Responding to ViewModel Signals) ---

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

    # ---UI EVENT HANDLERS (Calling ViewModel methods) ---

    def _on_add_game(self):
        """Flow 1.2: Membuka dialog folder dan meneruskannya ke ViewModel."""
        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Select Game's Mods Folder",
        )
        if selected_path:
            self.view_model.add_game_from_path(Path(selected_path))

    # ... (sisa class)

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

    def _on_error_dialog_requested(self, title: str, message: str):
        """Shows a modal error dialog."""
        dialog = Dialog(title, message, self)
        dialog.exec()
