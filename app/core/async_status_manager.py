# app/core/async_status_manager.py

from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Set


class AsyncStatusManager(QObject):
    """
    Manage async enable/disable/batch operations state for items.
    """

    status_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._pending_items: Set[str] = set()
        self._success_items: Set[str] = set()
        self._failed_items: Dict[str, str] = {}  # path -> error msg

    # --- Core Methods ---

    def mark_pending(self, item_path: str):
        """Register item as pending operation."""
        self._pending_items.add(item_path)
        self.status_changed.emit()

    def mark_success(self, item_path: str):
        """Register item as successful operation."""
        self._pending_items.discard(item_path)
        self._success_items.add(item_path)
        self.status_changed.emit()

    def mark_failed(self, item_path: str, error_message: str):
        """Register item as failed operation."""
        self._pending_items.discard(item_path)
        self._failed_items[item_path] = error_message
        self.status_changed.emit()

    def clear(self):
        """Clear all tracking states."""
        self._pending_items.clear()
        self._success_items.clear()
        self._failed_items.clear()
        self.status_changed.emit()

    # --- Query Methods ---

    def is_item_pending(self, item_path: str) -> bool:
        """Check if item is currently pending."""
        return item_path in self._pending_items

    def get_pending_count(self) -> int:
        """Return number of items currently pending."""
        return len(self._pending_items)

    def get_success_count(self) -> int:
        """Return number of successful operations."""
        return len(self._success_items)

    def get_fail_count(self) -> int:
        """Return number of failed operations."""
        return len(self._failed_items)

    def reset_count(self) -> None:
        self._success_items.clear()
        self._failed_items.clear()
        self._pending_items.clear()
        self.status_changed.emit()

    def get_all_pending_items(self) -> Set[str]:
        """Return all pending item paths."""
        return set(self._pending_items)

    def get_all_failed_items(self) -> Dict[str, str]:
        """Return all failed item paths and errors."""
        return dict(self._failed_items)
