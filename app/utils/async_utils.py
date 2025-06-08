# app/utils/async_utils.py
import sys
import traceback
from functools import wraps
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QTimer


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""

    # Note: A worker's target function can connect to these signals
    # by accepting a 'signals' keyword argument.

    finished = pyqtSignal()
    error = pyqtSignal(tuple)  # exctype, value, traceback
    result = pyqtSignal(object)
    progress = pyqtSignal(int, int)  # current, total


class Worker(QRunnable):
    """A generic, reusable worker thread for running any function."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        # --- Store task and arguments ---
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # --- Add the signals object to the function's keyword arguments ---
        # This allows the target function to emit progress signals.
        self.kwargs["signals"] = self.signals

    def run(self):
        """Execute the worker's task."""
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


def debounce(delay_ms: int):
    """A decorator that delays function execution, useful for search bars."""

    def decorator(fn):
        timer = None

        @wraps(fn)
        def wrapper(*args, **kwargs):
            nonlocal timer
            if timer is not None:
                timer.stop()
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: fn(*args, **kwargs))
            timer.start(delay_ms)

        return wrapper

    return decorator
