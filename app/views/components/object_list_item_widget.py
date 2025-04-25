# app/views/components/object_list_item_widget.py

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from app.models.object_item_model import ObjectItemModel
from app.core import constants

# --- Fluent Widget Imports ---
# Ganti SubtitleLabel menjadi BodyLabel
from qfluentwidgets import BodyLabel, CaptionLabel, SwitchButton, CheckBox
# --- End Fluent Widget Imports ---


class ObjectListItemWidget(QWidget):
    """ Custom widget representing a single item in the ObjectListPanel. """
    status_toggled = pyqtSignal(bool)
    bulk_selection_changed = pyqtSignal(bool)

    def __init__(self, model: ObjectItemModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.item_model = model
        # Ukuran thumbnail diambil dari konstanta
        self._thumb_size = QSize(constants.OBJECT_THUMB_SIZE_W,
                                 constants.OBJECT_THUMB_SIZE_H)

        self._setup_ui()
        self._update_ui_from_model()
        self._connect_signals()
        self.setObjectName("ObjectListItem")
        # Styling dasar (bisa disesuaikan lebih lanjut)
        self.setStyleSheet(
            "#ObjectListItem { background-color: rgba(243, 243, 243, 0.7); border-radius: 6px; padding: 5px; }"
        )

    def _setup_ui(self):
        """Creates and arranges the UI widgets."""
        # Main Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(6)

        # 1. Thumbnail Label (Ukuran sudah dari konstanta)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(
            self._thumb_size)  # Set fixed size from constants
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setObjectName("ThumbnailLabel")

        # 2. Center Area (Name + Status)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        #center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)  # Rapatkan Name dan Status line

        # --- START MODIFICATION: Gunakan BodyLabel ---
        self.name_label = BodyLabel()  # Ganti dari SubtitleLabel ke BodyLabel
        self.name_label.setObjectName("NameLabel")
        # --- END MODIFICATION ---

        # Status line (Switch + Text)
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        # --- START MODIFICATION: Kurangi spasi status ---
        status_layout.setSpacing(4)  # Rapatkan SwitchButton dan CaptionLabel
        # --- END MODIFICATION ---

        self.status_switch = SwitchButton()
        self.status_switch.setOnText("Enabled")
        self.status_switch.setOffText("Disabled")
        self.status_switch.setToolTip("Toggle Mod Enabled/Disabled status")
        self.status_switch.setEnabled(True)

        self.status_label = CaptionLabel()  # Tetap CaptionLabel (paling kecil)
        self.status_label.setObjectName("StatusLabel")

        status_layout.addWidget(self.status_switch)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch(1)  # Tetap rata kiri

        center_layout.addWidget(self.name_label)
        center_layout.addWidget(status_widget)

        # 3. Bulk Selection Checkbox (Right)
        self.bulk_checkbox = CheckBox()
        self.bulk_checkbox.setToolTip("Select for batch operations")

        # Assemble Main Layout
        self.main_layout.addWidget(
            self.thumbnail_label, 0,
            Qt.AlignmentFlag.AlignTop)  # Align thumbnail top
        # --- START MODIFICATION: Alignment & Stretch ---
        # Tambahkan center_widget tanpa stretch horizontal, align top
        self.main_layout.addWidget(center_widget, 0, Qt.AlignmentFlag.AlignTop)
        self.main_layout.addStretch(1)  # Stretch setelah center content
        # Align checkbox vertically center
        self.main_layout.addWidget(self.bulk_checkbox, 0,
                                   Qt.AlignmentFlag.AlignCenter)
        # --- END MODIFICATION ---

    def _update_ui_from_model(self):
        """Populates the widgets with data from the item model."""
        self.name_label.setText(self.item_model.display_name)
        self.status_switch.blockSignals(True)
        self.status_switch.setChecked(self.item_model.status)
        self.status_switch.blockSignals(False)

        self.set_placeholder_thumbnail()

    def _connect_signals(self):
        """Connects signals from internal widgets to slots or emits."""
        self.status_switch.checkedChanged.connect(self._on_status_changed)
        self.bulk_checkbox.stateChanged.connect(self._on_bulk_checked_changed)

    # --- Slots ---
    def _on_status_changed(self, checked: bool):
        """Handles the status switch change and emits signal."""
        self.status_toggled.emit(checked)  # Emit the custom signal

    def _on_bulk_checked_changed(self, state: int):
        """Handles the bulk checkbox state change and emits signal."""
        is_checked = (state == Qt.CheckState.Checked.value)
        self.bulk_selection_changed.emit(is_checked)

    # --- Public Methods ---
    def get_item_model(self) -> ObjectItemModel:
        """Returns the data model associated with this widget."""
        return self.item_model

    def set_thumbnail(self, pixmap: QPixmap | None):
        """Sets the thumbnail image (called externally)."""
        if pixmap and not pixmap.isNull():
            # Scaling uses self._thumb_size which comes from constants
            scaled_pixmap = pixmap.scaled(
                self._thumb_size, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled_pixmap)
            self.thumbnail_label.setText("")
            self.thumbnail_label.setStyleSheet(
                "#ThumbnailLabel { background-color: transparent; border-radius: 4px; }"
            )
        else:
            self.set_placeholder_thumbnail()

    def set_placeholder_thumbnail(self):
        """Sets the thumbnail label to a default placeholder state."""
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("")
        # Styling placeholder (contoh tema terang)
        self.thumbnail_label.setStyleSheet("""
            #ThumbnailLabel {
                background-color: rgba(0, 0, 0, 0.04);
                color: rgba(0, 0, 0, 0.5);
                border-radius: 4px;
                border: 1px solid rgba(0, 0, 0, 0.07);
                /* TODO: Placeholder icon */
            }
            """)
