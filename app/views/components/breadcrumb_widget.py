# app/views/components/breadcrumb_widget.py
# A navigation widget that displays the current folder path as clickable segments.

from __future__ import annotations
from pathlib import Path
import re
from typing import List

from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
from app.utils.logger_utils import logger
from app.core.signals import global_signals  # For toast notifications
from qfluentwidgets import BreadcrumbBar  # The core component for the UI


class BreadcrumbWidget(QWidget):
    """
    A navigation widget that wraps qfluentwidgets.BreadcrumbBar to display
    a clickable folder path.
    """

    # Custom signal that emits the full Path object of a clicked segment
    navigation_requested = pyqtSignal(Path)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.root_path: Path | None = None
        # Internal list to store the full path of each segment
        self._segment_paths: List[Path] = []

        self._init_ui()

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.breadcrumb = BreadcrumbBar(self)
        # The breadcrumb emits the index of the clicked item
        self.breadcrumb.currentIndexChanged.connect(self._on_segment_clicked)

        main_layout.addWidget(self.breadcrumb)

    def set_root_path(self, root_path: Path):
        """Sets the base path from which the breadcrumb starts."""
        self.root_path = root_path

    def update_path(self, current_path: Path):
        """
        Flow 2.3: Clears and rebuilds the breadcrumb segments based on the new path.
        This is called by the parent panel when the foldergrid's path changes.
        """
        if not self.root_path or not self.root_path.is_dir():
            # Can't update without a valid root
            return

        # Temporarily block signals to prevent firing while we rebuild the UI
        self.breadcrumb.blockSignals(True)

        self.breadcrumb.clear()
        self._segment_paths.clear()

        # Add the root segment
        self.breadcrumb.addItem(routeKey="root", text=self.root_path.name)
        self._segment_paths.append(self.root_path)

        # Add subsequent segments if the current path is a sub-path of root
        try:
            if current_path != self.root_path:
                relative_path = current_path.relative_to(self.root_path)

                cumulative_path = self.root_path
                for i, part in enumerate(relative_path.parts):
                    cumulative_path = cumulative_path / part
                    self._segment_paths.append(cumulative_path)
                    # Use the index as the routeKey for easy lookup
                    self.breadcrumb.addItem(routeKey=str(i + 1), text=part)

        except ValueError as e:
            logger.error(
                f"Path navigation error: '{current_path}' is not a subpath of root '{self.root_path}'. Error: {e}"
            )
            global_signals.toast_requested.emit("Navigation Error", "warning")
            return

        # Set the last segment as the active/current one
        self.breadcrumb.setCurrentIndex(len(self._segment_paths) - 1)

        # Unblock signals now that the UI is stable
        self.breadcrumb.blockSignals(False)

    def _on_segment_clicked(self, index: int):
        """
        Emits the navigation_requested signal with the full path associated
        with the clicked segment index.
        """
        if 0 <= index < len(self._segment_paths):
            path_to_navigate = self._segment_paths[index]
            self.navigation_requested.emit(path_to_navigate)

    def clear(self):
        """Clears all segments from the breadcrumb."""
        self.breadcrumb.blockSignals(True)
        self.breadcrumb.clear()
        self._segment_paths.clear()
        self.root_path = None
        self.breadcrumb.blockSignals(False)
