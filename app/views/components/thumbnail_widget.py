# app/views/components/thumbnail_widget.py

from pathlib import Path
from typing import Dict, List

from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import (
    QAction,
    QContextMenuEvent,
    QDragEnterEvent,
    QDropEvent,
    QMouseEvent,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QMenu,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QSizePolicy,
)

from qfluentwidgets import (
    HorizontalFlipView,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    RoundMenu,
    ToolButton,
    FluentIcon,
    CaptionLabel,
    ProgressRing,
    SubtitleLabel,
    TransparentPushButton,
    VBoxLayout,
)

from app.viewmodels.preview_panel_vm import PreviewPanelViewModel  # Adjusted import
from app.core.constants import SUPPORTED_IMAGE_EXTENSIONS


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
        self.stack = QStackedWidget(self)

        # --- 1. Main View with FlipView and Controls ---
        # (This part remains the same)
        self.main_content_widget = QWidget()
        content_layout = QVBoxLayout(self.main_content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        self.flip_view = HorizontalFlipView(self)
        self.flip_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.flip_view.setObjectName("thumbnailSlider")
        self.flip_view.setFixedWidth(240)
        self.flip_view.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        control_bar_layout = QHBoxLayout()
        control_bar_layout.setContentsMargins(5, 0, 5, 0)
        control_bar_layout.setSpacing(5)
        self.index_label = CaptionLabel("0 / 0")
        self.add_button = ToolButton(FluentIcon.ADD, self)
        self.add_button.setToolTip("Add image from file...")
        self.paste_button = ToolButton(FluentIcon.PASTE, self)
        self.paste_button.setToolTip("Paste image from clipboard")
        self.remove_button = ToolButton(FluentIcon.DELETE, self)
        self.remove_button.setToolTip("Remove current image")
        self.clear_all_button = ToolButton(FluentIcon.REMOVE, self)
        self.clear_all_button.setToolTip("Remove all images")
        self.loading_ring = ProgressRing(self)
        self.loading_ring.setFixedSize(16, 16)
        self.loading_ring.setVisible(False)
        control_bar_layout.addWidget(self.index_label, 0, Qt.AlignmentFlag.AlignLeft)
        control_bar_layout.addStretch(1)
        control_bar_layout.addWidget(self.loading_ring)
        control_bar_layout.addWidget(self.add_button)
        control_bar_layout.addWidget(self.paste_button)
        control_bar_layout.addWidget(self.remove_button)
        control_bar_layout.addWidget(self.clear_all_button)
        content_layout.addWidget(self.flip_view, 1)
        content_layout.addLayout(control_bar_layout)

        # --- 2. Null State View (New and Improved) ---
        self.null_state_widget = QWidget(self)
        null_layout = VBoxLayout(self.null_state_widget)
        null_layout.setSpacing(10)
        null_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info_label = SubtitleLabel("No Preview Images")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: grey;")

        # Horizontal layout for the small action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.null_add_button = TransparentPushButton(
            FluentIcon.ADD, "Add from File...", self
        )
        self.null_paste_button = TransparentPushButton(FluentIcon.PASTE, "Paste", self)

        button_layout.addStretch(1)
        button_layout.addWidget(self.null_add_button)
        button_layout.addWidget(self.null_paste_button)
        button_layout.addStretch(1)

        null_layout.addStretch(1)
        null_layout.addWidget(info_label)
        null_layout.addLayout(button_layout)
        null_layout.addStretch(1)

        # --- Assemble Stack ---
        self.stack.addWidget(self.main_content_widget)
        self.stack.addWidget(self.null_state_widget)  # Use the new widget
        main_layout.addWidget(self.stack)
        self.stack.setCurrentWidget(
            self.null_state_widget
        )  # Default to the new null state

    def _connect_signals(self):
        # View -> VM (Existing connections are correct)
        self.flip_view.currentIndexChanged.connect(self._update_index_label)
        self.add_button.clicked.connect(self._on_add_button_clicked)
        self.paste_button.clicked.connect(self._on_paste_button_clicked)
        self.remove_button.clicked.connect(self._on_remove_button_clicked)
        self.clear_all_button.clicked.connect(self._on_clear_all_button_clicked)

        # --- FIX: Connect the new buttons in the null state view ---
        self.null_add_button.clicked.connect(self._on_add_button_clicked)
        self.null_paste_button.clicked.connect(self._on_paste_button_clicked)

        # VM -> View (This connection is correct)
        self.view_model.thumbnail_operation_in_progress.connect(
            self._on_loading_state_changed
        )

    def set_image_paths(self, image_paths: list[Path]):
        """Receives a list of image paths and displays them in the FlipView."""
        # 1. Update the internal data model first. This is our source of truth.
        self._image_paths = image_paths or []

        # 2. Use the documented .clear() method to reset the view widget.
        self.flip_view.clear()
        self.flip_view.setCurrentIndex(0)  # Reset to the first index

        # 3. Check the state and switch between the null view and the content view.
        if not self._image_paths:
            self.stack.setCurrentWidget(self.null_state_widget)
            self._update_index_label()  # Ensure label resets to "0 / 0"
            return

        self.stack.setCurrentWidget(self.main_content_widget)

        # 4. Use the documented .addImages() method to populate the view from scratch.
        self.flip_view.addImages([str(p) for p in self._image_paths])

        # 5. Explicitly set the index to 0 to ensure it always starts on the first slide.
        # This fixes the bug where a new image appears on the second slide.
        if self.flip_view.count() > 0:  # .count() is a valid QListWidget method
            self.flip_view.setCurrentIndex(0)

        # 6. Update the 'X / Y' label based on the new, correct state.
        self._update_index_label()

    def _update_index_label(self):
        """Memperbarui label '1 / 5'."""
        total = len(self._image_paths)
        current = self.flip_view.currentIndex() + 1 if total > 0 else 0
        self.index_label.setText(f"{current} / {total}")

    # --- Drag & Drop Events ---

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accepts the drag event if it contains valid image files."""
        mime_data = event.mimeData()
        if mime_data is not None and mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(
                    SUPPORTED_IMAGE_EXTENSIONS
                ):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handles dropped files and forwards them to the ViewModel."""
        mime_data = event.mimeData()
        urls = []
        if mime_data is not None and mime_data.hasUrls():
            urls = [
                url
                for url in mime_data.urls()
                if url.isLocalFile()
                and url.toLocalFile().lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)
            ]

        for url in urls:
            try:
                with open(url.toLocalFile(), "rb") as f:
                    image_data = f.read()
                self.view_model.add_new_thumbnail(image_data)
            except IOError as e:
                InfoBar.error(
                    "File Error",
                    f"Could not read dropped file: {e}",
                    parent=self.window(),
                    position=InfoBarPosition.TOP_RIGHT,
                )
        event.acceptProposedAction()

    # --- Context Menu Event ---
    def contextMenuEvent(self, event: QContextMenuEvent):
        """Creates and shows a fluent context menu on right-click over the flip view."""
        # Use RoundMenu for a fluent look and feel
        menu = RoundMenu(parent=self)

        # --- Add/Paste Actions ---
        add_action = QAction(FluentIcon.ADD.icon(), "Add Image...", self)
        add_action.triggered.connect(self._on_add_button_clicked)
        menu.addAction(add_action)

        paste_action = QAction(FluentIcon.PASTE.icon(), "Paste from Clipboard", self)
        paste_action.triggered.connect(self._on_paste_button_clicked)
        menu.addAction(paste_action)

        # Only add deletion options if there are images to delete
        if self._image_paths:
            menu.addSeparator()

            # --- Deletion Actions ---
            # Corrected: using .icon() to get the QIcon object
            remove_action = QAction(FluentIcon.DELETE.icon(), "Remove This Image", self)
            remove_action.triggered.connect(self._on_remove_button_clicked)
            menu.addAction(remove_action)

            clear_all_action = QAction(
                FluentIcon.REMOVE.icon(), "Clear All Images", self
            )
            clear_all_action.triggered.connect(self._on_clear_all_button_clicked)
            menu.addAction(clear_all_action)

        # Use the exec method from RoundMenu, with animation enabled
        menu.exec(event.globalPos(), ani=True)

    def _on_thumbnail_ready(self, image_id: str, pixmap: QPixmap):
        pass

    def _on_add_button_clicked(self):
        """Handles the add image button click by opening a file dialog."""
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Preview Images",
            "",
            f"Image Files ({' '.join(['*' + ext for ext in SUPPORTED_IMAGE_EXTENSIONS])})",
        )

        if not file_names:
            return

        for file_name in file_names:
            try:
                with open(file_name, "rb") as f:
                    image_data = f.read()
                self.view_model.add_new_thumbnail(image_data)
            except IOError as e:
                InfoBar.error(
                    "File Error",
                    f"Could not read image file: {e}",
                    parent=self.window(),
                    position=InfoBarPosition.TOP_RIGHT,
                )

    def _on_paste_button_clicked(self):
        """Handles pasting an image from the clipboard."""
        self.view_model.paste_thumbnail_from_clipboard()

    def _on_remove_button_clicked(self):
        """Handles removing the currently displayed image."""
        if not self._image_paths:
            return

        current_index = self.flip_view.currentIndex()
        if 0 <= current_index < len(self._image_paths):
            path_to_remove = self._image_paths[current_index]

            reply = MessageBox(
                "Confirm Deletion",
                f"Are you sure you want to remove this image?\n({path_to_remove.name})",
                self.window(),
            )
            if reply.exec():
                self.view_model.remove_thumbnail(path_to_remove)

    def _on_clear_all_button_clicked(self):
        """Handles removing all images."""
        if not self._image_paths:
            return

        reply = MessageBox(
            "Confirm Clear All",
            "Are you sure you want to remove ALL preview images for this mod?",
            self.window(),
        )
        reply.yesButton.setText("Yes, Clear All")
        reply.cancelButton.setText("Cancel")
        if reply.exec():
            self.view_model.remove_all_thumbnails()

    def _on_loading_state_changed(self, is_loading: bool):
        """Shows/hides the loading ring and disables/enables controls."""
        self.loading_ring.setVisible(is_loading)
        self.add_button.setEnabled(not is_loading)
        self.paste_button.setEnabled(not is_loading)
        self.remove_button.setEnabled(not is_loading)
        self.clear_all_button.setEnabled(not is_loading)

    def _on_small_thumbnail_selected(self, image_path: Path):
        pass
