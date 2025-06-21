# app/views/sections/preview_panel.py
from pathlib import Path
from this import s
from typing import List
from PyQt6.QtCore import QSignalBlocker, Qt
from collections import defaultdict
from app.services.ini_parsing_service import KeyBinding
from app.views.components.common.ini_file_group_widget import IniFileGroupWidget
from app.views.components.common.keybinding_widget import KeyBindingWidget
from PyQt6.QtWidgets import (
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
)

from qfluentwidgets import (
    CaptionLabel,
    SingleDirectionScrollArea,
    LineEdit,
    StrongBodyLabel,
    SubtitleLabel,
    BodyLabel,
    TextEdit,
    SwitchButton,
    PrimaryPushButton,
    PushButton,
    FluentIcon,
    VBoxLayout,
    GroupHeaderCardWidget,
    ExpandGroupSettingCard,
)

# Import ViewModels and Services for type hinting and dependency injection
from app.viewmodels.preview_panel_vm import PreviewPanelViewModel
from app.services.thumbnail_service import ThumbnailService

# Import custom widgets we've designed
from app.views.components.thumbnail_widget import ThumbnailSliderWidget

# from app.views.components.keybinding_widget import KeyBindingWidget # To be created later
PANEL_MARGIN = (12, 12, 12, 12)  # uniform inner padding


class PreviewPanel(QWidget):
    """The UI panel on the right that displays details for a selected FolderItem."""

    def __init__(
        self,
        viewmodel: PreviewPanelViewModel,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.view_model = viewmodel

        self._ini_group_widgets = []
        self._init_ui()
        self._bind_view_models()

    def _init_ui(self):
        self.setStyleSheet("QLineEdit,QTextEdit,QComboBox,QSpinBox{min-width:0;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(0)

        # Stack: empty view / scrolling view
        self.stack = QStackedWidget(self)
        root.addWidget(self.stack)

        # ── scrolling area (vertical-only) ───────────────────────────────────────
        self.scroll_area = SingleDirectionScrollArea(
            orient=Qt.Orientation.Vertical
        )  # ← fluent class
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # main content widget
        view = QWidget()
        view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        vbox = QVBoxLayout(view)
        vbox.setContentsMargins(*PANEL_MARGIN)
        vbox.setSpacing(16)

        # ── header ───────────────────────────────────────────────────────────────
        header = QVBoxLayout()
        header.setSpacing(4)
        self.title_label = SubtitleLabel("No Mod Selected")
        self.title_label.setWordWrap(True)
        self.status_switch = SwitchButton()
        self.status_switch.setOnText("Enabled")
        self.status_switch.setOffText("Disabled")
        header.addWidget(self.title_label)
        header.addWidget(self.status_switch)
        vbox.addLayout(header)

        # ── thumbnail ────────────────────────────────────────────────────────────
        vbox.addWidget(StrongBodyLabel("Preview Images"))
        self.thumbnail_slider = ThumbnailSliderWidget(self.view_model)
        self.thumbnail_slider.setMinimumHeight(178)
        self.thumbnail_slider.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        vbox.addWidget(self.thumbnail_slider)

        # ── description ─────────────────────────────────────────────────────────
        vbox.addWidget(StrongBodyLabel("Description"))
        self.description_editor = TextEdit()
        self.description_editor.setPlaceholderText("No description available.")
        self.description_editor.setMaximumHeight(80)
        vbox.addWidget(self.description_editor)
        self.save_description_button = PushButton(FluentIcon.SAVE, "Save Description")
        self.save_description_button.hide()
        vbox.addWidget(self.save_description_button, 0, Qt.AlignmentFlag.AlignLeft)

        # ── config ───────────────────────────────────────────────────────────────
        vbox.addWidget(StrongBodyLabel("Mod Configuration"))
        cfg_wrap = QWidget()
        cfg_wrap.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.ini_config_layout = QVBoxLayout(cfg_wrap)
        self.ini_config_layout.setContentsMargins(0, 0, 0, 0)
        self.ini_config_layout.setSpacing(10)
        vbox.addWidget(cfg_wrap)

        self.save_config_button = PrimaryPushButton(
            FluentIcon.SAVE, "Save Configuration"
        )
        self.save_config_button.hide()
        vbox.addWidget(self.save_config_button, 0, Qt.AlignmentFlag.AlignLeft)

        vbox.addStretch(1)

        # commit scrolling view
        self.scroll_area.setWidget(view)

        # ── stack pages ──────────────────────────────────────────────────────────
        self.empty_view = BodyLabel(
            "Select a mod from the grid to see its details",
        )
        self.empty_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.empty_view)
        self.stack.addWidget(self.scroll_area)
        self.stack.setCurrentWidget(self.empty_view)

    def _bind_view_models(self):
        """Connects this panel's widgets and slots to the ViewModel."""
        # VM -> View
        self.view_model.item_loaded.connect(self._on_item_loaded)
        self.view_model.ini_config_ready.connect(self._on_ini_config_ready)
        self.view_model.is_description_dirty_changed.connect(
            self.save_description_button.setVisible
        )
        self.view_model.ini_dirty_state_changed.connect(
            self.save_config_button.setVisible
        )
        self.view_model.save_description_state.connect(
            self._on_save_description_state_changed
        )
        self.view_model.save_config_state.connect(self._on_save_config_state_changed)

        # View -> VM
        self.description_editor.textChanged.connect(self._on_description_text_changed)
        self.save_description_button.clicked.connect(self.view_model.save_description)
        self.save_config_button.clicked.connect(self.view_model.save_ini_config)

        # The ThumbnailSliderWidget will handle its own internal bindings for add/remove,
        # calling the appropriate methods on the view_model.
        # e.g., self.thumbnail_slider.add_requested.connect(self.view_model.add_new_thumbnail)

    # --- SLOTS (Responding to ViewModel Signals) ---

    def _on_item_loaded(self, item_data: dict | None) -> None:
        """Refresh whole panel with selected‐item data."""
        if not item_data:
            self.clear_panel()
            return

        # ── show main content ────────────────────────────────────────────────────
        self.stack.setCurrentWidget(self.scroll_area)

        # ── reset transient state ───────────────────────────────────────────────
        self._clear_ini_layout()
        self.save_description_button.hide()
        self.save_config_button.hide()

        # ── title ───────────────────────────────────────────────────────────────
        full_title = item_data.get("actual_name", "N/A")
        self.title_label.setToolTip(full_title)  # show full on hover
        self.title_label.setText(
            full_title[:20] + "…"  # ellipsis if >20
            if len(full_title) > 20
            else full_title
        )

        # ── enable/disable switch (block signal to avoid feedback loop) ─────────
        with QSignalBlocker(self.status_switch):
            self.status_switch.setChecked(item_data.get("is_enabled", False))

        # ── thumbnails ──────────────────────────────────────────────────────────
        self.thumbnail_slider.set_image_paths(item_data.get("preview_images", []))

        # ── description ─────────────────────────────────────────────────────────
        desc = item_data.get("description", "")
        self.description_editor.setText(desc)
        self.save_description_button.hide()

    def _on_ini_config_ready(self, keybindings: list[KeyBinding]) -> None:
        """Populate ini-config panel dengan group per‐file, no overlap."""
        self._clear_ini_layout()
        self._ini_group_widgets.clear()

        # ── empty state
        if not keybindings:
            lbl = CaptionLabel("No editable keybindings found in this mod.")
            lbl.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self.ini_config_layout.addWidget(lbl)
            self._ini_group_widgets.append(lbl)
            self.ini_config_layout.addStretch(1)
            return

        # ── grouping & sorting
        by_file: dict[Path, list[KeyBinding]] = defaultdict(list)
        for kb in keybindings:
            by_file[kb.source_file].append(kb)

        root_path: Path | None = getattr(
            self.view_model.current_item_model, "folder_path", None
        )

        files_sorted = sorted(
            by_file, key=lambda p: (root_path and p.parent != root_path, str(p).lower())
        )

        # ── build UI
        for ini_path in files_sorted:
            # label relative ke root jika possible
            label = (
                str(ini_path.relative_to(root_path))
                if root_path and root_path in ini_path.parents
                else ini_path.name
            )

            group = IniFileGroupWidget(label, ini_path, self)
            group.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            group.open_file_requested.connect(self.view_model.open_ini_file)

            for kb in by_file[ini_path]:
                widget = KeyBindingWidget(kb, parent=group)
                widget.value_changed.connect(self.view_model.on_keybinding_edited)
                group.add_binding_widget(widget)

            self.ini_config_layout.addWidget(group)
            self._ini_group_widgets.append(group)
            self.ini_config_layout.addSpacing(12)  # simple visual gap

        self.ini_config_layout.addStretch(1)
        self.ini_config_layout.activate()

    def _clear_ini_layout(self):
        """Helper to remove all old keybinding widgets and cards."""
        while self.ini_config_layout.count():
            item = self.ini_config_layout.takeAt(0)
            if item is None:
                continue

            # widget langsung
            if w := item.widget():
                w.deleteLater()
                continue

            # sub-layout rekursif
            if lay := item.layout():
                while lay.count():
                    sub_item = lay.takeAt(0)
                    widget = sub_item.widget() if sub_item else None
                    if widget is not None:
                        widget.deleteLater()
                continue

            # spacerItem – cukup di-drop (GC yang urus)
            # item.spacerItem() is not None untuk spacer; nothing else needed

        self._ini_group_widgets.clear()
        self.ini_config_layout.update()

    def _on_description_text_changed(self):
        """Memberitahu ViewModel setiap kali teks di editor berubah."""
        self.view_model.on_description_changed(self.description_editor.toPlainText())

    # ADD THIS SLOT
    def _on_save_description_state_changed(self, text: str, is_enabled: bool):
        """Mengubah teks dan status tombol simpan."""
        self.save_description_button.setText(text)
        self.save_description_button.setEnabled(is_enabled)

    # ADD THIS NEW SLOT
    def _on_save_config_state_changed(self, text: str, is_enabled: bool):
        """Mengubah teks dan status tombol simpan konfigurasi."""
        self.save_config_button.setText(text)
        self.save_config_button.setEnabled(is_enabled)

    def clear_panel(self):
        """Clears all displayed data from the panel."""
        self.stack.setCurrentWidget(self.empty_view)
