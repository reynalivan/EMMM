# app/utils/async_utils.py
# Utilities for asynchronous operations and debouncing.

import traceback
from typing import Any, Callable, Dict, Optional
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, QTimer

# Assuming logger is configured in logger_utils
from app.utils.logger_utils import logger


class WorkerSignals(QObject):
    """Defines signals available from a running worker thread."""
    finished = pyqtSignal()
    error = pyqtSignal(tuple)  # (type, value, traceback)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)  # Optional progress reporting


class Worker(QRunnable):
    """
    Worker thread for executing a function in the background.

    Inherits from QRunnable to run correctly with QThreadPool.

    Args:
        fn: The function callback to run.
        *args: Arguments to pass to the callback function.
        **kwargs: Keyword arguments to pass to the callback function.
    """

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any):
        super().__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        # Optional: Add progress callback mechanism if needed
        # self.kwargs['progress_callback'] = self.signals.progress

    def run(self) -> None:
        """Execute the worker function."""
        # Retrieve args/kwargs here; note constructor arguments are kept.
        #
        # This method runs in a separate thread provided by QThreadPool.
        # Be careful with accessing GUI elements or non-thread-safe objects.
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            logger.exception(f"Error during background task execution: {e}")
            exctype, value = type(e), e
            formatted_traceback = traceback.format_exc()
            self.signals.error.emit((exctype, value, formatted_traceback))
        else:
            self.signals.result.emit(result)  # Return result of processing
        finally:
            self.signals.finished.emit()  # Done


class Debouncer(QObject):
    """Manages QTimers to debounce function calls based on a key."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._timers: Dict[Any, QTimer] = {}

    def debounce(self, key: Any, func: Callable[[], None],
                 delay_ms: int) -> None:
        """
        Schedules a function to run after a delay, resetting the timer if called again for the same key.

        Args:
            key: A unique identifier for the debounced action.
            func: The function (taking no arguments) to call after the delay.
            delay_ms: The debounce interval in milliseconds.
        """
        # Implementation Note: Stop existing timer for key, create new single-shot timer,
        # connect its timeout to func and timer cleanup, start timer. Store timer in dict.
        pass  # Skeleton implementation


# Optional helper function
def run_in_background(fn: Callable, *args: Any, **kwargs: Any) -> Worker:
    """
    Creates a Worker and submits it to the global thread pool.

    Args:
        fn: The function to run in the background.
        *args: Positional arguments for fn.
        **kwargs: Keyword arguments for fn.

    Returns:
        The Worker instance (useful for connecting signals).
    """
    worker = Worker(fn, *args, **kwargs)
    QThreadPool.globalInstance().start(worker)
    return worker
