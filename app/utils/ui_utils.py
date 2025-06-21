# app/utils/ui_utils.py
from PyQt6.QtWidgets import QWidget, QFrame, QMessageBox

from qfluentwidgets import InfoBar, InfoBarPosition, Dialog


class UiUtils:
    """A collection of static utility functions and custom widgets for the UI."""

    @staticmethod
    def create_confirmation_dialog(
        parent: QWidget, title: str, text: str, informative_text: str = ""
    ) -> bool:
        """Creates a standardized confirmation dialog (e.g., for deletes or overwrites)."""
        # Returns True if the user clicks the affirmative button (Yes/OK), otherwise False.
        return True  # Placeholder for actual dialog logic

    # ADD THIS NEW STATIC METHOD
    @staticmethod
    def show_confirm_dialog(
        parent: QWidget, title: str, content: str, yes_text: str, no_text: str
    ) -> bool:
        """
        Creates and shows a fluent confirmation dialog with Yes/No buttons.

        Parameters
        ----------
        parent : QWidget
            The parent widget for the dialog.
        title : str
            The title of the dialog window.
        content : str
            The main message/question for the user.

        Returns
        -------
        bool
            True if the user clicked Yes/OK, False otherwise.
        """
        dialog = Dialog(title, content, parent)
        dialog.yesButton.setText(yes_text or "Confirm")
        dialog.cancelButton.setText(no_text or "Cancel")

        # Tombol Yes/OK akan membuat exec() mengembalikan True
        # Tombol No/Cancel/menutup window akan membuat exec() mengembalikan False
        if dialog.exec():
            return True
        else:
            return False

    @staticmethod
    def show_toast(
        parent: QWidget,
        message: str,
        level: str = "info",
        title: str | None = None,
        duration: int = 3000,
        position: InfoBarPosition = InfoBarPosition.TOP_RIGHT,
    ):
        """
        Creates and shows a non-blocking InfoBar (toast) notification.

        Parameters
        ----------
        parent : QWidget
            The widget over which the toast will be displayed.
        message : str
            The main content of the notification.
        level : str, optional
            The severity level ('info', 'success', 'warning', 'error'), by default 'info'.
        title : str | None, optional
            The title of the notification. If None, a default is used, by default None.
        duration : int, optional
            How long the toast stays visible in milliseconds, by default 3000.
        position : InfoBarPosition, optional
            Where the toast appears on the parent widget, by default InfoBarPosition.TOP_RIGHT.
        """
        # Use a default title based on the level if none is provided
        final_title = title if title is not None else level.capitalize()

        # Adjust duration for more critical messages
        final_duration = duration
        if level.lower() in ["error", "warning"]:
            final_duration = 5000

        # Create the InfoBar using the appropriate static method based on the level
        if level.lower() == "success":
            InfoBar.success(
                final_title,
                message,
                duration=final_duration,
                position=position,
                parent=parent,
            )
        elif level.lower() == "warning":
            InfoBar.warning(
                final_title,
                message,
                duration=final_duration,
                position=position,
                parent=parent,
            )
        elif level.lower() == "error":
            InfoBar.error(
                final_title,
                message,
                duration=final_duration,
                position=position,
                parent=parent,
            )
        else:  # 'info'
            InfoBar.info(
                final_title,
                message,
                duration=final_duration,
                position=position,
                parent=parent,
            )


class ShimmerFrame(QFrame):
    """A reusable overlay widget that provides a shimmering loading animation."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # --- UI and Animation objects would be initialized here ---
        self.hide()  # Initially hidden

    def start_shimmer(self):
        """Makes the widget visible and starts the animation loop."""
        self.show()
        # self.animation.start()
        pass

    def stop_shimmer(self):
        """Stops the animation and hides the widget."""
        # self.animation.stop()
        self.hide()
        pass
