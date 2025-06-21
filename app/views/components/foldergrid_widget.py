# App/views/components/foldergrid widget.py

from PyQt6.QtCore import pyqtSignal, QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import (
    CardWidget,
    BodyLabel,
    CaptionLabel,
    FluentIcon,
    IconWidget,
    IndeterminateProgressRing,
    RoundMenu,
    SwitchButton,
    FlowLayout,
    CheckBox,
    VBoxLayout,
)
from app.viewmodels.mod_list_vm import ModListViewModel


class FolderGridItemWidget(CardWidget):
    """
    A self-contained widget for a single item in the foldergrid. It can represent
    either a navigable folder or a final mod item.
    """

    # Custom signal to notify the main panel of a selection click

    item_selected = pyqtSignal(object)  # Emits the item model
    doubleClicked = pyqtSignal()  # Emits when the item is double-clicked
    status_toggled = pyqtSignal(bool)  # Emits the item model when status is toggled
    bulk_selection_changed = pyqtSignal(bool)
    paste_requested = pyqtSignal()

    def __init__(
        self,
        item_data: dict,
        viewmodel: ModListViewModel,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.item_data = item_data
        self.view_model = viewmodel

        self._card_width = 148
        self._image_height = 185
        self._thumb_size = QSize(self._card_width, self._image_height)

        self._init_ui()
        self._connect_signals()
        self.set_data(self.item_data)

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        self.setFixedSize(self._card_width, self._image_height + 86)

        # Revised: Using Vboxlayout from QFluentWidgets

        main_layout = VBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 8)
        main_layout.setSpacing(0)

        # ---1. Top Area: Image Container + Overlays ---
        image_container = QWidget(self)
        image_container.setFixedSize(self._thumb_size)

        self.thumbnail_label = CaptionLabel(image_container)
        self.thumbnail_label.setGeometry(
            0, 0, self._thumb_size.width(), self._thumb_size.height()
        )
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setObjectName("ThumbnailLabel")
        self.thumbnail_label.setStyleSheet(
            "#ThumbnailLabel { "
            "  background-color: rgba(255, 255, 255, 0.04); "
            "  border-top-left-radius: 8px; "
            "  border-top-right-radius: 8px; "
            "}"
        )

        self.processing_ring = IndeterminateProgressRing(image_container)
        self.processing_ring.setFixedSize(40, 40)
        ring_x = (self._thumb_size.width() - self.processing_ring.width()) // 2
        ring_y = (self._thumb_size.height() - self.processing_ring.height()) // 2
        self.processing_ring.move(ring_x, ring_y)
        self.processing_ring.hide()

        self.selection_checkbox = CheckBox(image_container)
        self.selection_checkbox.move(8, 8)
        self.selection_checkbox.hide()

        # ---2. Bottom Area: Info (Name and Status) ---

        info_area = QWidget(self)

        info_layout = VBoxLayout(info_area)
        info_layout.setContentsMargins(12, 8, 12, 0)
        info_layout.setSpacing(4)

        self.name_label = BodyLabel()
        self.name_label.setWordWrap(True)

        # ... (the remaining status layout has not changed)

        status_layout = FlowLayout(isTight=True)
        status_layout.setContentsMargins(0, 4, 0, 0)
        status_layout.setHorizontalSpacing(6)

        self.pin_icon = IconWidget(FluentIcon.PIN, self)
        self.pin_icon.setToolTip("Pinned")
        self.pin_icon.hide()

        self.status_switch = SwitchButton(self)
        self.status_switch.setOnText("Enabled")
        self.status_switch.setOffText("Disabled")
        self.status_switch.setToolTip("Toggle mod status")

        status_layout.addWidget(self.pin_icon)
        status_layout.addWidget(self.status_switch)

        info_layout.addWidget(self.name_label)
        info_layout.addLayout(status_layout)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        info_layout.addStretch(1)

        # ---Assemble Main Layout ---
        main_layout.addWidget(image_container)
        main_layout.addWidget(info_area, 1)

    def _connect_signals(self):
        """Connects internal UI widget signals to their handler methods."""
        # Connect user actions to methods that will call the ViewModel.
        self.status_switch.checkedChanged.connect(self._on_status_toggled)

    def set_data(self, item_data: dict):
        """Flow 2.3 & 3.1b: Updates the widget's display with new data."""
        self.item_data = item_data

        self.name_label.setText(self.item_data.get("actual_name", ""))
        self.pin_icon.setVisible(self.item_data.get("is_pinned", False))

        self.status_switch.blockSignals(True)
        is_enabled = self.item_data.get("is_enabled", False)
        self.status_switch.setChecked(is_enabled)
        self.status_switch.blockSignals(False)

        # ---Logic to show folder icon or mod thumbnail ---
        is_navigable = self.item_data.get("is_navigable")
        thumbnail_to_load = None
        default_icon_type = "mod"

        if is_navigable is None or is_navigable is True:
            default_icon_type = "folder"
        else:  # is_navigable is False, it's a final mod
            image_paths = self.item_data.get("preview_images", [])
            if image_paths:
                thumbnail_to_load = image_paths[0]

        # ---Revised Section for Thumbnail ---
        # Call the method of viewmodel, not direct service
        pixmap = self.view_model.get_thumbnail(
            item_id=self.item_data.get("id", ""),
            source_path=thumbnail_to_load,
            default_type=default_icon_type,
        )

        scaled_pixmap = pixmap.scaled(
            self._thumb_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.thumbnail_label.setPixmap(scaled_pixmap)

    def show_processing_state(self, is_processing: bool, text: str = "Processing..."):
        """Flow 3.1b, 4.2: Shows a visual indicator that the item is being processed."""
        # Disables controls and can show an overlay with text on the widget.
        self.setEnabled(not is_processing)
        if is_processing:
            self.processing_ring.show()
        else:
            self.processing_ring.hide()

    # ---Qt Event Handlers ---

    def contextMenuEvent(self, event):
        """Creates and shows a context menu on right-click."""
        menu = RoundMenu(parent=self)

        # Aksi di sini bisa berbeda, karena kita sudah punya SwitchButton
        # Tapi "Open in Explorer" sangat relevan
        open_folder_action = QAction(
            FluentIcon.FOLDER.icon(), "Open in File Explorer", self
        )
        open_folder_action.triggered.connect(
            lambda: self.view_model.open_in_explorer(self.item_data.get("id") or "")
        )
        menu.addAction(open_folder_action)

        menu.addSeparator()

        pin_action_text = "Unpin" if self.item_data.get("is_pinned") else "Pin"
        pin_action = QAction(FluentIcon.PIN.icon(), pin_action_text, self)
        menu.addAction(pin_action)

        rename_action = QAction(FluentIcon.EDIT.icon(), "Rename...", self)
        menu.addAction(rename_action)

        delete_action = QAction(FluentIcon.DELETE.icon(), "Delete", self)
        menu.addAction(delete_action)

        menu.exec(event.globalPos())

    def mousePressEvent(self, event):
        """Flow 5.2: Notifies the main view that this item was item_selected for preview."""
        # Do not emit if it's a navigation folder, as that's handled by double-click.

        if not self.item_data.get("is_navigable"):
            self.item_selected.emit(self.item_data)
        super().mousePressEvent(event)
        pass

    def mouseDoubleClickEvent(self, event):
        """Flow 2.3: Handles navigation into a subfolder."""
        if self.item_data.get("is_navigable"):
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)
        pass

    def showEvent(self, event):
        """Flow 2.3 Stage 2 Trigger: Triggers lazy-hydration when the widget becomes visible."""
        super().showEvent(event)
        # If the item is a skeleton, request its full data

        if self.item_data.get("is_skeleton", False):
            item_id = self.item_data.get("id")
            if item_id:
                self.view_model.request_item_hydration(item_id)

    # ---Private Slots (Handling UI events) ---

    def _on_status_toggled(self):
        """Flow 3.1b: Forwards the status toggle action to the ViewModel."""
        item_id = self.item_data.get("id")
        if item_id:
            self.view_model.toggle_item_status(item_id)

    def _on_selection_changed(self):
        """Flow 3.2: Forwards the selection change to the ViewModel."""
        # self.view_model.set_item_item_selected(
        #    self.item.id, self.selection_checkbox.isChecked()
        # )

        pass
