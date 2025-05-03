from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import (
    MessageBoxBase,
    SubtitleLabel,
    CaptionLabel,
    CheckBox,
    ScrollArea,
    StrongBodyLabel,
    FluentIcon,
    PushButton,
)


class FilterDialog(MessageBoxBase):
    """Fluent-style filter dialog"""

    def __init__(
        self,
        filters: dict[str, list[str]],
        active_filters: dict[str, set[str]],
        apply_callback,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Filter")
        self.filters = filters
        self.active_filters = active_filters
        self.apply_callback = apply_callback
        self.checkboxes: dict[str, dict[str, CheckBox]] = {}

        # --- Title
        self.titleLabel = SubtitleLabel("Select Filters", self)

        # --- Scroll area
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # --- Content widget inside scroll
        self.content_widget = QWidget()
        self.content_widget.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.content_widget)

        # Use viewLayout for outer layout, content widget will hold checkboxes
        self.scroll_layout = self._create_layout(self.content_widget)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.scroll_area)

        # --- Render filters
        for category, values in self.filters.items():
            self._render_category(category, values)

        # --- Action buttons
        self.yesButton.setText("Apply")
        self.cancelButton.setText("Cancel")

        self.scroll_area.setMinimumHeight(300)
        self.widget.setMinimumWidth(280)

    def _create_layout(self, parent):
        from PyQt6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(parent)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        return layout

    def _render_category(self, category: str, values: list[str]):
        label = StrongBodyLabel(category.title(), self.content_widget)
        label.setStyleSheet("margin-top: 12px; margin-bottom: 2px; margin-left: 0px;")
        self.scroll_layout.addWidget(label)

        self.checkboxes[category] = {}

        for val in sorted(values):
            cb = CheckBox(val, self.content_widget)
            cb.setChecked(val in self.active_filters.get(category, set()))
            self.scroll_layout.addWidget(cb)
            self.checkboxes[category][val] = cb

    def validate(self) -> bool:
        result = {}
        for cat, cb_dict in self.checkboxes.items():
            selected = {val for val, cb in cb_dict.items() if cb.isChecked()}
            if selected:
                result[cat] = selected

        self.apply_callback(result)
        return True
