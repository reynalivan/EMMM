# App/views/sections/preview panel.py


# ---Imports ---
# Delete Qstackedwidget, Qpushbutton. Maintain the others.

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QTextEdit, QHBoxLayout
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize  # Import QSize

import os

# Import ViewModel

from app.viewmodels.preview_panel_vm import PreviewPanelVM

# ---Fluent Widget Import ---

from qfluentwidgets import (
    HorizontalFlipView,
    TitleLabel,
    BodyLabel,
    TextEdit,
)  # Use the fluent component if desired


# ---End Imports ---


from app.utils.logger_utils import logger  # Import logger


class PreviewPanel(QWidget):
    """Panel to display details and image previews of a selected folder item."""

    def __init__(
        self, view_model: PreviewPanelVM, parent: QWidget | None = None
    ):  # Make sure the VM hint type is correct

        super().__init__(parent)
        self.vm = view_model
        self._setup_ui()
        self._connect_signals()
        logger.debug("PreviewPanel initialized.")

    def _setup_ui(self):
        """Creates and arranges the UI widgets."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)  # Give a margin

        # Use Fluent Labels if desired
        self.title_label = TitleLabel("No Selection")
        self.title_label.pixelFontSize = 16
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # Status
        self.status_label = BodyLabel("")
        self.status_label.setObjectName("StatusPreviewLabel")
        layout.addWidget(self.status_label)

        layout.setSpacing(10)  # Give space between elements
        self.image_view = HorizontalFlipView(self)
        self.image_view.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.image_view.setMinimumHeight(100)
        self.image_view.setFixedHeight(300)
        self.image_view.setObjectName("PreviewFlipView")
        layout.addWidget(
            self.image_view, 1
        )  # Give a stretch factor so that it can enlarge

        # Description
        self.description_label = BodyLabel("Description:")
        self.description_view = TextEdit()
        self.description_view.setPlaceholderText("No description available.")
        layout.addWidget(self.description_label)
        layout.addWidget(self.description_view)

        # layout.addlayout (Btn_layout) # Add the Paste/Upload button layout later

    def _connect_signals(self):
        """Connects signals from the ViewModel to slots."""
        logger.debug("Connecting PreviewPanel signals...")
        try:
            self.vm.display_data_updated.connect(self._on_data_updated)
            self.vm.thumbnail_paths_updated.connect(self._on_thumbnails_updated)

            # TODO: Connect signals for status switch, description edit, paste/upload buttons later

        except AttributeError as e:
            logger.error(f"Error connecting signals in PreviewPanel: {e}")

    # ---Delete Definition _on_data_updated first/duplicate ---

    # Maintain this safer definition of _on_data_updated

    def _on_data_updated(self, data: dict):
        """Updates UI elements when ViewModel data changes."""
        if not data:
            self.title_label.setText("No Selection")
            self.status_label.setText("")
            self.description_view.setPlainText("")  # Use SetText for Textedit

            self.description_view.setPlaceholderText("No description available.")
            # Flipview also blank when no item was selected

            self.image_view.setCurrentIndex(-1)  # Reset index
            self.image_view.clear()  # Delete the previous image
            self.image_view.addImages([])
        else:
            self.title_label.setText(data.get("title", "N/A"))
            # Use all caps text according to other widgets

            self.status_label.setText(
                "ENABLED" if data.get("is_enabled") else "DISABLED"
            )
            self.description_view.setText(data.get("description", ""))

    def _on_thumbnails_updated(self, paths: list[str]):
        """Updates the HorizontalFlipView with new image paths."""
        logger.debug(f"PreviewPanel received {len(paths)} thumbnail paths.")
        # ---Start Modification: Use Addimages ---
        # Delete all old logic (clear_image_stack, loop, addwidget qlabel)

        self.image_view.setCurrentIndex(-1)  # Reset index before clear/add
        self.image_view.clear()  # Delete old images from flipview
        self.image_view.addImages([])

        if paths:
            valid_paths = [p for p in paths if isinstance(p, str) and os.path.exists(p)]
            if valid_paths:
                logger.debug(
                    f"Adding {len(valid_paths)} valid image paths to FlipView."
                )
                self.image_view.addImages(valid_paths)
                if self.image_view.count() > 0:
                    self.image_view.setCurrentIndex(0)  # Show the first image

            else:
                logger.warning(
                    "Received thumbnail paths list but no valid/existing paths found."
                )
                # Maybe displaying Placeholder on Flip View? Flip View may have your own placeholder.

        else:
            logger.debug("Received empty thumbnail paths list.")

    def update_status_only(self, is_enabled: bool):
        """Update only the status label."""
        if is_enabled:
            self.status_label.setText("ENABLED")
        else:
            self.status_label.setText("DISABLED")
