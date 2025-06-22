# app/views/components/breadcrumb_widget.py
# A navigation widget that displays the current folder path as clickable segments.

from __future__ import annotations
from pathlib import Path
from typing import List

from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
from qfluentwidgets import BreadcrumbBar
from app.utils.logger_utils import logger


class BreadcrumbWidget(QWidget):
    """
    A navigation widget that displays a clickable folder path.
    It intelligently handles root path changes.
    """

    navigation_requested = pyqtSignal(Path)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.root_path: Path | None = None
        self._segment_paths: List[Path] = []
        self._init_ui()

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        self.breadcrumb = BreadcrumbBar(self)
        self.breadcrumb.currentIndexChanged.connect(self._on_segment_clicked)
        main_layout.addWidget(self.breadcrumb)

    def _build_from_path(self, current_path: Path):
        """Private helper to rebuild the UI from a given path and the current root."""
        self.breadcrumb.blockSignals(True)
        self.breadcrumb.clear()
        self._segment_paths.clear()

        if not self.root_path:
            self.breadcrumb.blockSignals(False)
            return

        # Add the root segment, which is always the first item
        self.breadcrumb.addItem(routeKey="root", text=self.root_path.name)
        self._segment_paths.append(self.root_path)

        # Add sub-segments if the current path is deeper than the root
        if current_path != self.root_path:
            try:
                relative_path = current_path.relative_to(self.root_path)
                cumulative_path = self.root_path
                for i, part in enumerate(relative_path.parts):
                    cumulative_path = cumulative_path / part
                    self._segment_paths.append(cumulative_path)
                    self.breadcrumb.addItem(routeKey=str(i + 1), text=part)
            except ValueError:
                # This should not happen due to the logic in set_current_path,
                # but it's a safe fallback.
                logger.error(
                    f"Path error: Could not find relation between '{current_path}' and root '{self.root_path}'"
                )
                self.clear()  # Clear the breadcrumb on error
                return

        self.breadcrumb.setCurrentIndex(len(self._segment_paths) - 1)
        self.breadcrumb.blockSignals(False)

    def _on_segment_clicked(self, index: int):
        """Emits the full path of the clicked segment."""
        if 0 <= index < len(self._segment_paths):
            path_to_navigate = self._segment_paths[index]
            self.navigation_requested.emit(path_to_navigate)

    # --- Public Methods ---

    def set_current_path(self, path: Path | None):
        """
        The main method to update the breadcrumb.
        It intelligently resets the root if the new path is not a sub-path
        of the old root, preventing navigation errors.
        """
        if not path or not path.is_dir():
            self.clear()
            return

        is_subpath = True
        if self.root_path:
            try:
                # Check if the new path is a descendant of the current root
                path.relative_to(self.root_path)
            except ValueError:
                is_subpath = False

        # If there is no root, or if the new path is not a sub-path,
        # it signifies a context switch (e.g., new ObjectItem selected).
        # We must reset the root path to this new path.
        if not self.root_path or not is_subpath:
            self.root_path = path

        # Now, rebuild the UI with a guaranteed correct root
        self._build_from_path(path)

    def clear(self):
        """Clears all segments and resets the root path."""
        self.breadcrumb.blockSignals(True)
        self.breadcrumb.clear()
        self._segment_paths.clear()
        self.root_path = None
        self.breadcrumb.blockSignals(False)
