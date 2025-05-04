# app/services/data_loader_service.py

import os
import json
from typing import Set
from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool
from app.models.object_item_model import ObjectItemModel
from app.core.constants import PROPERTIES_FILENAME, DISABLED_PREFIX
from app.utils.logger_utils import logger
from app.utils.async_utils import Worker, run_in_background
from app.models.folder_item_model import FolderItemModel
from app.core.constants import INFO_FILENAME

CHUNK_SIZE = 10


class DataLoaderService(QObject):
    objectItemsReady = pyqtSignal(str, list)  # game_path, list[ObjectItemModel]
    folderItemsReady = pyqtSignal(str, list)  # parent_path, list[FolderItemModel]
    iniFilesReady = pyqtSignal(str, list)
    errorOccurred = pyqtSignal(str, str)  # operation_name, message
    objectItemChunkReady = pyqtSignal(str, object)
    folderItemChunkReady = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("DataLoaderService initialized.")
        self._in_progress_paths: Set[str] = set()

    def get_object_items_async(self, game_path: str) -> None:
        """Asynchronously loads ObjectItemModels for the given game path."""
        if game_path in self._in_progress_paths:
            return
        self._in_progress_paths.add(game_path)
        logger.debug(f"Requesting object items async for: {game_path}")
        worker = Worker(self._load_object_items_task, game_path)
        # Connect signals correctly

        # --- Start Modification: Fix error signal connection ---
        # worker.signals.error.connect(
        #    lambda items, gp=game_path: self.objectItemsReady.emit(gp, items)) # Incorrect: Error should not emit Ready signal
        worker.signals.error.connect(
            lambda err_info, gp=game_path: self.errorOccurred.emit(
                f"Object Loader ({os.path.basename(gp)})", str(err_info[1])
            )
        )
        worker.signals.finished.connect(
            lambda: self._in_progress_paths.discard(game_path)
        )
        # --- End Modification ---
        QThreadPool.globalInstance().start(worker)

    def _load_object_items_task(self, game_path: str) -> list[ObjectItemModel]:
        result = []
        chunk = []
        BATCH_SIZE = 10

        if not os.path.isdir(game_path):
            raise FileNotFoundError(f"Invalid directory: {game_path}")

        for folder_name in os.listdir(game_path):
            folder_path = os.path.join(game_path, folder_name)
            if not os.path.isdir(folder_path):
                continue
            try:
                props = self._read_json_safe(
                    os.path.join(folder_path, PROPERTIES_FILENAME)
                )
                status = not folder_name.lower().startswith(DISABLED_PREFIX.lower())
                model = ObjectItemModel(
                    path=folder_path,
                    folder_name=folder_name,
                    properties=props,
                    status=status,
                )
                logger.debug(f"Loaded object: {folder_name}")
                chunk.append(model)
                if len(chunk) >= BATCH_SIZE:
                    for obj in chunk:
                        self.objectItemChunkReady.emit(game_path, obj)
                    result.extend(chunk)
                    chunk.clear()
            except Exception as e:
                logger.warning(f"Failed to load object: {folder_name}, {e}")
                continue

        if chunk:
            for obj in chunk:
                self.objectItemChunkReady.emit(game_path, obj)
            result.extend(chunk)

        return result

    # --- Folder Item Loading ---
    def get_folder_items_async(self, parent_path: str) -> None:
        """Asynchronously loads FolderItemModels for the given parent path."""
        logger.debug(f"Requesting folder items async for: {parent_path}")
        worker = Worker(self._load_folder_items_task, parent_path)
        worker.signals.result.connect(
            lambda items, path=parent_path: self.folderItemsReady.emit(path, items)
        )
        worker.signals.error.connect(
            lambda err_info, p=parent_path: self.errorOccurred.emit(
                f"Folder Loader ({os.path.basename(p)})", str(err_info[1])
            )
        )
        QThreadPool.globalInstance().start(worker)

    def _load_folder_items_task(self, parent_path: str) -> list[FolderItemModel]:
        items: list[FolderItemModel] = []
        if not os.path.isdir(parent_path):
            raise FileNotFoundError(parent_path)

        for name in os.listdir(parent_path):
            abs_path = os.path.join(parent_path, name)
            if not os.path.isdir(abs_path):
                continue
            info = self._read_json_safe(os.path.join(abs_path, INFO_FILENAME))
            is_disabled = name.lower().startswith(DISABLED_PREFIX.lower())
            items.append(
                FolderItemModel(
                    path=abs_path,
                    folder_name=name,
                    info=info,
                    status=not is_disabled,
                )
            )

        # ➜ ***sort sekali di thread worker***  —> tidak ada resort di UI
        items.sort(key=lambda m: (not m.status, m.display_name.lower()))

        # streaming : emit model per-item (tetap di urutan ter-sort)
        for it in items:
            self.folderItemChunkReady.emit(parent_path, it)

        return items

    # --- INI File Loading ---
    def get_ini_files_async(self, parent_path: str) -> None:
        """Asynchronously gets a list of .ini file paths within the given parent path."""
        logger.debug(f"Requesting INI files async for: {parent_path}")
        worker = Worker(self._load_ini_files_task, parent_path)
        # --- Start Modification: Connect to iniFilesReady ---
        # Original incorrect connection emitted folderItemsReady
        worker.signals.result.connect(
            lambda ini_files, path=parent_path: self.iniFilesReady.emit(path, ini_files)
        )
        # --- End Modification ---
        worker.signals.error.connect(
            lambda err_info, p=parent_path: self.errorOccurred.emit(
                f"INI Loader ({os.path.basename(p)})", str(err_info[1])
            )
        )
        QThreadPool.globalInstance().start(worker)

    def _load_ini_files_task(self, parent_path: str) -> list[str]:
        """Background task to find .ini files (non-recursive). Returns list of paths."""
        # --- Start Modification: Return list[str] ---
        ini_files: list[str] = []
        logger.debug(f"Task: Loading INI files from {parent_path}")
        if not os.path.exists(parent_path) or not os.path.isdir(parent_path):
            logger.error(
                f"Task: INI files path not found or not a directory: {parent_path}"
            )
            raise FileNotFoundError(f"Invalid parent path: {parent_path}")

        try:
            for name in os.listdir(parent_path):
                # Check if it's a file and ends with .ini (case-insensitive)
                if name.lower().endswith(".ini"):
                    abs_path = os.path.join(parent_path, name)
                    if os.path.isfile(abs_path):
                        ini_files.append(abs_path)  # Append the full path
        except Exception as e:
            logger.error(
                f"Task: Error listing INI files in {parent_path}: {e}", exc_info=True
            )
            # Raise error to be caught by worker
            raise e

        logger.debug(f"Task: Found {len(ini_files)} INI files in {parent_path}")
        return sorted(ini_files)  # Return sorted list of paths
        # --- End Modification ---

    # --- Helper Methods ---
    def _read_json_safe(self, file_path: str) -> dict | None:
        """Safely reads and parses a JSON file."""
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read or parse JSON: {file_path} - {e}")
            return None

    def get_single_object_item_async(
        self, folder_path: str, callback: callable
    ) -> None:
        """Loads a single ObjectItemModel asynchronously for the given folder path."""
        logger.debug(f"Requesting single object item for: {folder_path}")

        worker = Worker(self._load_single_object_item_task, folder_path)
        worker.signals.result.connect(callback)
        worker.signals.error.connect(
            lambda err_info: self.errorOccurred.emit(
                f"Object Item Loader ({os.path.basename(folder_path)})",
                str(err_info[1]),
            )
        )
        QThreadPool.globalInstance().start(worker)

    def _load_single_object_item_task(self, folder_path: str) -> ObjectItemModel | None:
        """Background task to load one object item."""
        if not os.path.isdir(folder_path):
            logger.warning(f"Invalid folder (not directory): {folder_path}")
            return None

        folder_name = os.path.basename(folder_path)
        properties_path = os.path.join(folder_path, PROPERTIES_FILENAME)
        properties = self._read_json_safe(properties_path)

        status = not folder_name.lower().startswith(DISABLED_PREFIX.lower())
        return ObjectItemModel(
            path=folder_path,
            folder_name=folder_name,
            properties=properties,
            status=status,
        )

    def get_single_folder_item_async(
        self, folder_path: str, callback: callable
    ) -> None:
        """Loads a single FolderItemModel asynchronously for the given folder path."""
        logger.debug(f"Requesting single folder item for: {folder_path}")

        worker = Worker(self._load_single_folder_item_task, folder_path)
        worker.signals.result.connect(callback)
        worker.signals.error.connect(
            lambda err_info: self.errorOccurred.emit(
                f"Folder Item Loader ({os.path.basename(folder_path)})",
                str(err_info[1]),
            )
        )
        QThreadPool.globalInstance().start(worker)

    def _load_single_folder_item_task(self, folder_path: str) -> FolderItemModel | None:
        """Background task to load one folder item."""
        if not os.path.isdir(folder_path):
            logger.warning(f"Invalid folder (not directory): {folder_path}")
            return None

        folder_name = os.path.basename(folder_path)
        info_path = os.path.join(folder_path, INFO_FILENAME)
        info = self._read_json_safe(info_path)

        status = not folder_name.lower().startswith(DISABLED_PREFIX.lower())
        return FolderItemModel(
            path=folder_path, folder_name=folder_name, info=info, status=status
        )
