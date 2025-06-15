# app/utils/async_utils.py
import sys
import traceback
import inspect
from functools import wraps
from typing import Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QTimer


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    Supported signals are:
    - finished: No data
    - error: tuple (exctype, value, traceback.format_exc())
    - result: object data returned from processing
    - progress: int percentage
    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)  # exctype, value, traceback
    result = pyqtSignal(object)
    progress = pyqtSignal(int, int)  # current, total


class Worker(QRunnable):
    """A generic, reusable worker thread for running any function."""

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any):
        super().__init__()
        # --- Store task and arguments ---
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Only inject the progress_callback if the target function can accept it.
        # This prevents TypeError for functions with fixed arguments.
        try:
            sig = inspect.signature(self.fn)
            if "progress_callback" in sig.parameters:
                self.kwargs["progress_callback"] = self.signals.progress
        except (ValueError, TypeError):
            # Handles cases where the target is a built-in or C-function that can't be inspected.
            # In these cases, we assume it doesn't take our custom callback.
            pass
        # --- END REVISED SECTION ---

    def run(self):
        """Execute the worker's task."""
        try:
            # Execute the target function with all provided arguments
            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            # If an error occurs, capture it and emit the error signal
            exctype, value = sys.exc_info()[:2]
            tb = traceback.format_exc()
            self.signals.error.emit((exctype, value, tb))
        else:
            # If successful, emit the result signal
            self.signals.result.emit(result)
        finally:
            # In all cases, emit the finished signal
            self.signals.finished.emit()


def debounce(delay_ms: int):
    """A decorator that delays function execution, useful for search bars."""

    def decorator(fn: Callable) -> Callable:
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
