# app/views/components/breadcrumb_widget.py
from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal


class BreadcrumbWidget(QWidget):
    """
    A navigation widget that displays the current folder path as
    clickable segments.
    """

    # Custom signal that emits the full path of a clicked segment
    navigation_requested = pyqtSignal(Path)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.root_path: Path | None = None

        self._init_ui()

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        # The layout will be populated dynamically.
        # e.g., self.layout = QHBoxLayout(self)
        pass

    def set_root_path(self, root_path: Path):
        """Sets the base path from which the breadcrumb starts."""
        self.root_path = root_path

    def update_path(self, current_path: Path):
        """
        Flow 2.3: Clears and rebuilds the breadcrumb segments based on the new path.
        This is called by the parent panel when the foldergrid's path changes.
        """
        # 1. Clear the current layout.
        # 2. Calculate the relative path from self.root_path.
        # 3. For each part of the path, create a clickable button or label.
        # 4. Connect each button's clicked signal to a lambda that calls _on_segment_clicked
        #    with the cumulative path for that segment.
        pass

    # --- Private Slots (Handling UI events) ---

    def _on_segment_clicked(self, path_to_navigate: Path):
        """
        Emits the navigation_requested signal with the path associated
        with the clicked segment.
        """
        self.navigation_requested.emit(path_to_navigate)
        pass
