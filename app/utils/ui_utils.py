# app/utils/ui_utils.py
# Utility functions for common UI dialogs.

from typing import Optional, Tuple
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QWidget

def show_info(parent: Optional[QWidget], title: str, message: str) -> None:
    """Displays a standard information message box."""
    # Implementation Note: Use QMessageBox.information(parent, title, message)
    pass # Skeleton implementation

def show_warning(parent: Optional[QWidget], title: str, message: str) -> None:
    """Displays a standard warning message box."""
     # Implementation Note: Use QMessageBox.warning(parent, title, message)
    pass # Skeleton implementation

def show_error(parent: Optional[QWidget], title: str, message: str) -> None:
    """Displays a standard error message box."""
    QMessageBox.critical(parent, title, message)

def confirm_yes_no(parent: Optional[QWidget],
                     title: str,
                     message: str,
                     default_button=QMessageBox.StandardButton.No
                     ) -> bool:
    """
    Displays a Yes/No confirmation dialog using QMessageBox.question.

    Args:
        parent: Parent widget.
        title: Dialog title.
        message: Confirmation message/question.
        default_button: Which button is focused by default (No or Yes).

    Returns:
        True if Yes was clicked, False otherwise (No or dialog closed).
    """
    reply = QMessageBox.question(parent,
                                 title,
                                 message,
                                 buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 defaultButton=default_button)
    return reply == QMessageBox.StandardButton.Yes

def get_text_input(parent: Optional[QWidget],
                   title: str,
                   label: str,
                   default_text: str = ""
                   ) -> Tuple[Optional[str], bool]:
    """
    Gets text input from the user via a dialog.
    (Skeleton - Implementation deferred)
    """
    # TODO: Implement if needed later
    pass # Skeleton implementation
    # Placeholder return
    return None, False