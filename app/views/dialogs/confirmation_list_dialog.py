# app/views/dialogs/confirmation_list_dialog.py

from typing import List, Dict
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidgetItem
from qfluentwidgets import ListWidget, PrimaryPushButton, PushButton, SubtitleLabel, BodyLabel, ToolButton, FluentIcon
from app.views.components.creation_task_widget import CreationTaskWidget

class ConfirmationListDialog(QDialog):
    """
    A dialog to show a list of proposed mod creation tasks, allowing the user
    to edit names and confirm before starting the main process.
    """

    def __init__(self, tasks: List[dict], existing_names: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Mod Creation")
        self.setMinimumWidth(500)

        self.task_widgets: List[CreationTaskWidget] = []

        # --- UI Components ---
        title = SubtitleLabel("Review and Confirm", self)
        info = BodyLabel("The following mods will be created. You can edit the output folder names below.", self)

        self.list_widget = ListWidget(self)
        for task in tasks:
            list_item = QListWidgetItem(self.list_widget)
            widget = CreationTaskWidget(task)
            widget.set_existing_names(existing_names)
            widget.validation_changed.connect(self._on_validation_changed)

            list_item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)
            self.task_widgets.append(widget)

        self.start_button = PrimaryPushButton("Start Process")
        cancel_button = PushButton("Cancel")

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.start_button)

        main_layout.addWidget(title)
        main_layout.addWidget(info)
        main_layout.addWidget(self.list_widget, 1)
        main_layout.addLayout(button_layout)

        # --- Connections ---
        self.start_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        # Initial validation check
        self._on_validation_changed()

    def _on_validation_changed(self):
        """Checks if all task names are valid and enables/disables the start button."""
        all_valid = all(widget.is_valid() for widget in self.task_widgets)
        self.start_button.setEnabled(all_valid)

    def get_final_tasks(self) -> List[dict]:
        """Returns the list of tasks with user-edited names."""
        return [widget.get_task_data() for widget in self.task_widgets]