# app/views/components/folder_grid_item_widget.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtGui import QPixmap, QPainter, QEnterEvent  # Import event handlers
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRect, QEvent
from app.models.folder_item_model import FolderItemModel  # Pastikan path import benar
from app.core import constants

# --- Fluent Widget Imports ---
from qfluentwidgets import (
    BodyLabel, CaptionLabel, SwitchButton, CheckBox, ToolButton, FluentIcon,
    CardWidget)  # Gunakan CardWidget sebagai dasar? Atau style QWidget
# --- End Fluent Widget Imports ---

from app.utils.logger_utils import logger  # Import logger


class FolderGridItemWidget(
        CardWidget
):  # Inherit CardWidget for card style? Or QWidget + manual style
    """ Custom widget representing a single folder/mod item in a grid view. """

    # --- Signals ---
    status_toggled = pyqtSignal(bool)
    bulk_selection_changed = pyqtSignal(bool)
    paste_requested = pyqtSignal()
    doubleClicked = pyqtSignal()

    # --- End Signals ---

    def __init__(self, model: FolderItemModel, parent: QWidget | None = None):
        super().__init__(parent)  # Initialize CardWidget or QWidget
        self.item_model = model

        # Define approximate dimensions based on visual guess (can be adjusted)
        self._card_width = 180
        self._image_height = 130  # Height for the image area
        self._info_padding = 8  # Padding for the info area
        self._info_base_height_estimate = 76
        self._info_height = self._info_base_height_estimate + (
            self._info_padding * 2)
        self._card_height = self._image_height + self._info_height

        # Size for the internal thumbnail label to scale image into
        self._thumb_size = QSize(self._card_width, self._image_height)

        self._setup_ui()
        self._update_ui_from_model()
        self._connect_signals()

        self.setObjectName(
            f"FolderGridItemCard_{model.folder_name}")  # Unique object name
        self.setFixedSize(self._card_width,
                          self._card_height)  # Grid items often have fixed size

        # Enable mouse tracking for hover events if not default for CardWidget
        self.setMouseTracking(True)

    def _setup_ui(self):
        """Creates and arranges the UI widgets."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Top Area (Image Container + Overlays)
        # Container to hold image label and overlays
        self.image_area_container = QWidget(self)
        self.image_area_container.setFixedSize(self._card_width,
                                               self._image_height)
        self.image_area_container.setObjectName("ImageAreaContainer")
        # Enable mouse tracking on container too if needed for paste button visibility
        self.image_area_container.setMouseTracking(True)
        # Style: Set background color for placeholder state, potentially remove border
        self.image_area_container.setStyleSheet("""
            #ImageAreaContainer {
                background-color: transparent; /* Let thumbnail label handle bg */
                border-top-left-radius: 8px; /* Match CardWidget radius */
                border-top-right-radius: 8px;
            }
        """)

        # Thumbnail Label (child of container, fills it)
        self.thumbnail_label = QLabel(self.image_area_container)
        self.thumbnail_label.setGeometry(0, 0, self._card_width,
                                         self._image_height)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setObjectName("ThumbnailLabel")
        # Style: Rounded top corners to match container, handle placeholder style
        self.thumbnail_label.setStyleSheet(
            "background-color: rgba(0,0,0,0.06); border-top-left-radius: 8px; border-top-right-radius: 8px;"
        )

        # Checkbox Overlay (Top-Left) - Child of container
        self.bulk_checkbox = CheckBox(self.image_area_container)
        self.bulk_checkbox.setObjectName("BulkCheckboxOverlay")
        self.bulk_checkbox.setFixedSize(20, 20)  # Make it smaller
        self.bulk_checkbox.move(6, 6)  # Position near top-left corner
        # Make checkbox background slightly transparent for visibility? Optional.
        # self.bulk_checkbox.setStyleSheet("background-color: rgba(255, 255, 255, 0.7); border-radius: 3px;")

        # Paste Button Overlay (Bottom-Right) - Child of container
        # Using ToolButton with an icon
        self.paste_button = ToolButton(FluentIcon.PASTE,
                                       self.image_area_container)
        self.paste_button.setObjectName("PasteButtonOverlay")
        button_size = 26  # Smaller button
        self.paste_button.setFixedSize(button_size, button_size)
        padding = 6
        paste_x = self._card_width - button_size - padding
        paste_y = self._image_height - button_size - padding
        self.paste_button.move(paste_x, paste_y)
        self.paste_button.setToolTip("Paste thumbnail from clipboard")
        self.paste_button.setVisible(False)  # Initially hidden

        # 2. Bottom Area (Info)
        # Container for padding and background
        self.info_area = QWidget(self)
        self.info_area.setObjectName("InfoArea")
        self.info_area.setFixedHeight(self._info_height)
        # Style: Background, padding, rounded bottom corners
        self.info_area.setStyleSheet(f"""
            #InfoArea {{
                background-color: transparent; /* Let CardWidget handle main bg */
                border-bottom-left-radius: 8px; /* Match CardWidget radius */
                border-bottom-right-radius: 8px;
                padding: {self._info_padding}px;
            }}
        """)
        info_layout = QVBoxLayout(self.info_area)
        info_layout.setContentsMargins(2, 2, 2,
                                       2)  # Padding is handled by stylesheet
        info_layout.setSpacing(1)  # Very tight spacing

        # Use BodyLabel, allow multiple lines if needed
        self.name_label = BodyLabel()
        self.name_label.setObjectName("NameLabel")
        self.name_label.setWordWrap(True)
        self.name_label.setContentsMargins(12, 8, 12, 0)

        # Status line (Switch + Text)
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(12, 4, 12, 12)
        status_layout.setSpacing(4)  # Tight spacing

        self.status_switch = SwitchButton()
        self.status_switch.setToolTip("Toggle Mod Enabled/Disabled status")
        self.status_switch.setEnabled(True)  # Make interactive
        self.status_switch.setOnText("Enabled")
        self.status_switch.setOffText("Disabled")

        status_layout.addWidget(self.status_switch)
        status_layout.addStretch(1)  # Push left

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(status_widget)
        # info_layout.addStretch(1) # Add stretch if content needs to be pushed up

        # Assemble Main Layout (Image Area + Info Area)
        self.main_layout.addWidget(self.image_area_container)
        self.main_layout.addWidget(self.info_area)

    def _update_ui_from_model(self):
        """Populates the widgets with data from the item model."""
        self.name_label.setText(self.item_model.display_name)
        self.status_switch.blockSignals(True)
        self.status_switch.setChecked(self.item_model.status)
        self.status_switch.blockSignals(False)
        self.bulk_checkbox.blockSignals(True)
        self.bulk_checkbox.setChecked(False)  # Default to unchecked
        self.bulk_checkbox.blockSignals(False)
        self.set_placeholder_thumbnail()
        display_name = self.item_model.display_name
        self.name_label.setText(display_name)
        self.name_label.setToolTip(display_name)

    def _connect_signals(self):
        """Connects signals from internal widgets."""
        self.status_switch.checkedChanged.connect(self._on_status_changed)
        self.bulk_checkbox.stateChanged.connect(self._on_bulk_checked_changed)
        self.paste_button.clicked.connect(self.paste_requested)

    # --- Event Handlers for Hover ---
    def enterEvent(self, event: QEnterEvent):
        """Show paste button on hover."""
        self.paste_button.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        """Hide paste button when not hovering."""
        self.paste_button.setVisible(False)
        super().leaveEvent(event)

    # --- Slots ---
    def _on_status_changed(self, checked: bool):
        """Handles internal switch change."""
        self.status_toggled.emit(checked)  # Emit signal for VM

    def _on_bulk_checked_changed(self, state: int):
        """Handles internal checkbox change."""
        is_checked = (state == Qt.CheckState.Checked.value)
        self.bulk_selection_changed.emit(is_checked)  # Emit signal for VM

    # --- Public Methods ---
    def get_item_model(self) -> FolderItemModel:
        """Returns the data model associated with this widget."""
        return self.item_model

    def set_thumbnail(self, pixmap: QPixmap | None):
        """Sets the thumbnail image (called externally)."""
        if pixmap and not pixmap.isNull():
            # Scale pixmap to fit the image area
            scaled_pixmap = pixmap.scaled(
                self._thumb_size,  # Target size is the label size
                Qt.AspectRatioMode.KeepAspectRatio,  # Maintain aspect ratio
                Qt.TransformationMode.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled_pixmap)
            self.thumbnail_label.setText("")
            # Clear background, keep border radius for image label
            self.thumbnail_label.setStyleSheet(
                "#ThumbnailLabel { background-color: transparent; border-top-left-radius: 8px; border-top-right-radius: 8px; }"
            )
        else:
            self.set_placeholder_thumbnail()

    def set_placeholder_thumbnail(self):
        """Sets the thumbnail label to a default placeholder state."""
        self.thumbnail_label.clear()  # Clear any previous pixmap

        # TODO: Use FluentIcon.PHOTO or FOLDER here. Requires drawing the icon.
        # Simplest is text or empty background for now.
        self.thumbnail_label.setText("")
        # Set placeholder style on the label
        self.thumbnail_label.setStyleSheet("""
            #ThumbnailLabel {
                background-color: rgba(0, 0, 0, 0.06); /* Placeholder background */
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid rgba(0, 0, 0, 0.08); /* Optional border */
                /* Add icon via QSS background-image: url(...) later */
            }
            """)

    def mouseDoubleClickEvent(self, event: QEvent):
        """Emit doubleClicked signal on left mouse button double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            logger.debug(
                f"Item '{self.item_model.display_name}': Double-click detected, emitting signal."
            )  # Tambahkan log ini
            self.doubleClicked.emit()  # <-- Pastikan sinyal dipancarkan
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
