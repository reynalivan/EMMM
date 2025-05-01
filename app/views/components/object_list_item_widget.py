# App/views/components/object list item widget.py

import os
from turtle import position
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint
from app.models.object_item_model import ObjectItemModel
from app.core import constants
from qfluentwidgets import TeachingTip, TeachingTipView, TeachingTipTailPosition

# ---Fluent Widget Imports  ---

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    SwitchButton,
    CheckBox,
    ToolButton,
    TransparentToolButton,
    FluentIcon,
)
from app.utils.logger_utils import logger


class ObjectListItemWidget(QWidget):
    """Custom widget representing a single item in the ObjectListPanel."""

    # ---Signals ---
    status_toggled = pyqtSignal(bool)
    bulk_selection_changed = pyqtSignal(bool)
    # ---End Signals ---

    def __init__(self, model: ObjectItemModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.item_model = model
        thumb_w = getattr(constants, "OBJECT_THUMB_SIZE_W", 64)
        thumb_h = getattr(constants, "OBJECT_THUMB_SIZE_H", 64)
        self._thumb_size = QSize(thumb_w, thumb_h)

        self._setup_ui()
        self._setup_loading_overlay()
        self._update_ui_from_model()  # Call after UI made

        self._connect_signals()  # Call after UI made

        self.setObjectName("ObjectListItem")
        self.setStyleSheet(
            "#ObjectListItem { background-color: rgba(243, 243, 243, 0.7); border-radius: 6px; padding: 5px; }"
            "#ObjectListItem:hover { background-color: rgba(235, 235, 235, 0.8); }"
        )

    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(6)

        # --- Thumbnail + Checkbox Container ---
        self.thumbnail_container = QWidget()
        self.thumbnail_container.setFixedSize(self._thumb_size)
        self.thumbnail_container.setObjectName("ThumbnailContainer")
        self.thumbnail_container.setStyleSheet("background: transparent;")
        self.thumbnail_label = QLabel(self.thumbnail_container)
        self.thumbnail_label.setFixedSize(self._thumb_size)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setObjectName("ThumbnailLabel")

        # Overlay checkbox
        self.bulk_checkbox = CheckBox(self.thumbnail_container)
        self.bulk_checkbox.setToolTip("Select for batch operations")
        self.bulk_checkbox.move(4, 4)
        self.bulk_checkbox.setVisible(False)  # Only show on hover/checked
        self.bulk_checkbox.raise_()

        self.main_layout.addWidget(
            self.thumbnail_container, 0, Qt.AlignmentFlag.AlignTop
        )

        # --- Center Info Block ---
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(6)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.name_label = BodyLabel()
        self.name_label.setObjectName("NameLabel")
        self.name_label.setMinimumWidth(200)
        self.name_label.setSizePolicy(
            self.name_label.sizePolicy().horizontalPolicy(),
            self.name_label.sizePolicy().verticalPolicy(),
        )

        # Status Row
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)

        self.status_label = CaptionLabel()
        self.status_label.setObjectName("StatusLabel")
        self.status_switch = SwitchButton()
        self.status_switch.setToolTip("Toggle Mod On/Off")

        status_layout.addWidget(self.status_switch)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        center_layout.addWidget(self.name_label)
        center_layout.addWidget(status_widget)

        self.main_layout.addWidget(center_widget, 1)
        self.main_layout.addStretch(1)

        self.set_placeholder_thumbnail()

    def _setup_loading_overlay(self):
        """Creates the loading icon overlay widget, initially hidden."""
        # Use a non-interactive TransparentToolButton with FluentIcon.SYNC

        self.loading_icon = TransparentToolButton(
            FluentIcon.SYNC, self
        )  # Parent is self

        self.loading_icon.setObjectName("LoadingIconOverlay")
        indicator_size = 28  # Adjust the size of the loading icon

        self.loading_icon.setFixedSize(indicator_size, indicator_size)
        self.loading_icon.setIconSize(
            QSize(indicator_size - 10, indicator_size - 10)
        )  # Icons smaller than buttons

        self.loading_icon.setEnabled(False)  # Not interactive

        self.loading_icon.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Styling to make it look like overlay (optional)
        # self.loading_icon.setstylesheet ("Background-Color: RGBA (100, 100, 100, 0.5); Border-Radius: 14px;")

        self.loading_icon.hide()  # Starting in a hidden state
        # The initial position will be rearranged by Resizeevent

    # ---END MODIFICATION ---

    def _update_ui_from_model(self):
        """Populates the widgets with data from the item model."""
        display_name = self.item_model.display_name
        self.name_label.setText(display_name)
        self.name_label.setToolTip(display_name)  # Add tooltip

        self.status_switch.blockSignals(True)
        self.status_switch.setChecked(self.item_model.status)
        self.status_switch.blockSignals(False)
        self.status_switch.setOnText("Enabled")
        self.status_switch.setOffText("Disabled")
        self.status_switch.setToolTip("Toggle Mod Enabled/Disabled status")

        # Reset bulk checkbox

        self.bulk_checkbox.blockSignals(True)
        self.bulk_checkbox.setChecked(False)
        self.bulk_checkbox.blockSignals(False)

        # Call Placeholder set here too if needed when updated
        # self.set_placeholder_thumbnail () # may not need to be called back here

    def _connect_signals(self):
        """Connects signals from internal widgets."""
        # ---Start Verification: Make sure the connection is there ---

        self.status_switch.checkedChanged.connect(self._on_status_changed)
        self.bulk_checkbox.stateChanged.connect(self._on_bulk_checked_changed)
        # ---End Verification ---

    # ---Slots ---

    def _on_status_changed(self, checked: bool):
        """Handles the status switch change and emits signal."""
        # ---Start Verification: Make sure the signal is emitted ---

        self.status_toggled.emit(checked)
        # ---End Verification ---

    def _on_bulk_checked_changed(self, state: int):
        """Handles the bulk checkbox state change and emits signal."""
        is_checked = state == Qt.CheckState.Checked.value
        # Make sure this signal is there and emitted if the bulk checkbox is used

        self.bulk_selection_changed.emit(is_checked)

    # ---Public Methods ---

    def get_item_model(self) -> ObjectItemModel:
        """Returns the data model associated with this widget."""
        return self.item_model

    # (Method set_thumbnail and set_placeholder_thumbnail remain the same as your code)

    def set_thumbnail(self, pixmap: QPixmap | None):
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                self._thumb_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumbnail_label.setPixmap(scaled_pixmap)
            self.thumbnail_label.setText("")
            self.thumbnail_label.setStyleSheet(
                "#ThumbnailLabel { background-color: transparent; border-radius: 4px; }"
            )
        else:
            self.set_placeholder_thumbnail()

    def set_placeholder_thumbnail(self):
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("")
        self.thumbnail_label.setStyleSheet(
            """
            #ThumbnailLabel {
                background-color: rgba(0, 0, 0, 0.04); color: rgba(0, 0, 0, 0.5);
                border-radius: 4px; border: 1px solid rgba(0, 0, 0, 0.07);
                /* TODO: Placeholder icon */
            }
            """
        )

    def set_interactive(self, enabled: bool):
        """Enable or disable interactive elements (switch, checkbox)."""
        self.status_switch.setEnabled(enabled)
        self.bulk_checkbox.setEnabled(enabled)
        # If stuck, log it
        logger.debug(
            f"Widget [{self.item_model.display_name}] interactive set to {enabled}"
        )

    def show_loading_overlay(self, show: bool):
        """Show or hide the loading indicator overlay."""
        if not hasattr(self, "loading_icon"):
            return  # Safety check

        if show:
            # Optional: Make widget slightly more transparent when loading
            # self.setOpacity(0.8) # Already handled by set_interactive?
            self.loading_icon.setIcon(FluentIcon.SYNC)

        else:
            # Restore opacity if changed
            # self.setOpacity(1.0)
            self.loading_icon.setIcon(FluentIcon.CLOSE)

    def update_display(self, data: dict):
        """Updates the displayed info based on data from ViewModel signal."""
        # logger.debug(f"Widget {self.item_model.display_name}: Updating display with {data}") # Keep lean
        # Extract data safely using .get with fallback to current model state

        new_status = data.get("status", self.item_model.status)
        new_display_name = data.get("display_name", self.item_model.display_name)
        # new_path = data.get('path', self.item_model.path) # Path for tooltip

        # Update UI elements
        self.name_label.setText(new_display_name)
        self.name_label.setToolTip(new_display_name)  # Update tooltip

        if isinstance(new_status, bool):
            self.status_switch.blockSignals(True)
            self.status_switch.setChecked(new_status)
            self.status_switch.blockSignals(False)

            self.set_interactive(True)
        else:
            logger.warning(
                f"Widget update skipped invalid status for {self.item_model.display_name}: {new_status}"
            )

        self.status_label.enabled = True
        # Update switch state programmatically, block signals

        self.status_switch.blockSignals(True)
        self.status_switch.setChecked(new_status)
        self.status_switch.blockSignals(False)
        self.status_label.setText("Enabled" if new_status else "Disabled")

    # app/views/components/object_list_item_widget.py

    def set_selected_state(self, is_selected: bool):
        """Toggle between switch and status label visibility."""
        self.status_switch.setVisible(is_selected)
        self.status_label.setVisible(not is_selected)

    def show_metadata_flyout(self):
        """Show metadata flyout with rich info."""
        props = self.item_model.properties or {}
        if not props:
            return

        actual_name = self.item_model.actual_name or "-"
        element = props.get("element", "-").capitalize()
        region = props.get("region", "-").capitalize()
        rarity = props.get("rarity", "-").capitalize()
        gender = props.get("gender", "-").capitalize()
        roles = ", ".join(props.get("roles", [])) or "-"
        weapon = props.get("weapon", "-").capitalize()

        # Compose content
        content_lines = [
            f"Element: {element}",
            f"Region: {region}",
            f"Rarity: {rarity}",
            f"Gender: {gender}",
            f"Roles: {roles}",
            f"Weapon: {weapon}",
        ]
        content = "\n".join(content_lines)
        position = TeachingTipTailPosition.LEFT_TOP

        view = TeachingTipView(
            title=actual_name,
            content=content,
            tailPosition=position,
            isClosable=False,
        )

        self._meta_tip = TeachingTip.make(
            target=self.name_label,
            view=view,
            duration=-1,
            tailPosition=position,
            parent=self,
        )

    def enterEvent(self, event):
        if not self.bulk_checkbox.isChecked():
            self.bulk_checkbox.setVisible(True)
        self.show_metadata_flyout()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.bulk_checkbox.isChecked():
            self.bulk_checkbox.setVisible(False)

        if hasattr(self, "_meta_tip") and self._meta_tip:
            self._meta_tip.close()
            self._meta_tip = None
        super().leaveEvent(event)
