# App/views/components/foldergrid widget.py

from PyQt6.QtCore import QSignalBlocker, pyqtSignal, QSize, Qt
from PyQt6.QtGui import QAction, QMouseEvent
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
    themeColor,
)
from app.utils.logger_utils import logger
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

        self._is_selected = False

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

        # --- Update basic UI elements ---
        self.name_label.setText(self.item_data.get("actual_name", "N/A"))
        self.pin_icon.setVisible(self.item_data.get("is_pinned", False))

        with QSignalBlocker(self.status_switch):
            is_enabled = self.item_data.get("is_enabled", False)
            self.status_switch.setChecked(is_enabled)

        # --- Logic to determine icon/thumbnail based on navigability ---
        is_navigable = item_data.get("is_navigable")
        source_path_to_load = None
        default_icon_key = ""

        if is_navigable is True:
            # It's a confirmed navigable folder. Use the folder icon.
            default_icon_key = "folder"
            # Double-clicking should navigate into it.
            self.setMouseTracking(True)
        elif is_navigable is False:
            # It's a confirmed final mod. Try to find its thumbnail.
            default_icon_key = "mod_placeholder"  # Fallback if no image is found
            preview_images = item_data.get("preview_images", [])
            if preview_images:
                source_path_to_load = preview_images[0]
            # Double-clicking should not navigate.
            self.setMouseTracking(False)
        else:  # is_navigable is None (still a skeleton)
            # Assume it's a folder until proven otherwise by hydration.
            default_icon_key = "folder"
            self.setMouseTracking(True)

        # --- Call ViewModel to get the final pixmap ---
        # The ViewModel will delegate this to the ThumbnailService
        pixmap = self.view_model.get_thumbnail(
            item_id=self.item_data.get("id", ""),
            source_path=source_path_to_load,
            default_type=default_icon_key,
        )

        # --- Scale and set the pixmap ---
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                self._thumb_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumbnail_label.setPixmap(scaled_pixmap)
        else:
            # Handle case where even the default pixmap failed to load
            self.thumbnail_label.setText("?")  # Or clear it

    def set_selected(self, is_selected: bool):
        """
        Sets the visual state of the widget to selected or unselected.
        """
        # Avoid redundant stylesheet changes if the state is already correct
        if self._is_selected == is_selected:
            return

        self._is_selected = is_selected

        if is_selected:
            # Apply a border using the application's current theme color
            border_color = themeColor().name()
            self.setStyleSheet(
                f"""
                CardWidget {{
                    border-top: 4px solid {border_color};
                    background: rgba(255, 255, 255, 0.08);
                }}
            """
            )
        else:
            # Revert to the default stylesheet (or a default border)
            self.setStyleSheet("")

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

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """
        Handles the double-click event to enable folder navigation.
        """
        # Only emit the signal if the item is explicitly marked as navigable
        if self.item_data.get("is_navigable") is True:
            logger.debug(
                f"Navigable item '{self.item_data.get('actual_name')}' double-clicked. Calling load_items."
            )

            path_to_load = self.item_data.get("folder_path")
            if not path_to_load:
                logger.error("Double-clicked item has no folder_path.")
                return

            # Directly call the method on the ViewModel it already holds
            self.view_model.load_items(
                path=path_to_load,
                game=self.view_model.current_game,
                is_new_root=False,
            )
            event.accept()
        else:
            # If not navigable, just pass the event to the parent class
            logger.debug(
                f"Item {self.item_data.get('id')} double-clicked but not navigable."
            )
            super().mouseDoubleClickEvent(event)

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
