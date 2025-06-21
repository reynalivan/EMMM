# app/views/components/thumbnail_widget.py

from pathlib import Path
from typing import Dict, List

from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QSizePolicy,
)

from qfluentwidgets import (
    HorizontalFlipView,  # Core component for image sliding
    ToolButton,
    FluentIcon,
    CaptionLabel,
    SubtitleLabel,
)

from app.services.thumbnail_service import ThumbnailService
from app.viewmodels.preview_panel_vm import PreviewPanelViewModel  # Adjusted import


class ThumbnailSliderWidget(QWidget):
    """
    A complex widget that displays an interactive image slider using HorizontalFlipView,
    along with controls for managing images.
    """

    def __init__(
        self,
        viewmodel: PreviewPanelViewModel,  # Use specific ViewModel for better type hinting
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.view_model = viewmodel
        self._image_paths: List[Path] = []

        # Enable drag & drop for image files
        self.setAcceptDrops(True)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Use a QStackedWidget to switch between the slider and an empty state message
        self.stack = QStackedWidget(self)

        # --- 1. Main View with FlipView and Controls ---
        self.main_content_widget = QWidget()
        content_layout = QVBoxLayout(self.main_content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        # The image slider
        self.flip_view = HorizontalFlipView(self)
        self.flip_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        # set image object fit to ensure images are resized properly
        self.flip_view.setObjectName("thumbnailSlider")
        self.flip_view.setFixedWidth(240)
        self.flip_view.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.index_label = CaptionLabel("0 / 0")
        # Control bar for actions
        control_bar_layout = QHBoxLayout()
        control_bar_layout.setContentsMargins(5, 0, 5, 0)
        control_bar_layout.setSpacing(5)
        control_bar_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.add_button = ToolButton(FluentIcon.ADD, self)
        self.add_button.setToolTip("Add image from file...")

        self.paste_button = ToolButton(FluentIcon.PASTE, self)
        self.paste_button.setToolTip("Paste image from clipboard")

        self.remove_button = ToolButton(FluentIcon.DELETE, self)
        self.remove_button.setToolTip("Remove current image")

        self.clear_all_button = ToolButton(FluentIcon.REMOVE, self)
        self.clear_all_button.setToolTip("Remove all images")

        control_bar_layout.addWidget(self.add_button)
        control_bar_layout.addWidget(self.paste_button)
        control_bar_layout.addWidget(self.remove_button)
        control_bar_layout.addWidget(self.clear_all_button)

        content_layout.addWidget(self.flip_view, 1)
        content_layout.addWidget(self.index_label)
        content_layout.addLayout(control_bar_layout)

        # --- 2. Empty State View ---
        self.empty_label = SubtitleLabel(
            "No preview images.\nDrag images here or use the buttons below.", self
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: grey;")

        # --- Assemble Stack ---
        self.stack.addWidget(self.main_content_widget)
        self.stack.addWidget(self.empty_label)

        main_layout.addWidget(self.stack)

        # Start on the empty state page
        self.stack.setCurrentWidget(self.empty_label)

    # --- Methods to be implemented later ---

    def _connect_signals(self):
        self.flip_view.currentIndexChanged.connect(self._update_index_label)

    def set_image_paths(self, image_paths: list[Path]):
        """Menerima daftar path gambar dan menampilkannya di FlipView."""
        self._image_paths = image_paths or []

        # Hapus gambar lama sebelum menambahkan yang baru
        self.flip_view.clear()

        if not self._image_paths:
            self.stack.setCurrentWidget(self.empty_label)
            return

        self.stack.setCurrentWidget(self.main_content_widget)

        # Tambahkan gambar-gambar baru ke FlipView
        self.flip_view.addImages([str(p) for p in self._image_paths])
        self._update_index_label()

    def _update_index_label(self):
        """Memperbarui label '1 / 5'."""
        total = len(self._image_paths)
        current = self.flip_view.currentIndex() + 1 if total > 0 else 0
        self.index_label.setText(f"{current} / {total}")

    def dropEvent(self, event):
        pass

    def _on_thumbnail_ready(self, image_id: str, pixmap: QPixmap):
        pass

    def _on_add_button_clicked(self):
        pass

    def _on_small_thumbnail_selected(self, image_path: Path):
        pass
