import os
from typing import Optional, Set, List, Dict
from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
    QTimer,
    QThread,
    QMetaObject,
    Qt,
    Q_ARG,
    pyqtSlot,
)
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from app.utils.logger_utils import logger
from app.utils.image_cache import ImageCache


# --- Event Class ---
class FileChangeEvent:
    def __init__(self, event_type: str, src_path: str, dest_path: Optional[str] = None):
        self.event_type = event_type
        self.src_path = src_path
        self.dest_path = dest_path


# --- Thread Handler ---
class WatchdogThread(QThread):
    def __init__(self, handler: FileSystemEventHandler):
        super().__init__()
        self._observer = Observer()
        self._handler = handler
        self._running = False

    def run(self):
        self._running = True
        self._observer.start()
        while self._running:
            self.msleep(200)  # Soft idle

    def stop(self):
        self._running = False
        self._observer.stop()
        self._observer.join()

    def schedule(self, handler, path, recursive=False):
        self._observer.schedule(handler, path, recursive=recursive)

    def unschedule(self, path):
        """Unschedule a specific watched path safely."""
        for watch in list(self._observer._watches.values()):
            if watch.path == path:
                self._observer.unschedule(watch)
                logger.debug(f"WatchdogThread: Unschedule {path}")
                return
        logger.warning(f"WatchdogThread: Path not found to unschedule: {path}")


# --- Main Service ---
class FileWatcherService(QObject):
    fileBatchChanged = pyqtSignal(str, list)  # folder_path, list[FileChangeEvent]
    fileChanged = pyqtSignal(str)
    statsUpdated = pyqtSignal(int, float)  # folder_count: int, change_rate: float
    MAX_BATCH_SIZE = 250  # Max event per folder per batch

    def __init__(
        self, cache: Optional[ImageCache] = None, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._thread: Optional[WatchdogThread] = None
        self._handler = _WatchdogHandler(self)
        self._watched_paths: Set[str] = set()
        self._active = False

        self._pending_events: Dict[str, List[FileChangeEvent]] = {}
        self._batch_timer = QTimer()
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._emit_batch_changes)

        self._cache = cache
        self._events_count = 0
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._log_stats)

    def start(self):
        if self._thread is None:
            self._thread = WatchdogThread(self._handler)
        if not self._thread.isRunning():
            self._thread.start()
            logger.info("FileWatcherService thread started.")
        self._stats_timer.start(10000)

    def stop(self):
        if self._thread:
            self._thread.stop()
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            logger.info("FileWatcherService thread stopped.")
        self._watched_paths.clear()
        self._stats_timer.stop()

    def enable(self):
        self._active = True
        logger.info("FileWatcherService ENABLED.")

    def disable(self):
        self._active = False
        logger.info("FileWatcherService DISABLED.")

    def is_enabled(self) -> bool:
        return self._active

    def add_path(self, folder_path: str):
        if not self._active:
            logger.debug(
                f"Watcher ignored add_path because service disabled: {folder_path}"
            )
            return
        if not os.path.isdir(folder_path):
            logger.warning(f"Invalid path given to Watcher: {folder_path}")
            return
        if folder_path in self._watched_paths:
            return

        if self._thread is None or not self._thread.isRunning():
            self.start()

        self._thread.schedule(self._handler, folder_path, recursive=False)
        self._watched_paths.add(folder_path)
        logger.info(f"Watching {len(self._watched_paths)} folders.")

    def remove_path(self, folder_path: str):
        if not self._thread or not self._thread.isRunning():
            return

        normalized_path = os.path.normpath(folder_path)
        if normalized_path in self._watched_paths:
            try:
                self._thread.unschedule(normalized_path)
                self._watched_paths.remove(normalized_path)
                logger.info(f"FileWatcherService: Unwatched path {normalized_path}")
            except Exception as e:
                logger.error(
                    f"FileWatcherService: Failed to unwatch {normalized_path}: {e}"
                )

    def clear_watches(self):
        self.stop()

    def _enqueue_event(self, evt: FileChangeEvent):
        folder_path = os.path.dirname(evt.src_path)

        if folder_path not in self._pending_events:
            self._pending_events[folder_path] = []

        self._pending_events[folder_path].append(evt)
        self._events_count += 1

        if evt.src_path:
            QMetaObject.invokeMethod(
                self,
                "emit_file_changed",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, evt.src_path),
            )

        # Safely call _start_batch_timer_async instead of .start() directly
        QMetaObject.invokeMethod(
            self, "start_batch_timer_async", Qt.ConnectionType.QueuedConnection
        )

    @pyqtSlot()
    def start_batch_timer_async(self):
        """Safely starts the batch timer from the main thread."""
        if not self._batch_timer.isActive():
            self._batch_timer.start(500)

    @pyqtSlot(str)
    def emit_file_changed(self, path: str):
        """Wrapper to emit fileChanged in a thread-safe manner"""
        self.fileChanged.emit(path)

    def _emit_batch_changes(self):
        if not self._pending_events:
            return

        logger.info(
            f"FileWatcher emitting batched changes for {len(self._pending_events)} folders."
        )

        for folder_path, events in self._pending_events.items():
            if not events:
                continue

            if len(events) > self.MAX_BATCH_SIZE:
                chunks = [
                    events[i : i + self.MAX_BATCH_SIZE]
                    for i in range(0, len(events), self.MAX_BATCH_SIZE)
                ]
                for chunk in chunks:
                    self._process_cache_removal(chunk)
                    self.fileBatchChanged.emit(folder_path, chunk)
            else:
                self._process_cache_removal(events)
                self.fileBatchChanged.emit(folder_path, events)

        self._pending_events.clear()

    def is_watching_path(self, path: str) -> bool:
        """Check if the given path is currently being watched."""
        norm_path = os.path.normpath(path)
        return norm_path in {os.path.normpath(p) for p in self._watched_paths}

    def _process_cache_removal(self, events: List[FileChangeEvent]):
        if not self._cache:
            return
        for evt in events:
            if evt.event_type == "deleted":
                self._cache.remove_by_path(evt.src_path)

    def _log_stats(self):
        change_rate = self._events_count / 5
        logger.info(
            f"FileWatcher Stats: {len(self._watched_paths)} folders watched, {change_rate:.1f} changes/sec"
        )
        logger.debug(f"FileWatcher Stats list: {self._watched_paths}")
        self.statsUpdated.emit(len(self._watched_paths), change_rate)
        self._events_count = 0  # Reset counter


# --- Watchdog Event Handler ---
class _WatchdogHandler(FileSystemEventHandler):
    VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".ini")

    def __init__(self, service: FileWatcherService):
        super().__init__()
        self._service = service

    def dispatch(self, event: FileSystemEvent):
        if not self._service._active:
            return

        is_folder = event.is_directory
        path = event.src_path

        if not path:
            return

        if not is_folder and not path.lower().endswith(self.VALID_EXTENSIONS):
            # For regular files: filter extensions
            return

        logger.debug(
            f"FileWatcher Event: {event.event_type} -> {path} (folder={is_folder})"
        )

        change_event = None
        if event.event_type == "created":
            change_event = FileChangeEvent("created", event.src_path)
        elif event.event_type == "deleted":
            change_event = FileChangeEvent("deleted", event.src_path)
        elif event.event_type == "moved":
            change_event = FileChangeEvent(
                "moved", event.src_path, getattr(event, "dest_path", None)
            )
        elif event.event_type == "modified":
            change_event = FileChangeEvent("modified", event.src_path)

        if change_event:
            self._service._enqueue_event(change_event)
