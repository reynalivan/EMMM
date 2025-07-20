# app/views/dialogs/create_object_dialog.py

from pathlib import Path
import re
from typing import Dict, Any, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QDialog, QHBoxLayout, QStackedWidget, QSizePolicy, QFileDialog
from PyQt6.QtGui import QImage, QPixmap
from qfluentwidgets import (
    LineEdit, ComboBox, BodyLabel, TitleLabel, SubtitleLabel,
    PrimaryPushButton, PushButton, Pivot, OpacityAniStackedWidget, FluentIcon, ImageLabel
)

from app.models.mod_item_model import ModType
from app.utils.image_utils import ImageUtils
from app.utils.logger_utils import logger
from app.utils.ui_utils import UiUtils


class CreateObjectDialog(QDialog):
    """
    A flexible dialog for creating new objects, using a Pivot to switch
    between Manual Creation and Database Sync modes.
    """
    ILLEGAL_CHAR_PATTERN = re.compile(r'[\\/:*?"<>|]')

    def __init__(self, schema: dict | None, existing_names: List[str], reconciliation_counts: dict,parent: QWidget | None = None):
        super().__init__(parent)
        # If schema is None, default to an empty dict to prevent errors.
        self.schema = schema or {}
        self.existing_names = [name.lower() for name in existing_names]
        self.reconciliation_counts = reconciliation_counts or {}

        # Internal state to track the dialog's result
        self.accepted_mode = None
        self.manual_data = {}
        self.selected_thumbnail_source: Any = None

        self._init_ui()
        self._connect_signals()

        # Set the initial state of the dynamic fields
        if self.object_type_combo.count() > 0:
            self._on_object_type_changed(self.object_type_combo.currentText())
        else:
            self._on_object_type_changed(None)

    def _init_ui(self):
        """Initializes the UI components and layout."""
        self.setWindowTitle("Create New Object")
        self.setFixedWidth(420)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- Pivot for Mode Selection ---
        self.pivot = Pivot(self)
        self.stack = QStackedWidget(self)

        # Create the two pages for the stack. These methods now handle a missing schema.
        self._create_manual_page()
        self._create_sync_page()

        # Set initial tab AFTER items have been added
        self.pivot.setCurrentItem("manual")

        # --- Bottom Buttons ---
        button_layout = QHBoxLayout()
        self.status_label = BodyLabel("")
        self.status_label.setStyleSheet("color: #f97171;") # Fluent error color
        self.cancel_button = PushButton("Cancel")
        self.ok_button = PrimaryPushButton("Create")

        button_layout.addWidget(self.status_label)
        button_layout.addStretch(1)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        main_layout.addWidget(self.pivot)
        main_layout.addWidget(self.stack, 1)
        main_layout.addLayout(button_layout)


    def _create_manual_page(self) -> QWidget:
        """Creates the form for manual creation, resilient to a missing schema."""
        manual_widget = QWidget()
        self.form_layout = QFormLayout(manual_widget) # Make form_layout an instance attribute
        self.form_layout.setContentsMargins(2, 15, 2, 5)
        self.form_layout.setSpacing(12)

        # --- Create all widgets ---
        self.folder_name_edit = LineEdit(self)
        self.object_type_combo = ComboBox(self)
        self.rarity_combo = ComboBox(self)
        self.gender_combo = ComboBox(self)
        self.element_combo = ComboBox(self)
        self.subtype_edit = LineEdit(self)
        self.tags_edit = LineEdit(self)

        # --- Populate from schema, with fallbacks ---
        # If schema is empty, these lists will be empty.
        self.object_type_combo.addItems([e.value for e in ModType])
        self.rarity_combo.addItems(self.schema.get('rarity', []))
        self.gender_combo.addItems(self.schema.get('gender', []))
        self.element_combo.addItems(self.schema.get('element', []))

        # --- Set enabled state based on schema availability ---
        # The entire manual form is less useful without a schema to define types.
        is_schema_present = bool(self.schema)
        self.object_type_combo.setEnabled(is_schema_present)
        # Folder name and tags can always be edited.

        # --- Thumbnail Section ---
        thumbnail_container = QWidget()
        thumbnail_layout = QVBoxLayout(thumbnail_container)
        thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        thumbnail_layout.setSpacing(8)

        # Preview and buttons for thumbnail
        self.thumbnail_preview = ImageLabel("app/assets/images/mod_placeholder.jpg") # Gambar placeholder
        self.thumbnail_preview.setMaximumHeight(300)
        self.thumbnail_preview.setMaximumWidth(300)
        self.thumbnail_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.thumbnail_preview.setMinimumSize(100, 100)
        # make image fit KeepAspectRatioByExpanding
        self.thumbnail_preview.setScaledContents(True)
        self.thumbnail_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)


        self.thumbnail_preview.setBorderRadius(8,8,8,8)
        thumbnail_layout.addWidget(self.thumbnail_preview, 0, Qt.AlignmentFlag.AlignCenter)

        thumb_button_layout = QHBoxLayout()
        self.browse_thumb_button = PushButton("Browse...")
        self.paste_thumb_button = PushButton("Paste Image")
        thumb_button_layout.addWidget(self.browse_thumb_button)
        thumb_button_layout.addWidget(self.paste_thumb_button)
        thumbnail_layout.addLayout(thumb_button_layout)

        # --- Add rows to layout ---
        self.form_layout.addRow("Folder Name:", self.folder_name_edit)
        self.form_layout.addRow("Object Type:", self.object_type_combo)
        self.form_layout.addRow("Rarity:", self.rarity_combo)
        self.form_layout.addRow("Gender:", self.gender_combo)
        self.form_layout.addRow("Element:", self.element_combo)
        self.form_layout.addRow("Subtype:", self.subtype_edit)
        self.form_layout.addRow("Initial Tags:", self.tags_edit)
        self.form_layout.addRow("Thumbnail:", thumbnail_container)
        self.stack.addWidget(manual_widget)
        self.pivot.addItem(
            routeKey="manual",
            text="Create Manually",
            onClick=lambda: self.stack.setCurrentWidget(manual_widget),
            icon=FluentIcon.EDIT,
        )


    def _create_sync_page(self) -> QWidget:
        """
        [REVISED] Creates a simplified info page for the database reconciliation feature.
        """
        sync_page = QWidget()
        layout = QVBoxLayout(sync_page)
        layout.setContentsMargins(15, 20, 15, 5)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(15)

        if not self.schema:
            # Case 1: Schema is missing. Sync is impossible.
            info_text = "Database file (schema.json) is missing or corrupted. Sync feature is disabled."
            info_label = BodyLabel(info_text, self)
            info_label.setWordWrap(True)
            info_label.setStyleSheet("color: #f97171;")
            self.sync_button = PrimaryPushButton("Sync Unavailable")
            self.sync_button.setEnabled(False)
        else:
            # Case 2: Schema exists. Show the reconciliation info.
            to_create = self.reconciliation_counts.get("to_create", 0)
            to_update = self.reconciliation_counts.get("to_update", 0)
            total_actions = to_create + to_update

            info_text = (
                "This action will reconcile your local folders with the database.\n\n"
                f"• {to_create} new folder(s) will be created.\n"
                f"• {to_update} existing folder(s) will be updated."
            )

            info_label = BodyLabel(info_text, self)
            info_label.setWordWrap(True)

            self.sync_button = PrimaryPushButton(f"Start Sync ({total_actions} Actions)")
            self.sync_button.setEnabled(total_actions > 0)

        layout.addWidget(info_label)
        layout.addWidget(self.sync_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)

        # (Logika untuk menambahkan ke stack dan pivot tetap sama)
        self.stack.addWidget(sync_page)
        self.pivot.addItem(
            routeKey="sync",
            text="Sync from Database",
            onClick=lambda: self.stack.setCurrentWidget(sync_page),
            icon=FluentIcon.SYNC,
        )


    def _connect_signals(self):
        """Connect all signals to their slots."""
        self.pivot.currentItemChanged.connect(self._on_pivot_changed)
        # Manual page signals
        self.object_type_combo.currentTextChanged.connect(self._on_object_type_changed)
        self.folder_name_edit.textChanged.connect(self._validate_manual_input)

        # Bottom button signals
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.cancel_button.clicked.connect(self.reject)

        # Sync page signal
        self.sync_button.clicked.connect(self._on_sync_clicked)
        self.browse_thumb_button.clicked.connect(self._on_browse_clicked)
        self.paste_thumb_button.clicked.connect(self._on_paste_clicked)

    def _on_pivot_changed(self):
        """Handle UI changes when switching between Manual and Sync tabs."""
        is_manual_tab = (self.pivot._currentRouteKey == "manual")
        logger.debug(f"Pivot changed to: {self.pivot._currentRouteKey}")
        self.ok_button.setVisible(is_manual_tab)
        self.status_label.setVisible(is_manual_tab)

        if is_manual_tab:
            # When switching to manual tab, re-validate the input.
            self._validate_manual_input()
        else:
            self.status_label.clear()

    def _validate_manual_input(self):
        if not self.schema:
            self.status_label.setText("Manual creation disabled: database schema is missing.")
            self.ok_button.setEnabled(False)
            return

        name = self.folder_name_edit.text().strip()
        is_valid = True
        error_message = ""
        if not name:
            error_message = "Folder name cannot be empty."
            is_valid = False
        elif self.ILLEGAL_CHAR_PATTERN.search(name):
            error_message = 'Name cannot contain: \\ / : * ? " < > |'
            is_valid = False
        elif name.lower() in self.existing_names:
            error_message = f"An object named '{name}' already exists."
            is_valid = False

        self.status_label.setText(error_message)
        self.ok_button.setEnabled(is_valid)

    def _on_ok_clicked(self):
        """Handles the click of the main 'Create' button."""
        self._validate_manual_input()
        if self.ok_button.isEnabled():
            self.accepted_mode = "manual"
            self.manual_data = self._get_manual_data()
            self.accept()

    def _on_sync_clicked(self):
        """Handles the click of the 'Sync Objects' button."""
        # Get the latest counts for the confirmation message
        to_create = self.reconciliation_counts.get("to_create", 0)
        to_update = self.reconciliation_counts.get("to_update", 0)

        # Build a clear confirmation message
        title = "Confirm Full Sync"
        content = (
            "You are about to start a full synchronization with the database.\n\n"
            f"• Up to {to_create} new object(s) will be created.\n"
            f"• Up to {to_update} existing object(s) will be updated.\n\n"
            "This action will modify your local mod folders. Are you sure you want to proceed?"
        )

        # Show the confirmation dialog
        # Using UiUtils.show_confirm_dialog is a good practice for consistency
        if UiUtils.show_confirm_dialog(self.window(), title, content, "Yes, Start Sync", "Cancel"):
            # If the user confirms, set the accepted mode and accept the dialog
            self.accepted_mode = "reconcile"
            self.accept()
        else:
            # If the user cancels, do nothing.
            logger.info("User cancelled the sync operation.")

    def _get_manual_data(self) -> Dict[str, Any]:
        """Gathers data from the manual creation form."""
        tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
        object_type = self.object_type_combo.currentText()

        data = {
            "name": self.folder_name_edit.text().strip(),
            "object_type": object_type,
            "tags": tags,
        }

        if object_type == ModType.CHARACTER.value:
            data["rarity"] = self.rarity_combo.currentText()
            data["gender"] = self.gender_combo.currentText()
            data["element"] = self.element_combo.currentText()
        else:
            subtype = self.subtype_edit.text().strip()
            if subtype:
                data["subtype"] = subtype

        if self.selected_thumbnail_source:
            data["thumbnail_source"] = self.selected_thumbnail_source


        return {"type": "manual", "data": data}


    def get_results(self) -> dict:
        """Public method to get the result after the dialog is accepted."""
        if self.accepted_mode == "manual":
            return {"mode": "manual", "task": self.manual_data}
        elif self.accepted_mode == "reconcile":
            return {"mode": "reconcile"}
        return {"mode": None}

    def _on_object_type_changed(self, text: str | None):
        """Shows or hides fields based on the selected object type."""
        # If no schema, text can be None. Default to not character.
        is_character = (text == ModType.CHARACTER.value) if text else False

        self.form_layout.labelForField(self.rarity_combo).setVisible(is_character)
        self.rarity_combo.setVisible(is_character)
        self.form_layout.labelForField(self.gender_combo).setVisible(is_character)
        self.gender_combo.setVisible(is_character)
        self.form_layout.labelForField(self.element_combo).setVisible(is_character)
        self.element_combo.setVisible(is_character)

        # Show Subtype field for any type that is NOT Character and not None
        show_subtype = bool(text and not is_character)
        self.form_layout.labelForField(self.subtype_edit).setVisible(show_subtype)
        self.subtype_edit.setVisible(show_subtype)

        self.adjustSize()

    def _on_browse_clicked(self):
        """Opens a file dialog to select a thumbnail image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Thumbnail Image",
            "", # Start directory
            "Image Files (*.png *.jpg *.jpeg *.webp)"
        )

        if not file_path:
            return

        self.selected_thumbnail_source = Path(file_path)

        pixmap = QPixmap(file_path)
        self.thumbnail_preview.setPixmap(pixmap.scaled(
            self.thumbnail_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def _on_paste_clicked(self):
        """Pastes an image from the clipboard and displays it as a preview."""
        image = ImageUtils.get_image_from_clipboard()

        if image is None:
            logger.warning("No valid image found on clipboard.")
            # show toast
            UiUtils.show_toast(self, "No valid image found on clipboard.", "warning")
            return

        # Convert PIL Image to QImage
        from PIL.ImageQt import ImageQt
        qimage = ImageQt(image)

        self.selected_thumbnail_source = image

        pixmap = QPixmap.fromImage(qimage)
        self.thumbnail_preview.setPixmap(pixmap.scaled(
            self.thumbnail_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))