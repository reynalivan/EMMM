# App/services/file watcher service.py


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
from app.core.constants import VALID_EXTENSIONS, MAX_BATCH_SIZE
from collections import defaultdict
import time


class FileChangeEvent:
    def __init__(self, event_type: str, src_path: str, dest_path: Optional[str] = None):
        self.event_type = event_type
        self.src_path = src_path
        self.dest_path = dest_path


class WatchdogThread(QThread):
    def __init__(self, handler: FileSystemEventHandler):
        super().__init__()
        self._observer = Observer()
        self._handler = handler
        self._running = False
        self._pending_paths = []

    def run(self):
        self._running = True
        self._observer.start()
        while self._running:
            self._schedule_pending_paths()
            self.msleep(200)  # Soft idle

    def stop(self):
        self._running = False
        self._observer.stop()
        self._observer.join()

    def schedule(self, handler, path, recursive=False):
        self._pending_paths.append((handler, path, recursive))

    def unschedule(self, watch):
        self._observer.unschedule(watch)

    def _schedule_pending_paths(self):
        while self._pending_paths:
            handler, path, recursive = self._pending_paths.pop(0)
            if any(
                os.path.normpath(w.path) == os.path.normpath(path)
                for w in self._observer._watches
            ):
                logger.debug(f"Already scheduled, skipping: {path}")
                continue
            try:
                self._observer.schedule(handler, path, recursive=recursive)
            except Exception as e:
                logger.error(f"Failed to schedule path {path}: {e}", exc_info=True)


class FileWatcherService(QObject):
    fileBatchChanged = pyqtSignal(str, list)  # folder_path, list[FileChangeEvent]

    fileChanged = pyqtSignal(str)
    statsUpdated = pyqtSignal(int, float)  # folder_count: int, change_rate: float

    def __init__(
        self, cache: Optional[ImageCache] = None, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._thread: Optional[WatchdogThread] = None
        self._suppressed_paths = set()
        self._handler = _WatchdogHandler(self)
        self._watched_paths: Set[str] = set()
        self._active = False
        self._pending_events: Dict[str, List[FileChangeEvent]] = {}
        self._batch_timer = QTimer()
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._emit_batch_changes)
        self._last_modified_time: dict[str, float] = {}
        self._modified_cooldown_sec = 2.0
        self._cache = cache
        self._events_count = 0
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._log_stats)
        self._suppressed_paths: Set[str] = set()  # Add to suppress rename

    def start(self):
        if self._thread and self._thread.isRunning():
            logger.debug("FileWatcherService thread already running, skipping start.")
            return
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
        if self._active:
            logger.debug("FileWatcherService already enabled, skipping.")
            return
        self._active = True
        logger.info("FileWatcherService ENABLED.")

    def disable(self):
        self._active = False
        logger.info("FileWatcherService DISABLED.")

    def add_path(self, folder_path: str, recursive: bool = False):
        if not self._active:
            logger.debug(
                f"Watcher ignored add_path because service disabled: {folder_path}"
            )
            return
        norm_path = os.path.normpath(folder_path)
        if any(
            os.path.normcase(norm_path) == os.path.normcase(w)
            for w in self._watched_paths
        ):
            logger.debug(f"Path already watched (case-insensitive): {norm_path}")
            return
        if not os.path.isdir(folder_path):
            logger.warning(f"Invalid path given to Watcher: {folder_path}")
            return
        logger.debug(f"Attempting to add path: {norm_path}")
        if norm_path in self._watched_paths:
            logger.debug(f"Path already watched: {norm_path}")
            return
        if self._thread is None:
            self._thread = WatchdogThread(self._handler)
            logger.debug("Watcher thread created.")
        if not self._thread.isRunning():
            self._thread.start()
            logger.info("FileWatcherService thread started.")
        try:
            self._thread.schedule(self._handler, norm_path, recursive=recursive)
            self._watched_paths.add(norm_path)
            logger.info(
                f"add_path: new folder to watch: {norm_path} (recursive={recursive}). Total: {len(self._watched_paths)} folders."
            )
        except Exception as e:
            logger.exception(f"Failed to schedule watcher for {norm_path}: {e}")

    def remove_path(self, folder_path: str):
        if (
            not self._thread
            or not self._thread.isRunning()
            or not self._thread._observer
        ):
            return
        normalized_path = os.path.normpath(folder_path)
        try:
            watch_to_remove = None
            for watch in self._thread._observer._watches:
                if os.path.normpath(watch.path) == normalized_path:
                    watch_to_remove = watch
                    break
            if watch_to_remove:
                self._thread._observer.unschedule(watch_to_remove)
                self._watched_paths.discard(normalized_path)
                logger.info(f"FileWatcherService: Unwatched path {normalized_path}")
                logger.debug(f"Current watched paths: {self._watched_paths}")
            else:
                logger.warning(
                    f"FileWatcherService: Path not found to unwatch: {normalized_path}"
                )
        except Exception as e:
            logger.error(
                f"FileWatcherService: Failed to unwatch {normalized_path}: {e}",
                exc_info=True,
            )

    def clear_watches(self):
        self.stop()

    def suppress_path(self, path: str):
        norm_path = os.path.normpath(path)
        self._suppressed_paths.add(norm_path)
        # Delete the Suppress sign after 1 second

        QTimer.singleShot(1000, lambda: self._suppressed_paths.discard(norm_path))

    def is_suppressed(self, path: str) -> bool:
        return os.path.normpath(path) in self._suppressed_paths

    def _enqueue_event(self, evt: FileChangeEvent):
        # Check whether the event comes from the path that is supplied

        if evt.src_path in self._suppressed_paths or (
            evt.dest_path and evt.dest_path in self._suppressed_paths
        ):
            logger.debug(f"Skip, Suppressed event: {evt.event_type} -> {evt.src_path}")
            return  # Ignore this event
        # Event process as usual if not supposed

        logger.debug(f"Enqueueing event: {evt.event_type} -> {evt.src_path}")
        # Filter based on the depth of the folder to object Context

        if hasattr(self, "_get_item_type") and self._get_item_type() == "object":
            current_context = os.path.normpath(self._get_current_path_context() or "")
            relative_depth = (
                len(os.path.relpath(evt.src_path, current_context).split(os.sep)) - 1
            )
            if relative_depth > 1:  # Only the event process from the level one folder

                logger.debug(f"Ignored event: {evt.src_path} is deeper than level 1")
                return

        # Skip non-allowed file types and unknown folders

        if evt.event_type in {"created", "modified"}:
            is_folder = os.path.isdir(evt.src_path)
            ext = os.path.splitext(evt.src_path)[1].lower()
            if not is_folder and ext not in VALID_EXTENSIONS:
                logger.debug(f"Skipped event: {evt.src_path} not in VALID_EXTENSIONS")
                return

        # Debounce modified

        if evt.event_type == "modified":
            now = time.time()
            last = self._last_modified_time.get(evt.src_path, 0)
            if now - last < self._modified_cooldown_sec:
                logger.debug(f"Modified ignored (cooldown): {evt.src_path}")
                return
            self._last_modified_time[evt.src_path] = now
        folder_path = os.path.dirname(evt.src_path)
        self._pending_events.setdefault(folder_path, []).append(evt)
        self._events_count += 1

        if evt.src_path:
            QMetaObject.invokeMethod(
                self,
                "emit_file_changed",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, evt.src_path),
            )

        QMetaObject.invokeMethod(
            self, "start_batch_timer_async", Qt.ConnectionType.QueuedConnection
        )

    @pyqtSlot()
    def start_batch_timer_async(self):
        logger.debug("start_batch_timer_async() called")
        if not self._batch_timer.isActive():
            self._batch_timer.start(500)
            logger.debug("Batch timer started")
        else:
            logger.debug("Batch timer already active")

    @pyqtSlot(str)
    def emit_file_changed(self, path: str):
        self.fileChanged.emit(path)

    def _emit_batch_changes(self):
        if not self._pending_events:
            logger.debug("No pending events to emit.")
            return
        logger.info(
            f"FileWatcher emitting batched changes for {len(self._pending_events)} folders."
        )
        for folder_path, events in self._pending_events.items():
            logger.info(f"Emitting {len(events)} events for folder: {folder_path}")
            if not events:
                continue
            if len(events) > MAX_BATCH_SIZE:
                chunks = [
                    events[i : i + MAX_BATCH_SIZE]
                    for i in range(0, len(events), MAX_BATCH_SIZE)
                ]
                for chunk in chunks:
                    self._process_cache_removal(chunk)
                    self.fileBatchChanged.emit(folder_path, chunk)
            else:
                self._process_cache_removal(events)
                self.fileBatchChanged.emit(folder_path, events)
        self._pending_events.clear()

    def is_watching_path(self, path: str) -> bool:
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
        self._events_count = 0


class _WatchdogHandler(FileSystemEventHandler):
    def __init__(self, service: FileWatcherService):
        super().__init__()
        self._service = service

    def dispatch(self, event: FileSystemEvent):
        logger.debug(f"Dispatching event: {event.event_type} - {event.src_path}")
        if not self._service._active:
            logger.debug("Skipping dispatch: service not active")
            return
        is_folder = event.is_directory
        path = event.src_path
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if (
            event.event_type != "deleted"
            and not is_folder
            and ext not in VALID_EXTENSIONS
        ):
            logger.debug(
                f"Skipped event (filtered): {event.event_type} - {path} (ext={ext}, is_folder={is_folder})"
            )
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
