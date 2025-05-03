from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QWidget,
    QLineEdit,
    QFileDialog,
)
from app.viewmodels.settings_vm import SettingsVM
from app.utils.logger_utils import logger


class SettingsDialog(QDialog):

    def __init__(self, view_model: SettingsVM, parent: QWidget | None = None):
        super().__init__(parent)
        self.vm = view_model
        self.setWindowTitle("Settings – Game List")
        self.setMinimumWidth(500)
        self._setup_ui()
        self._connect_signals()
        self.vm.load_settings()

    def _setup_ui(self) -> None:
        self.layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels(["Name", "Path"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.layout.addWidget(self.table)

        button_row = QHBoxLayout()

        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit")
        self.remove_button = QPushButton("Remove")
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")

        for btn in [
            self.add_button,
            self.edit_button,
            self.remove_button,
            self.save_button,
            self.cancel_button,
        ]:
            button_row.addWidget(btn)

        self.layout.addLayout(button_row)

    def _connect_signals(self) -> None:
        self.vm.game_list_changed.connect(self._populate_game_table)
        self.vm.save_finished.connect(self._handle_save_finished)

        self.add_button.clicked.connect(self._on_add_clicked)
        self.edit_button.clicked.connect(self._on_edit_clicked)
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.save_button.clicked.connect(self._on_save_clicked)
        self.cancel_button.clicked.connect(self.reject)

    def _populate_game_table(self) -> None:
        games = self.vm.get_editable_games()
        self.table.setRowCount(len(games))
        for i, game in enumerate(games):
            self.table.setItem(i, 0, QTableWidgetItem(game.name))
            self.table.setItem(i, 1, QTableWidgetItem(game.path))

    def _get_selected_index(self) -> int | None:
        selected = self.table.currentRow()
        return selected if selected >= 0 else None

    def _on_add_clicked(self) -> None:
        name, ok1 = self._prompt_text("Enter game name:")
        if not ok1 or not name:
            return
        path, ok2 = self._prompt_path()
        if not ok2 or not path:
            return

        if not self.vm.add_game(name, path):
            logger.warning("Failed to add game (possibly duplicate or invalid)")

    def _on_edit_clicked(self) -> None:
        idx = self._get_selected_index()
        if idx is None:
            return
        current = self.vm.get_editable_games()[idx]

        name, ok1 = self._prompt_text("Edit game name:", default=current.name)
        if not ok1 or not name:
            return
        path, ok2 = self._prompt_path(default=current.path)
        if not ok2 or not path:
            return

        if not self.vm.update_game(idx, name, path):
            logger.warning("Failed to update game (possibly duplicate)")

    def _on_remove_clicked(self) -> None:
        idx = self._get_selected_index()
        if idx is not None:
            self.vm.remove_game(idx)

    def _on_save_clicked(self) -> None:
        self.vm.save_changes()

    def _handle_save_finished(self, success: bool) -> None:
        if success:
            self.accept()
        else:
            logger.error("Failed to save games to config.")

    def _prompt_text(self, label: str, default: str = "") -> tuple[str, bool]:
        text_input = QLineEdit()
        text_input.setText(default)
        dlg = QDialog(self)
        dlg.setWindowTitle(label)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.addWidget(text_input)
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        dlg_layout.addLayout(btn_row)

        result = {"ok": False}

        def _accept():
            result["ok"] = True
            dlg.accept()

        def _reject():
            dlg.reject()

        ok_btn.clicked.connect(_accept)
        cancel_btn.clicked.connect(_reject)

        dlg.exec()
        return text_input.text().strip(), result["ok"]

    def _prompt_path(self, default: str = "") -> tuple[str, bool]:
        result = QFileDialog.getExistingDirectory(
            self, "Select Game Folder", default or ""
        )
        return result, bool(result)
