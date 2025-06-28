# app/views/dialogs/select_game_type_dialog.py

from typing import List
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import MessageBoxBase, SubtitleLabel, ComboBox, BodyLabel

class SelectGameTypeDialog(MessageBoxBase):
    """
    A custom dialog that prompts the user to select a game type from a list
    when it cannot be automatically detected.
    """

    def __init__(self, proposal_name: str, available_types: List[str], parent: QWidget | None = None):
        super().__init__(parent)

        # --- Create Widgets ---
        self.titleLabel = SubtitleLabel(f"Set Database Key for '{proposal_name}'", self)
        self.infoLabel = BodyLabel(
            "This game needs a 'Database Key (Type)' to link it to its metadata "
            "(e.g., for filters). Please select the correct one below.", self
        )
        self.infoLabel.setWordWrap(True)

        self.game_type_combo = ComboBox(self)
        self.game_type_combo.addItems(available_types)

        # --- Add Widgets to Layout ---
        # The viewLayout is provided by MessageBoxBase
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.infoLabel)
        self.viewLayout.addWidget(self.game_type_combo)

        # --- Configure Buttons ---
        self.yesButton.setText("Confirm")
        self.cancelButton.setText("Cancel")

        self.widget.setMinimumWidth(380)

    def selected_game_type(self) -> str:
        """Returns the game type selected by the user."""
        return self.game_type_combo.currentText()