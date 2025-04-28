# app/utils/async_utils.py
import traceback
from typing import Any, Callable, Dict, Optional, Set
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, QTimer
from app.utils.logger_utils import logger

# --- Worker System (Background Task) ---


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    def __init__(self, fn: Callable, *args: Any, **kwargs: Any):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            self._handle_error(e)
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

    def _handle_error(self, e: Exception) -> None:
        """Centralized error handling."""
        logger.exception(f"Error during background task execution: {e}")
        exctype, value = type(e), e
        formatted_traceback = traceback.format_exc()
        self.signals.error.emit((exctype, value, formatted_traceback))


def run_in_background(fn: Callable, *args: Any, **kwargs: Any) -> Worker:
    worker = Worker(fn, *args, **kwargs)
    QThreadPool.globalInstance().start(worker)
    return worker


# --- Debouncer System ---
class Debouncer(QObject):
    """Manages QTimers to debounce function calls based on a key."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._timers: Dict[Any, QTimer] = {}

    def debounce(self, key: Any, func: Callable[[], None], delay_ms: int) -> None:
        """Schedules a function to run after a delay, resets timer if called again."""
        # Cancel previous timer if exists
        if key in self._timers:
            old_timer = self._timers.pop(key)
            old_timer.stop()
            old_timer.deleteLater()

        # Create new timer
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._execute_and_cleanup(key, func))
        timer.start(delay_ms)

        # Store timer
        self._timers[key] = timer

    def _execute_and_cleanup(self, key: Any, func: Callable[[], None]) -> None:
        """Internal helper to call function and remove timer reference."""
        try:
            func()
        finally:
            if key in self._timers:
                self._timers.pop(key).deleteLater()


# --- Async Status Manager ---


class AsyncStatusManager(QObject):
    """Manage async enable/disable/batch operations state for items."""

    status_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._pending_items: Set[str] = set()
        self._success_items: Set[str] = set()
        self._failed_items: Dict[str, str] = {}

    # Core methods
    def mark_pending(self, item_path: str):
        self._pending_items.add(item_path)
        self.status_changed.emit()

    def mark_success(self, item_path: str):
        self._pending_items.discard(item_path)
        self._success_items.add(item_path)
        self.status_changed.emit()

    def mark_failed(self, item_path: str, error_message: str):
        self._pending_items.discard(item_path)
        self._failed_items[item_path] = error_message
        self.status_changed.emit()

    def clear(self):
        self._pending_items.clear()
        self._success_items.clear()
        self._failed_items.clear()
        self.status_changed.emit()

    # Query methods
    def is_item_pending(self, item_path: str) -> bool:
        return item_path in self._pending_items

    def get_pending_count(self) -> int:
        return len(self._pending_items)

    def get_success_count(self) -> int:
        return len(self._success_items)

    def get_fail_count(self) -> int:
        return len(self._failed_items)

    def reset_count(self) -> None:
        self.clear()

    def get_all_pending_items(self) -> Set[str]:
        return set(self._pending_items)

    def get_all_failed_items(self) -> Dict[str, str]:
        return dict(self._failed_items)
