# app/services/thumbnail_service.py

from typing import Literal
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from app.utils.image_cache import ImageCache
from app.utils.image_utils import ImageUtils
from app.utils.logger_utils import logger
from app.utils.async_utils import Worker, run_in_background
from app.core import constants
from typing import Optional
import os
import glob
import hashlib
from collections import deque

MAX_CONCURRENT = 4


class ThumbnailService(QObject):
    thumbnailReady = pyqtSignal(str, dict)
    previewThumbnailsFound = pyqtSignal(str, list)

    def __init__(
        self,
        image_cache: ImageCache,
        image_utils: ImageUtils,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        logger.debug("ThumbnailService initialized.")
        self._cache = image_cache
        self._utils = image_utils
        self._setup_cache_clean_timer()
        self._thumbnail_cache: dict[str, dict] = {}
        self._thumbnail_request_queue = deque()
        self._requested_paths = set()
        self._active_thumbnail_tasks = set()

        self._thumbnail_queue_timer = QTimer(self)
        self._thumbnail_queue_timer.setInterval(50)  # 20fps
        self._thumbnail_queue_timer.timeout.connect(self._process_thumbnail_queue)
        self._thumbnail_queue_timer.start()

    def get_thumbnail_async(
        self, item_path: str, item_type: Literal["object", "folder"]
    ):
        """
        logger.debug(
            f"Requesting thumbnail async for '{item_path}' (type: {item_type})"
        )
        """

        normalized_path = os.path.normpath(item_path)
        cache_key = self._generate_cache_key(normalized_path, item_type)

        # Optimasi: Check cache dulu, kalau ada emit langsung tanpa worker
        cached_path = self._cache.get(cache_key)
        if cached_path and os.path.exists(cached_path):
            logger.debug(
                f"ThumbnailService: Immediate cache hit for '{normalized_path}'"
            )
            self.thumbnailReady.emit(
                normalized_path,
                {"path": cached_path, "status": "hit", "error_msg": None},
            )
            return  # Skip spawn worker

        # Kalau tidak ada, baru async worker
        def _handle_result(result_dict):
            if not os.path.exists(normalized_path):
                logger.warning(
                    f"ThumbnailService: Path disappeared before result: {normalized_path}"
                )
                return
            self.thumbnailReady.emit(normalized_path, result_dict)

        def _handle_error(error_info):
            if not os.path.exists(normalized_path):
                logger.warning(
                    f"ThumbnailService: Path disappeared before error result: {normalized_path}"
                )
                return
            self._handle_thumbnail_error(normalized_path, error_info)

        worker = run_in_background(self._get_thumbnail_task, normalized_path, item_type)
        worker.signals.result.connect(_handle_result)
        worker.signals.error.connect(_handle_error)

    def request_thumbnail(self, item_path: str, item_type: Literal["object", "folder"]):
        normalized_path = os.path.normpath(item_path)
        key = f"{item_type}:{normalized_path}"

        # skip if already requested
        if key in self._requested_paths or key in self._active_thumbnail_tasks:
            return

        # Add to queue
        self._requested_paths.add(key)
        self._thumbnail_request_queue.append((normalized_path, item_type))

    def _process_thumbnail_queue(self):
        if not self._thumbnail_request_queue:
            return

        while (
            self._thumbnail_request_queue
            and len(self._active_thumbnail_tasks) < MAX_CONCURRENT
        ):
            item_path, item_type = self._thumbnail_request_queue.popleft()
            key = f"{item_type}:{item_path}"
            self._active_thumbnail_tasks.add(key)

            def _on_result(result_dict, p=item_path, t=item_type):
                k = f"{t}:{p}"
                self._active_thumbnail_tasks.discard(k)
                self.thumbnailReady.emit(p, result_dict)

            def _on_error(error_info, p=item_path, t=item_type):
                k = f"{t}:{p}"
                self._active_thumbnail_tasks.discard(k)
                self._handle_thumbnail_error(p, error_info)

            worker = run_in_background(self._get_thumbnail_task, item_path, item_type)
            worker.signals.result.connect(_on_result)
            worker.signals.error.connect(_on_error)

    def reset_thumbnail_queue(self):
        self._thumbnail_request_queue.clear()
        self._requested_paths.clear()
        self._active_thumbnail_tasks.clear()

    def _generate_cache_key(self, item_path: str, item_type: str) -> str:
        """Generate cache key that survives folder renames, including file size."""

        try:
            # Cari source thumbnail file
            source_image = self._find_object_thumbnail_source(item_path)

            if source_image and os.path.exists(source_image):
                mtime = int(os.path.getmtime(source_image))
                size = os.path.getsize(source_image)
                basename = os.path.basename(source_image)
                raw_key = f"{item_type}:{basename}:{mtime}:{size}"
            else:
                # Kalau thumbnail tidak ada, fallback pakai nama folder saja
                clean_base = os.path.basename(item_path)
                raw_key = f"{item_type}:{clean_base}"

            sha1 = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()
            return sha1

        except Exception as e:
            logger.error(
                f"ThumbnailService: Error generating cache key: {e}", exc_info=True
            )
            # Super fallback: hash dari path saja
            return hashlib.sha1(item_path.encode("utf-8")).hexdigest()

    def find_preview_thumbnails_async(self, folder_path: str):
        logger.debug(f"Requesting preview thumbnails async for '{folder_path}'")
        worker = run_in_background(self._scan_preview_thumbnails_task, folder_path)
        worker.signals.result.connect(
            lambda paths, p=folder_path: self.previewThumbnailsFound.emit(p, paths)
        )
        worker.signals.error.connect(
            lambda error_info, p=folder_path: self._handle_scan_error(p, error_info)
        )

    def _get_thumbnail_task(
        self, item_path: str, item_type: Literal["object", "folder"]
    ) -> dict:
        cache_key = self._generate_cache_key(item_path, item_type)
        # logger.debug(f"Cache key for {item_path}: {cache_key}")

        cached_path = self._cache.get(cache_key)
        if cached_path and os.path.exists(cached_path):
            logger.debug(f"Cache hit for '{item_path}' -> {cached_path}")
            return {"path": cached_path, "status": "hit", "error_msg": None}

        # logger.debug(f"Cache miss for '{item_path}'. Finding source image...")
        source_image_path = None
        try:
            if item_type == "object":
                source_image_path = self._find_object_thumbnail_source(item_path)
            elif item_type == "folder":
                preview_paths = self._find_preview_thumbnail_sources(item_path)
                if preview_paths:
                    source_image_path = preview_paths[0]
        except Exception as e:
            logger.warning(f"Error finding source image for '{item_path}': {e}")
            return {
                "path": None,
                "status": "error",
                "error_msg": f"Finding source failed: {e}",
            }

        if not source_image_path:
            # logger.debug(f"No source image found for '{item_path}'.")
            return {
                "path": None,
                "status": "fallback",
                "error_msg": "Source image not found",
            }

        logger.debug(
            f"Source image found: '{source_image_path}'. Generating thumbnail..."
        )
        try:
            target_size = (
                constants.DEFAULT_THUMB_SIZE_W,
                constants.DEFAULT_THUMB_SIZE_H,
            )
            thumbnail_bytes = self._utils.create_thumbnail(
                source_image_path, target_size
            )

            if not thumbnail_bytes:
                logger.error(
                    f"Thumbnail generation returned None for '{source_image_path}'."
                )
                return {
                    "path": None,
                    "status": "error",
                    "error_msg": "Generation failed (returned None)",
                }

            cached_path_after_put = self._cache.put(cache_key, thumbnail_bytes)
            if cached_path_after_put:
                logger.debug(
                    f"Generated and cached thumbnail for '{item_path}' at '{cached_path_after_put}'."
                )
                return {
                    "path": cached_path_after_put,
                    "status": "generated",
                    "error_msg": None,
                }
            else:
                logger.error(
                    f"Failed to put generated thumbnail into cache for '{item_path}'."
                )
                return {
                    "path": None,
                    "status": "error",
                    "error_msg": "Cache put failed",
                }

        except Exception as e:
            logger.error(
                f"Error during thumbnail generation/caching for '{item_path}': {e}",
                exc_info=True,
            )
            return {
                "path": None,
                "status": "error",
                "error_msg": f"Generation/Cache error: {e}",
            }

    def _scan_preview_thumbnails_task(self, folder_path: str) -> list[str]:
        logger.debug(f"Scanning preview thumbnails task started for {folder_path}")
        try:
            paths = self._find_preview_thumbnail_sources(folder_path)
            logger.debug(
                f"Scan task found {len(paths)} preview paths for {folder_path}"
            )
            return paths
        except Exception as e:
            logger.warning(
                f"Preview thumbnail scan task error for {folder_path}: {e}",
                exc_info=True,
            )
            raise e

    def _find_object_thumbnail_source(self, folder_path: str) -> Optional[str]:
        try:
            suffix = constants.THUMBNAIL_OBJECT_SUFFIX
            extensions = constants.SUPPORTED_THUMB_EXTENSIONS
            all_found_files = []

            for ext in extensions:
                pattern_glob = os.path.join(folder_path, f"*{suffix}.{ext}")
                matches = glob.glob(pattern_glob)
                all_found_files.extend(matches)

            if not all_found_files:
                """logger.debug(
                    f"No files found matching pattern *{suffix}.<ext> in {folder_path}"
                )"""
                return None

            preferred_order = [".png", ".jpg", ".jpeg", ".webp", ".gif"]

            for pref_ext in preferred_order:
                for file_path in all_found_files:
                    if file_path.lower().endswith(pref_ext):
                        #   logger.debug(
                        #       f"Prioritized thumbnail source found ({pref_ext}): {file_path}"
                        #   )
                        return file_path

            logger.warning(
                f"No preferred extension match in {all_found_files}, returning first found: {all_found_files[0]}"
            )
            return all_found_files[0]

        except AttributeError as e:
            logger.error(
                f"AttributeError accessing constants in _find_object_thumbnail_source: {e}."
            )
            return None
        except Exception as e:
            logger.error(
                f"Error finding object thumbnail source in {folder_path}: {e}",
                exc_info=True,
            )
            return None

    def _find_preview_thumbnail_sources(self, folder_path: str) -> list[str]:
        result = []
        try:
            prefix = constants.THUMBNAIL_FOLDER_PREFIX
            extensions = constants.SUPPORTED_THUMB_EXTENSIONS

            # 1. Cari preview*.jpg/png di root
            for ext in extensions:
                pattern = os.path.join(folder_path, f"{prefix}*.{ext}")
                matches = glob.glob(pattern)
                result.extend(matches)

            if result:
                logger.debug(
                    f"Found {len(result)} specific preview(s) in {folder_path}"
                )
                return sorted(result)[:12]  # Sort + limit 12

            logger.debug(f"No preview* files found, fallback to recursive image scan.")

            # 2. Recursive fallback, max 4 levels
            fallback_files = []
            for root, dirs, files in os.walk(folder_path):
                level = root.replace(folder_path, "").count(os.sep)
                if level > 4:
                    continue

                for file in files:
                    if file.lower().endswith(extensions):
                        fallback_files.append(os.path.join(root, file))

            # Sort by filename, limit to 12
            fallback_files = sorted(fallback_files)[:12]
            logger.debug(
                f"Found {len(fallback_files)} fallback image(s) in {folder_path}"
            )
            return fallback_files

        except Exception as e:
            logger.error(
                f"Error finding preview thumbnails in {folder_path}: {e}", exc_info=True
            )
            return []

    def _handle_thumbnail_error(self, item_path: str, error_info: tuple):
        exctype, value, tb_str = error_info
        logger.error(f"Worker error getting thumbnail for '{item_path}': {value}")
        self.thumbnailReady.emit(
            item_path, {"path": None, "status": "error", "error_msg": str(value)}
        )

    def _handle_scan_error(self, item_path: str, error_info: tuple):
        exctype, value, tb_str = error_info
        logger.error(f"Worker error scanning previews for '{item_path}': {value}")
        self.previewThumbnailsFound.emit(item_path, [])

    def _setup_cache_clean_timer(self):
        """Setup a timer to clean expired cache periodically."""
        self._cache_clean_timer = QTimer(self)
        self._cache_clean_timer.timeout.connect(self._cache.clean_expired)

        # Set interval 24 hours
        interval_ms = 24 * 60 * 60 * 1000  # 24 hours
        self._cache_clean_timer.start(interval_ms)

        logger.info(
            "ThumbnailService: Scheduled periodic cache cleaning every 24 hours."
        )

    def get_cached_thumbnail(self, item_path: str, item_type: str) -> dict | None:
        """Returns cached thumbnail result if available."""
        normalized_path = os.path.normpath(item_path)
        cache_key = self._generate_cache_key(normalized_path, item_type)

        cached_path = self._cache.get(cache_key)
        if cached_path and os.path.exists(cached_path):
            return {"path": cached_path, "status": "hit", "error_msg": None}
        return None
