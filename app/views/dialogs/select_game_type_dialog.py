# app/views/dialogs/select_game_type_dialog.py

from typing import List
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
from qfluentwidgets import SubtitleLabel, ComboBox, BodyLabel, PrimaryPushButton, PushButton

class SelectGameTypeDialog(QDialog):
    """
    [REVISED] A custom QDialog that prompts the user to select a game type.
    This version inherits from QDialog for maximum compatibility.
    """

    def __init__(self, proposal_name: str, available_types: List[str], parent: QWidget | None = None):
        super().__init__(parent)

        # --- Dialog Setup ---
        self.setWindowTitle("Select Database Key")
        self.setFixedWidth(400)

        # --- 1. Create Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # --- 2. Create Widgets ---
        titleLabel = SubtitleLabel(f"Set Database Key for '{proposal_name}'", self)
        infoLabel = BodyLabel(
            "This game needs a 'Database Key (Type)' to link it to its metadata. "
            "Please select the correct one below.", self
        )
        infoLabel.setWordWrap(True)

        self.game_type_combo = ComboBox(self)
        if available_types:
            self.game_type_combo.addItems(available_types)
        else:
            self.game_type_combo.setPlaceholderText("No types found in database")
            self.game_type_combo.setEnabled(False)

        # --- 3. Create Button Layout ---
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        confirm_button = PrimaryPushButton("Confirm")
        cancel_button = PushButton("Cancel")
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)

        # --- 4. Add Widgets to Main Layout ---
        main_layout.addWidget(titleLabel)
        main_layout.addWidget(infoLabel)
        main_layout.addWidget(self.game_type_combo)
        main_layout.addStretch(1)
        main_layout.addLayout(button_layout)

        # --- 5. Connections ---
        confirm_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        # Disable confirm button if there are no types to select
        if not available_types:
            confirm_button.setEnabled(False)


    def selected_game_type(self) -> str:
        """Returns the game type selected by the user."""
        return self.game_type_combo.currentText()