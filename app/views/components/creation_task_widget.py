# app/views/dialogs/components/creation_task_widget.py

import re
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QApplication
from qfluentwidgets import LineEdit, BodyLabel, ToolButton, FluentIcon

class CreationTaskWidget(QWidget):
    """A widget for a single item in the ConfirmationListDialog."""
    validation_changed = pyqtSignal()

    ILLEGAL_CHAR_PATTERN = re.compile(r'[\\/:*?"<>|]')

    def __init__(self, task_data: dict, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self._is_valid = True
        self.existing_names_lower: list[str] = []

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        self.warning_icon = ToolButton(FluentIcon.EXPRESSIVE_INPUT_ENTRY, self)
        self.warning_icon.setToolTip("This folder/archive does not contain any .ini files.")
        self.warning_icon.setVisible(task_data.get("has_ini_warning", False))

        source_label = BodyLabel(f"From: {task_data['source_path'].name}")
        source_label.setToolTip(str(task_data['source_path']))

        self.name_edit = LineEdit(self)
        self.name_edit.setText(task_data.get("proposed_name", ""))

        main_layout.addWidget(self.warning_icon)
        main_layout.addWidget(source_label, 1)
        main_layout.addWidget(self.name_edit, 2)

        self.name_edit.textChanged.connect(self.validate)

    def validate(self):
        """
        [REVISED] Validates the input name against illegal characters
        and the list of existing names.
        """
        name = self.name_edit.text().strip()
        is_currently_valid = True

        if not name or self.ILLEGAL_CHAR_PATTERN.search(name):
            is_currently_valid = False
            self.name_edit.setProperty('state', 'error')
        elif name.lower() in self.existing_names_lower:
            # Check for duplicates
            is_currently_valid = False
            self.name_edit.setProperty('state', 'error')
            self.name_edit.setToolTip("This name already exists in the destination folder.")
        else:
            is_currently_valid = True
            self.name_edit.setProperty('state', '')
            self.name_edit.setToolTip("")

        # Only emit the signal if the validity state has actually changed
        if self._is_valid != is_currently_valid:
            self._is_valid = is_currently_valid
            self.validation_changed.emit()

        self.name_edit.setStyle(QApplication.style())

    def set_existing_names(self, names: list[str]):
        """Receives the list of existing names from the parent dialog."""
        self.existing_names_lower = [name.lower() for name in names]
        self.validate() # Re-validate with the new list

    def is_valid(self) -> bool:
        return self._is_valid

    def get_task_data(self) -> dict:
        self.task_data['output_name'] = self.name_edit.text().strip()
        return self.task_data