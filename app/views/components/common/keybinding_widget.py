# app/views/components/keybinding_widget.py

from typing import List, Dict
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QVBoxLayout,
    QWidget,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
)

from qfluentwidgets import (
    BodyLabel,
    LineEdit,
    ComboBox,
    StrongBodyLabel,
    CaptionLabel,
    VBoxLayout,
    SpinBox,
    FlowLayout,
    FluentIcon,
)

from app.services.Iniparsing_service import KeyBinding, Assignment

# ---------- constants ----------
ROW_MARGINS = (4, 0, 4, 0)
HEADER_MARGIN = (4, 8, 4, 8)
FIELD_WIDTH = 160
SPACING_V = 8


class KeyBindingWidget(QWidget):
    """
    A widget to display and edit a single key binding entry.
    This version has a robust layout structure to prevent parenting errors.
    """

    value_changed = pyqtSignal(str, str, object, str)

    def __init__(self, binding_data: KeyBinding, parent: QWidget | None = None):
        super().__init__(parent)
        self.binding_data = binding_data
        self.binding_id = self.binding_data.binding_id

        self.key_edits: List[LineEdit] = []
        self.back_edits: List[LineEdit] = []
        self.assignment_widgets: Dict[str, QWidget] = {}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Build widget UI – vertical list, label-left field-right, fluent widgets."""
        # global
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet("QLineEdit,QComboBox,QSpinBox{min-width:0;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING_V)

        # ── header ────────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(*HEADER_MARGIN)
        header.addWidget(StrongBodyLabel(self.binding_data.section_name))
        header.addStretch(1)
        if self.binding_data.condition:
            header.addWidget(CaptionLabel(f"if: {self.binding_data.condition}"))
        root.addLayout(header)

        # ── assignments ───────────────────────────────────────────────────────────
        for a in self.binding_data.assignments:
            root.addLayout(self._create_row(a.variable, self._create_smart_input(a)))

        # ── triggers (keys / backs) ───────────────────────────────────────────────
        if self.binding_data.keys or self.binding_data.backs:
            if self.binding_data.assignments:
                root.addWidget(self._hline())

            for i, val in enumerate(self.binding_data.keys, 1):
                root.addLayout(self._create_row(f"Key", self._line_edit(val)))

            for i, val in enumerate(self.binding_data.backs, 1):
                root.addLayout(self._create_row(f"Back", self._line_edit(val)))

        self.setLayout(root)

    # ── helpers ──────────────────────────────────────────────────────────────────
    def _create_row(self, text: str, field: QWidget) -> QHBoxLayout:
        """Return HBox: [label][stretch][field-right]."""
        row = QHBoxLayout()
        row.setContentsMargins(*ROW_MARGINS)
        row.setSpacing(8)

        lbl = BodyLabel(f"{text}:")
        lbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        field.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        field.setFixedWidth(FIELD_WIDTH)

        row.addWidget(lbl)
        row.addStretch(1)
        row.addWidget(field, 0, Qt.AlignmentFlag.AlignRight)
        return row

    def _line_edit(self, text: str) -> LineEdit:
        le = LineEdit()
        le.setText(text)
        le.setFixedWidth(FIELD_WIDTH)
        return le

    def _hline(self) -> QFrame:
        ln = QFrame()
        ln.setFrameShape(QFrame.Shape.HLine)
        ln.setFrameShadow(QFrame.Shadow.Sunken)
        return ln

    def _create_assignment_row(self, assignment: Assignment) -> QWidget:
        """Row: [label][stretch][field-right]."""
        container = QWidget(self)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        row = QHBoxLayout()
        row.setContentsMargins(*ROW_MARGINS)
        row.setSpacing(SPACING_V)

        lbl = BodyLabel(f"{assignment.variable}:")
        lbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        row.addWidget(lbl)

        row.addStretch(1)

        field = self._create_smart_input(assignment)
        field.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        field.setFixedWidth(FIELD_WIDTH)
        self.assignment_widgets[assignment.variable] = field
        row.addWidget(field, 0, Qt.AlignmentFlag.AlignRight)

        container.setLayout(row)
        return container

    def _create_smart_input(self, assignment: Assignment) -> QWidget:
        """SpinBox jika numeric sequence, else ComboBox."""

        cb = ComboBox(self)
        cb.setFixedWidth(FIELD_WIDTH)
        cb.setStyleSheet("min-width:0;")
        if assignment.cycle_options:
            cb.addItems(assignment.cycle_options)
        cb.setCurrentText(
            assignment.current_value
            or (assignment.cycle_options[0] if assignment.cycle_options else "")
        )
        return cb

    def _create_trigger_row(
        self,
        parent_layout: QVBoxLayout,
        label: str,
        values: list[str],
        widget_list: list[LineEdit],
    ) -> None:
        """Add trigger rows ke parent_layout."""

        for idx, val in enumerate(values, 1):
            row = QWidget(self)
            row.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )

            h = QHBoxLayout()
            h.setContentsMargins(*ROW_MARGINS)
            h.setSpacing(SPACING_V)

            cap = CaptionLabel(f"{label} {idx}:")
            cap.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
            h.addWidget(cap)

            h.addStretch(1)

            edit = LineEdit(self)
            edit.setText(val)
            edit.setFixedWidth(FIELD_WIDTH)
            edit.setStyleSheet("min-width:0;")
            widget_list.append(edit)
            h.addWidget(edit, 0, Qt.AlignmentFlag.AlignRight)

            row.setLayout(h)
            parent_layout.addWidget(row)

    def _connect_signals(self):
        for i, edit in enumerate(self.key_edits):
            edit.textChanged.connect(
                lambda text, index=i: self.value_changed.emit(
                    self.binding_id, "key", index, text
                )
            )
        for i, edit in enumerate(self.back_edits):
            edit.textChanged.connect(
                lambda text, index=i: self.value_changed.emit(
                    self.binding_id, "back", index, text
                )
            )
        for var, widget in self.assignment_widgets.items():
            if isinstance(widget, ComboBox):
                widget.currentTextChanged.connect(
                    lambda text, v=var: self.value_changed.emit(
                        self.binding_id, "assignment", v, text
                    )
                )
            elif isinstance(widget, SpinBox):
                widget.valueChanged.connect(
                    lambda val, v=var: self.value_changed.emit(
                        self.binding_id, "assignment", v, str(val)
                    )
                )
