# app/viewmodels/mixins/file_watcher_mixin.py

import os
from typing import List, Optional
from PyQt6.QtCore import QTimer
from app.services.file_watcher_service import FileChangeEvent, FileWatcherService
from app.utils.logger_utils import logger
from app.utils.signal_utils import safe_connect

"""
Requires methods/attrs in class:
- self._get_item_list(): List[ItemModelType]
- self._load_items_for_path(path: str)
- self._get_current_path_context(): str
- self._data_loader: DataLoaderService
- self.displayListChanged: pyqtSignal
- self.updateItemDisplay: pyqtSignal
- self.objectItemPathChanged: pyqtSignal
- self.request_thumbnail_for(item)
- self._insert_item_to_ui()
- self._remove_item_from_ui()
- self._suppressed_renames: Set[str]
"""


class FileWatcherMixin:
    """Mixin to handle file watching logic, debounce, and sync with UI."""

    def _init_filewatcher_logic(self):
        """Call in __init__ of the main VM class to initialize timers and sets."""
        self._file_watcher_service: Optional[FileWatcherService] = None
        self._watched_paths: set[str] = set()
        self._pending_refresh_paths: set[str] = set()
        self._refresh_debounce_timer = QTimer(self)
        self._refresh_debounce_timer.setSingleShot(True)
        self._refresh_debounce_timer.setInterval(400)
        self._refresh_debounce_timer.timeout.connect(self._process_pending_refresh)

    def _connect_file_watcher_signals(self):
        if self._file_watcher_service:
            safe_connect(
                self._file_watcher_service.fileBatchChanged,
                self._on_file_batch_changed,
                self,
            )

    def _process_pending_refresh(self):
        """Debounced refresh executor."""
        if not self._pending_refresh_paths:
            return
        paths = list(self._pending_refresh_paths)
        self._pending_refresh_paths.clear()
        self._refresh_items_async(paths)

    def _refresh_items_async(self, paths: list[str]):
        if not paths:
            return
        context = self._get_current_path_context()
        if not context:
            logger.warning(f"{self.__class__.__name__}: No active context path.")
            return

        context = os.path.normpath(context)

        # refresh specific items
        updated = 0
        for p in paths:
            norm_path = os.path.normpath(p)
            item = next(
                (
                    i
                    for i in self._get_item_list()
                    if os.path.normpath(i.path) == norm_path
                ),
                None,
            )
            if item:
                try:
                    self.request_thumbnail_for(item)
                    self.updateItemDisplay.emit(
                        item.path,
                        {
                            "path": item.path,
                            "display_name": item.display_name,
                            "status": item.status,
                        },
                    )
                    updated += 1
                except Exception as e:
                    logger.warning(f"Failed to update display for {item.path}: {e}")

        if updated == 0:
            logger.info(
                f"{self.__class__.__name__}: No matching items, fallback reload."
            )
            self._load_items_for_path(context)
        else:
            logger.info(
                f"{self.__class__.__name__}: Updated {updated} item(s) directly."
            )

    def _on_file_batch_changed(self, folder_path: str, events: List[FileChangeEvent]):
        logger.info(
            f"{self.__class__.__name__}: Batch file change at {folder_path} ({len(events)} events)"
        )
        if self._get_item_type() != "object":
            logger.debug(
                f"{self.__class__.__name__}: Skipping file batch change – not object type."
            )
            return
        context_path = os.path.normpath(self._get_current_path_context() or "")
        if not os.path.commonpath([context_path, folder_path]) == context_path:
            logger.debug(
                f"{self.__class__.__name__}: Skipping batch – outside current context: {folder_path}"
            )
            return
        for evt in events:
            logger.debug(
                f"[{evt.event_type}] src={evt.src_path} → dest={evt.dest_path}"
            )
            if evt.event_type == "moved" and (
                os.path.normpath(evt.src_path) in self._suppressed_renames
                or os.path.normpath(evt.dest_path or "") in self._suppressed_renames
            ):
                logger.debug(
                    f"Ignoring suppressed rename event: {evt.src_path} → {evt.dest_path}"
                )
                continue
            if evt.event_type == "created":
                self._handle_file_created(evt.src_path)
            elif evt.event_type == "deleted":
                self._handle_file_deleted(evt.src_path)
            elif evt.event_type == "moved":
                self._handle_file_rename(evt.src_path, evt.dest_path)
            elif evt.event_type == "modified":
                self._pending_refresh_paths.add(evt.src_path)
        if not self._refresh_debounce_timer.isActive():
            self._refresh_debounce_timer.start()

    def _handle_file_created(self, path: str):
        logger.info(f"{self.__class__.__name__}: File created: {path}")
        loader = self._data_loader
        item_type = self._get_item_type()

        def _cb(result):
            if result:
                self._insert_item_to_ui(result)

        if item_type == "object":
            loader.get_single_object_item_async(path, _cb)
        elif item_type == "folder":
            loader.get_single_folder_item_async(path, _cb)

    def _handle_file_deleted(self, path: str):
        logger.info(f"{self.__class__.__name__}: File deleted: {path}")
        self._remove_item_from_ui(path)

    def _handle_file_rename(self, src_path: str, dest_path: str):
        src_path_norm = os.path.normpath(src_path)
        dest_path_norm = os.path.normpath(dest_path)
        if not os.path.exists(dest_path_norm):
            logger.warning(f"Rename target is not a directory: {dest_path_norm}")
            return
        if src_path_norm == dest_path_norm:
            return

        if dest_path_norm in self._suppressed_renames:
            logger.debug(f"Watcher rename ignored (self): {dest_path_norm}")
            self._suppressed_renames.remove(dest_path_norm)
            return

        item = next(
            (
                i
                for i in self._get_item_list()
                if os.path.normpath(i.path) == src_path_norm
            ),
            None,
        )
        if not item:
            logger.warning(f"Rename target not found in model: {src_path}")
            return

        item.path = dest_path_norm
        item.folder_name = os.path.basename(dest_path_norm)

        from app.core.constants import DISABLED_PREFIX

        item.status = not item.folder_name.lower().startswith(DISABLED_PREFIX.lower())

        # Emit updates
        self.updateItemDisplay.emit(
            src_path_norm,
            {
                "path": dest_path_norm,
                "display_name": item.display_name,
                "status": item.status,
            },
        )

        if self._get_item_type() == "object":
            self.objectItemPathChanged.emit(src_path_norm, dest_path_norm)

        try:
            self.request_thumbnail_for(item)
        except Exception as e:
            logger.warning(f"Failed to refresh thumbnail for {item.path}: {e}")

        # Update watcher path if changed
        if self._file_watcher_service:
            old_parent = os.path.dirname(src_path_norm)
            new_parent = os.path.dirname(dest_path_norm)
            if old_parent != new_parent:
                self._file_watcher_service.remove_path(src_path_norm)
                self._watched_paths.discard(src_path_norm)
                if os.path.exists(dest_path_norm):
                    self._file_watcher_service.add_path(dest_path_norm)
                    self._watched_paths.add(dest_path_norm)

    def clear_refresh_queue(self, stop_only: bool = True):
        """Stop debounce + optionally clear pending queue."""
        self._refresh_debounce_timer.stop()
        if not stop_only:
            self._pending_refresh_paths.clear()
