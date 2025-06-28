# App/views/components/objectlist widget.py

from PyQt6.QtCore import pyqtSignal, QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QSizePolicy, QWidget, QHBoxLayout
from qfluentwidgets import (
    StrongBodyLabel,
    CaptionLabel,
    FluentIcon,
    IconWidget,
    CheckBox,
    IndeterminateProgressRing,
    FlowLayout,
    VBoxLayout,
    AvatarWidget,
    RoundMenu,
)

# Import models and services for type hinting

from app.viewmodels.mod_list_vm import ModListViewModel
from app.utils.logger_utils import logger


class ObjectListItemWidget(QWidget):
    """
    A self-contained widget to display a single ObjectItem. It forwards all
    user interactions to the ViewModel and updates its display based on the item model.
    """

    # Custom signal to notify the parent panel of a selection click.

    item_selected = pyqtSignal(object)  # Emits the item model

    def __init__(
        self,
        item_data: dict,
        viewmodel: ModListViewModel,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.item_data = item_data
        self.view_model = viewmodel
        self._is_hovering = False

        self._init_ui()
        self._connect_signals()
        self.set_data(self.item_data)

    def _init_ui(self):
        """Initializes the UI components of the widget with Fluent components."""
        self.setObjectName("ObjectListItem")
        # ---Main Layout: Use Fluent Flowlayout ---

        main_layout = QHBoxLayout(self)
        # main_layout = FlowLayout(self)

        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # ---1. Thumbnail as Avatar ---

        self.avatar = AvatarWidget(self)
        self.avatar.setRadius(34)
        self.avatar.setFixedSize(QSize(76, 76))

        # Checkbox is made as a child of Avatar for overlay

        self.selection_checkbox = CheckBox(self.avatar)
        self.selection_checkbox.setFixedSize(20, 20)
        self.selection_checkbox.move(
            2, 2
        )  # Position in the upper left corner of Avatar

        self.selection_checkbox.hide()  # Hide by default

        # Added Processing Ring as Overlay in Avatar

        self.processing_ring = IndeterminateProgressRing(self.avatar)
        self.processing_ring.setFixedSize(32, 32)
        ring_x = (self.avatar.width() - self.processing_ring.width()) // 2
        ring_y = (self.avatar.height() - self.processing_ring.height()) // 2
        self.processing_ring.move(ring_x, ring_y)
        self.processing_ring.hide()

        main_layout.addWidget(self.avatar)

        # ---2. Info Block (Name + Passive Label Status) ---

        info_widget = QWidget(self)
        info_layout = VBoxLayout(info_widget)
        info_layout.setContentsMargins(4, 0, 0, 0)
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.name_label = StrongBodyLabel()
        self.name_label.setObjectName("NameLabel")
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(42)
        info_layout.addWidget(self.name_label)

        self.status_text = CaptionLabel()
        self.status_text.setObjectName("StatusTextLabel")
        info_layout.addWidget(self.status_text)
        main_layout.addWidget(info_widget)

        # ---3. Spacer to push the icon pin to the right ---
        # Revised: Use Qwidget with expanding policy as a spacer

        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        main_layout.addWidget(spacer)

        # ---4. Pin Icon ---

        self.pin_icon = IconWidget(FluentIcon.PIN, self)
        self.pin_icon.setToolTip("Pinned")
        self.pin_icon.hide()
        main_layout.addWidget(self.pin_icon)

    def _connect_signals(self):
        """Connects internal UI widget signals to their handler methods."""
        # Connect user actions to methods that will call the ViewModel.
        # self.status_switch.toggled.connect(self._on_status_toggled)

        self.selection_checkbox.stateChanged.connect(self._on_selection_changed)
        self.selection_checkbox.stateChanged.connect(self._update_checkbox_visibility)
        pass

    def set_data(self, item_data: dict):
        """Updates the widget's display with new data from a dictionary."""
        self.item_data = item_data
        actual_name = self.item_data.get("actual_name", "")
        self.name_label.setText(actual_name)

        is_enabled = self.item_data.get("is_enabled")
        self.status_text.setText("Enabled" if is_enabled else "Disabled")
        self.pin_icon.setVisible(self.item_data.get("is_pinned", False))

        id_data = self.item_data.get("id") or ""
        thumbnail_path = self.item_data.get("thumbnail_path")

        if not thumbnail_path or not id_data:
            # get initial from actual_name

            self.avatar.setText(self.view_model.get_initial_name(actual_name))
            return None

        thumbnail_pixmap = self.view_model.get_thumbnail(
            item_id=id_data,
            source_path=thumbnail_path,
            default_type="object",
        )
        self.avatar.setPixmap(thumbnail_pixmap)
        self.avatar.setRadius(34)
        self.avatar.setFixedSize(QSize(76, 76))

    def show_processing_state(self, is_processing: bool, text: str = "Processing..."):
        """Flow 3.1a, 4.2: Shows a visual indicator that the item is being processed."""
        self.setEnabled(not is_processing)
        if is_processing:
            self.processing_ring.show()
        else:
            self.processing_ring.hide()

    # ---Qt Event Handlers ---

    def contextMenuEvent(self, event):
        """Creates and shows a context menu on right-click."""
        menu = RoundMenu(parent=self)

        # ---Enable/dynamic disable/disable action ---
        is_enabled = self.item_data.get("is_enabled", False)
        action_text = "Disable" if is_enabled else "Enable"
        action_icon = FluentIcon.REMOVE_FROM if is_enabled else FluentIcon.ACCEPT

        toggle_action = QAction(action_icon.icon(), action_text, self)
        toggle_action.triggered.connect(
            lambda: self.view_model.toggle_item_status(
                self.item_data.get("id") or "false"
            )
        )
        menu.addAction(toggle_action)

        menu.addSeparator()

        # Open in File Explorer action
        open_folder_action = QAction(
            FluentIcon.FOLDER.icon(), "Open in File Explorer", self
        )
        open_folder_action.triggered.connect(
            lambda: self.view_model.open_in_explorer(self.item_data.get("id") or "")
        )
        menu.addAction(open_folder_action)

        pin_action_text = "Unpin" if self.item_data.get("is_pinned") else "Pin"
        pin_action = QAction(FluentIcon.PIN.icon(), pin_action_text, self)
        # Pin action.triggered.connect(...)

        menu.addAction(pin_action)

        rename_action = QAction(FluentIcon.EDIT.icon(), "Rename...", self)
        menu.addAction(rename_action)

        delete_action = QAction(FluentIcon.DELETE.icon(), "Delete", self)
        menu.addAction(delete_action)

        # Show menus in the cursor position

        menu.exec(event.globalPos())

    def mousePressEvent(self, event):
        """Flow 2.3: Notifies the parent panel that this item was clicked."""
        # This signal will be caught by ObjectListPanel, which then orchestrates
        # the call to the main view model to set the active object.

        self.item_selected.emit(self.item_data)
        super().mousePressEvent(event)
        pass

    def showEvent(self, event):
        """Triggers lazy-hydration when the widget becomes visible."""
        super().showEvent(event)
        # Revised: Data access from DICT

        if self.item_data.get("is_skeleton", False):
            item_id = self.item_data.get("id") or ""
            self.view_model.request_item_hydration(item_id)

    # ---Private Slots (Handling UI events) ---

    def _on_status_toggled(self):
        """Flow 3.1a: Forwards the status toggle action to the ViewModel."""
        self.view_model.toggle_item_status(self.item_data.get("id") or "")
        pass

    def _on_selection_changed(self):
        """Flow 3.2: Forwards the selection change to the ViewModel."""
        self.view_model.set_item_selected(
            self.item_data.get("id") or "", self.selection_checkbox.isChecked()
        )

    # ---Event Handlers for Hover Logic ---

    def enterEvent(self, event):
        """Called when the mouse cursor entered the widget area."""
        super().enterEvent(event)
        self._is_hovering = True
        self._update_checkbox_visibility()

    def leaveEvent(self, event):
        """Called when the mouse cursor left the widget area."""
        super().leaveEvent(event)
        self._is_hovering = False
        self._update_checkbox_visibility()

    def _update_checkbox_visibility(self):
        """
        The main logic to display/hide the checkbox.
        Checkbox will appear if hovers or if it has been checked.
        """
        if self._is_hovering or self.selection_checkbox.isChecked():
            self.selection_checkbox.show()
        else:
            self.selection_checkbox.hide()
