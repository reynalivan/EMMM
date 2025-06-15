# app/views/components/common/flow_grid_widget.py
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FlowLayout


class FlowGridWidget(QWidget):
    """A widget that displays other widgets in a responsive flow layout."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FlowGridContentWidget")

        # The FlowLayout is the main layout for this widget
        self.flowLayout = FlowLayout(self, needAni=False)
        self.flowLayout.setContentsMargins(12, 12, 12, 12)
        self.flowLayout.setVerticalSpacing(15)
        self.flowLayout.setHorizontalSpacing(15)

    def add_widget(self, widget: QWidget):
        """Adds a widget to the flow layout."""
        self.flowLayout.addWidget(widget)

    def clear_items(self):
        """
        Removes all widgets from the flow layout.
        The built-in function handles widget deletion safely.
        """
        # self.flowLayout.removeAllWidgets()
        self.flowLayout.takeAllWidgets()
