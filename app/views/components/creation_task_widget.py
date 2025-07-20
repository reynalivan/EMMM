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
        # This is a simplified validation. A more robust one would check for duplicates.
        name = self.name_edit.text().strip()
        if not name or self.ILLEGAL_CHAR_PATTERN.search(name):
            self._is_valid = False
            self.name_edit.setProperty('state', 'error') # Visual feedback
        else:
            self._is_valid = True
            self.name_edit.setProperty('state', '')

        self.name_edit.setStyle(QApplication.style())
        self.validation_changed.emit()

    def is_valid(self) -> bool:
        return self._is_valid

    def get_task_data(self) -> dict:
        self.task_data['output_name'] = self.name_edit.text().strip()
        return self.task_data