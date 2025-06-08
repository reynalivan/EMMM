# app/views/components/objectlist_widget.py
from PyQt6.QtCore import pyqtSignal, QSize, Qt
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon,
    IconWidget,
    CheckBox,
    IndeterminateProgressRing,
    FlowLayout,
    VBoxLayout,
)

# Import models and services for type hinting
from app.models.mod_item_model import ObjectItem
from app.services.thumbnail_service import ThumbnailService
from app.viewmodels.mod_list_vm import ModListViewModel


class ObjectListItemWidget(QWidget):
    """
    A self-contained widget to display a single ObjectItem. It forwards all
    user interactions to the ViewModel and updates its display based on the item model.
    """

    # Custom signal to notify the parent panel of a selection click.
    item_selected = pyqtSignal(object)  # Emits the item model

    def __init__(
        self,
        item: ObjectItem,
        viewmodel: ModListViewModel,
        thumbnail_service: ThumbnailService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.item = item
        self.view_model = viewmodel
        self.thumbnail_service = thumbnail_service
        self._thumb_size = QSize(64, 64)

        self._init_ui()
        self._connect_signals()
        self.set_data(item)

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        self.setObjectName("ObjectListItem")

        # --- Main Layout ---
        # Use FlowLayout for responsive wrapping if the panel is very narrow
        main_layout = FlowLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setHorizontalSpacing(12)
        main_layout.setVerticalSpacing(8)

        # --- 1. Left Side: Thumbnail, Checkbox, and Loading Ring ---
        # Container to layer multiple widgets on top of each other
        thumbnail_container = QWidget(self)
        thumbnail_container.setFixedSize(self._thumb_size)

        # The base image. Use standard QLabel as it's the best for QPixmap
        self.thumbnail_label = CaptionLabel(thumbnail_container)
        self.thumbnail_label.setFixedSize(self._thumb_size)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Loading Ring, centered on the container.
        self.processing_ring = IndeterminateProgressRing(thumbnail_container)
        self.processing_ring.setFixedSize(32, 32)  # Smaller ring
        ring_x = (self._thumb_size.width() - self.processing_ring.width()) // 2
        ring_y = (self._thumb_size.height() - self.processing_ring.height()) // 2
        self.processing_ring.move(ring_x, ring_y)
        self.processing_ring.hide()  # Initially hidden

        # Checkbox overlay
        self.selection_checkbox = CheckBox(thumbnail_container)
        self.selection_checkbox.setToolTip("Select for bulk operations")
        self.selection_checkbox.move(4, 4)
        self.selection_checkbox.hide()

        main_layout.addWidget(thumbnail_container)

        # --- 2. Center: Info Block (Name and Status) ---
        # We use a container QWidget to host a VBoxLayout inside the FlowLayout
        info_widget = QWidget(self)
        info_layout = VBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        self.name_label = BodyLabel()  # Fluent component for standard text
        self.name_label.setObjectName("NameLabel")
        info_layout.addWidget(self.name_label)

        # Status Layout (Icon + Text)
        status_widget = QWidget(self)
        status_layout = FlowLayout(
            status_widget, isTight=True
        )  # isTight=True reduces margins
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setHorizontalSpacing(6)

        self.status_icon = IconWidget(self)  # Fluent component for icons
        self.status_icon.setFixedSize(16, 16)

        self.status_text = CaptionLabel(self)  # Fluent component for small text
        self.status_text.setObjectName("StatusTextLabel")

        status_layout.addWidget(self.status_icon)
        status_layout.addWidget(self.status_text)

        info_layout.addWidget(status_widget)
        main_layout.addWidget(info_widget)

        # --- 3. Right Side: Pin Indicator ---
        self.pin_icon = IconWidget(FluentIcon.PIN, self)  # Fluent component
        self.pin_icon.setToolTip("Pinned")
        self.pin_icon.hide()  # Initially hidden
        main_layout.addWidget(self.pin_icon)

    def _connect_signals(self):
        """Connects internal UI widget signals to their handler methods."""
        # Connect user actions to methods that will call the ViewModel.
        # self.status_switch.toggled.connect(self._on_status_toggled)
        # self.selection_checkbox.stateChanged.connect(self._on_selection_changed)
        pass

    def set_data(self, item: ObjectItem):
        """Flow 2.2, 3.1a, 4.2.A: Updates the widget's display with new data."""
        self.item = item
        # Update UI elements: name_label, status_switch state, etc.
        # Request thumbnail update
        # pixmap = self.thumbnail_service.get_thumbnail(item.id, item.thumbnail_path, 'object')
        # self.thumbnail_label.setPixmap(pixmap)
        pass

    def show_processing_state(self, is_processing: bool, text: str = "Processing..."):
        """Flow 3.1a, 4.2: Shows a visual indicator that the item is being processed."""
        # Disables controls and can show an overlay with text on the widget.
        pass

    # --- Qt Event Handlers ---

    def contextMenuEvent(self, event):
        """Flow 4.2, 4.3, 6.3: Creates and shows a context menu on right-click."""
        # Create a menu with actions that connect directly to ViewModel methods.
        # e.g., rename_action.triggered.connect(lambda: self.view_model.rename_item(self.item.id))
        pass

    def mousePressEvent(self, event):
        """Flow 2.3: Notifies the parent panel that this item was clicked."""
        # This signal will be caught by ObjectListPanel, which then orchestrates
        # the call to the main view model to set the active object.
        self.item_selected.emit(self.item)
        super().mousePressEvent(event)
        pass

    def showEvent(self, event):
        """Flow 2.2: Triggers lazy-hydration when the widget becomes visible."""
        # if self.item.is_skeleton:
        #    self.view_model.request_item_hydration(self.item.id)
        super().showEvent(event)
        pass

    # --- Private Slots (Handling UI events) ---

    def _on_status_toggled(self):
        """Flow 3.1a: Forwards the status toggle action to the ViewModel."""
        self.view_model.toggle_item_status(self.item.id)
        pass

    def _on_selection_changed(self):
        """Flow 3.2: Forwards the selection change to the ViewModel."""
        # self.view_model.set_item_selected(
        #    self.item.id, self.selection_checkbox.isChecked()
        # )
        pass
