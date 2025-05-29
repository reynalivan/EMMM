# app/services/thumbnail_service.py

import os
import glob
import hashlib
import time
import io
from typing import Literal, Optional, Tuple, Union
from collections import deque, OrderedDict

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap, QGuiApplication
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from PIL import Image, ImageSequence

from app.utils.logger_utils import logger
from app.utils.async_utils import Worker, run_in_background
from app.core import constants

MAX_CONCURRENT = 4
ImageSource = Union[str, bytes]


class _ImageCache:
    """
    Internal image cache handler for thumbnails.
    """

    def __init__(
        self,
        cache_dir: str = constants.CACHE_DIR,
        max_size_mb: int = constants.DEFAULT_CACHE_MAX_MB,
        expiry_days: int = constants.DEFAULT_CACHE_EXPIRY_DAYS,
    ):
        """Initializes the cache, creates cache directory if needed."""
        self._cache_dir = os.path.abspath(cache_dir)
        self._max_size_bytes = max_size_mb * 1024 * 1024 if max_size_mb > 0 else 0
        self._expiry_seconds = expiry_days * 24 * 60 * 60 if expiry_days > 0 else 0

        try:
            os.makedirs(self._cache_dir, exist_ok=True)
            logger.info(f"Image cache directory initialized at: {self._cache_dir}")
        except OSError as e:
            logger.critical(
                f"FATAL: Failed to create cache directory '{self._cache_dir}': {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Cannot create cache directory: {self._cache_dir}"
            ) from e

    def _get_cache_filepath(self, key: str) -> str:
        """Generates a unique and safe file path within the cache directory from a key."""
        hashed_key = hashlib.sha1(key.encode("utf-8")).hexdigest()
        filename = f"{hashed_key}.png"
        return os.path.join(self._cache_dir, filename)

    def put(self, key: str, data: bytes) -> Optional[str]:
        """Saves data bytes to a file in the cache directory using the generated key."""
        file_path = self._get_cache_filepath(key)
        logger.debug(
            f"Caching data for key '{key}' to '{file_path}' ({len(data)} bytes)"
        )
        try:
            with open(file_path, "wb") as f:
                f.write(data)
            logger.info(f"Successfully cached: '{key}' -> '{file_path}'")
            self._manage_cache()
            return file_path
        except (IOError, OSError) as e:
            logger.error(
                f"Failed to write cache file '{file_path}' for key '{key}': {e}",
                exc_info=True,
            )
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            return None

    def get(self, key: str) -> Optional[str]:
        """Gets the file path for a cached item if it exists and is valid."""
        file_path = self._get_cache_filepath(key)

        if not os.path.isfile(file_path):
            return None

        if self._expiry_seconds > 0:
            try:
                file_mod_time = os.path.getmtime(file_path)
                if time.time() - file_mod_time > self._expiry_seconds:
                    try:
                        os.remove(file_path)
                        logger.debug(f"Expired cache file removed: {file_path}")
                    except OSError:
                        pass
                    return None
            except OSError as e:
                logger.warning(f"Error checking cache file expiry: {e}")
                return None

        return file_path

    def remove(self, key: str) -> bool:
        """Removes a specific item from the cache by key."""
        file_path = self._get_cache_filepath(key)
        logger.debug(f"Attempting to remove cache file: {file_path}")
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Successfully removed cache file: {file_path}")
                return True
            except OSError as e:
                logger.error(f"Failed to remove cache file '{file_path}': {e}")
                return False
        return False

    def clear(self) -> bool:
        """Removes all files within the cache directory."""
        logger.warning(f"Clearing ALL files from cache directory: {self._cache_dir}")
        if not os.path.isdir(self._cache_dir):
            logger.warning("Cache directory does not exist, nothing to clear.")
            return True

        success = True
        for filename in os.listdir(self._cache_dir):
            file_path = os.path.join(self._cache_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed cache file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove cache file '{file_path}': {e}")
                success = False
        logger.info("Cache clear operation finished.")
        return success

    def _manage_cache(self) -> None:
        """Manage cache size: remove oldest files if exceeding max size."""
        if self._max_size_bytes <= 0:
            return

        try:
            total_size = 0
            file_infos = []

            for filename in os.listdir(self._cache_dir):
                filepath = os.path.join(self._cache_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    filesize = stat.st_size
                    mtime = stat.st_mtime
                    total_size += filesize
                    file_infos.append((filepath, mtime, filesize))

            if total_size <= self._max_size_bytes:
                return

            logger.warning(
                f"Image cache size {total_size} exceeds limit {self._max_size_bytes}, cleaning up..."
            )

            file_infos.sort(key=lambda x: x[1])

            for filepath, _, filesize in file_infos:
                try:
                    os.remove(filepath)
                    total_size -= filesize
                    logger.debug(f"Removed old cache file: {filepath}")
                    if total_size <= self._max_size_bytes:
                        break
                except OSError as e:
                    logger.error(f"Failed to remove old cache file '{filepath}': {e}")

        except Exception as e:
            logger.error(f"Error managing cache size: {e}", exc_info=True)

    def clean_expired(self) -> None:
        """Remove cache files that are expired based on modification time."""
        if self._expiry_seconds <= 0:
            return

        try:
            now = time.time()
            expired_files = []

            for filename in os.listdir(self._cache_dir):
                filepath = os.path.join(self._cache_dir, filename)
                if os.path.isfile(filepath):
                    try:
                        mtime = os.path.getmtime(filepath)
                        if now - mtime > self._expiry_seconds:
                            expired_files.append(filepath)
                    except OSError:
                        continue

            for filepath in expired_files:
                try:
                    os.remove(filepath)
                    logger.debug(f"Removed expired cache file: {filepath}")
                except OSError as e:
                    logger.error(
                        f"Failed to remove expired cache file '{filepath}': {e}"
                    )

            if expired_files:
                logger.info(
                    f"Expired cache clean complete. Deleted {len(expired_files)} files."
                )

        except Exception as e:
            logger.error(f"Error during expired cache cleaning: {e}", exc_info=True)


class _ImageUtils:
    """
    Internal image utilities for thumbnail creation.
    """

    @staticmethod
    def create_thumbnail(
        source: ImageSource,
        target_size: Tuple[int, int] = (
            constants.DEFAULT_THUMB_SIZE_W,
            constants.DEFAULT_THUMB_SIZE_H,
        ),
        quality: int = 85,
        output_format: str = "PNG",
    ) -> Union[bytes, None]:
        """Creates a thumbnail from an image file path or bytes using Pillow."""
        if Image is None:
            logger.critical("Pillow library is required but not installed.")
            return None

        img = None
        final_format = output_format.upper()

        try:
            # Load Image
            if isinstance(source, str):
                if not os.path.exists(source):
                    logger.error(f"Thumbnail source file not found: {source}")
                    return None
                try:
                    img = Image.open(source)
                    logger.debug(
                        f"Loaded image from path: {source} (Format: {img.format}, Mode: {img.mode})"
                    )
                except Exception as load_err:
                    logger.error(f"Failed to load image from path {source}: {load_err}")
                    return None
            elif isinstance(source, bytes):
                try:
                    img = Image.open(io.BytesIO(source))
                    img.load()
                    logger.debug(
                        f"Loaded image from bytes (Format: {img.format}, Mode: {img.mode})"
                    )
                except Exception as load_err:
                    logger.error(f"Failed to load image from bytes: {load_err}")
                    return None
            else:
                logger.error(f"Invalid thumbnail source type provided: {type(source)}")
                return None

            # Handle Mode & Transparency
            has_transparency = False
            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                has_transparency = True

            if has_transparency:
                logger.debug(
                    f"Transparency detected (mode={img.mode}). Ensuring output is PNG."
                )
                final_format = "PNG"
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
            elif img.mode != "RGB":
                logger.debug(f"Converting image mode '{img.mode}' to 'RGB'.")
                img = img.convert("RGB")

            if final_format not in Image.SAVE:
                logger.warning(
                    f"Output format '{final_format}' not supported by Pillow. Defaulting to PNG."
                )
                final_format = "PNG"

            # Resize using thumbnail() - Preserves aspect ratio
            original_size = img.size
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            logger.debug(
                f"Image resized from {original_size} to {img.size} (target <= {target_size})"
            )

            # Save to BytesIO stream
            byte_stream = io.BytesIO()
            save_params = {"format": final_format}

            if final_format == "JPEG":
                save_params["quality"] = quality
                save_params["optimize"] = True
                if img.mode == "RGBA":
                    logger.debug("Converting RGBA to RGB before saving as JPEG.")
                    img = img.convert("RGB")
            elif final_format == "PNG":
                save_params["optimize"] = True
            elif final_format == "WEBP":
                save_params["quality"] = quality
                save_params["lossless"] = not has_transparency

            logger.debug(
                f"Saving thumbnail to BytesIO stream as {final_format} with params: {save_params}"
            )
            img.save(byte_stream, **save_params)

            thumbnail_bytes = byte_stream.getvalue()
            logger.debug(
                f"Thumbnail created ({len(thumbnail_bytes)} bytes, Format: {final_format})."
            )
            return thumbnail_bytes

        except Exception as e:
            logger.error(f"Unexpected error creating thumbnail: {e}", exc_info=True)
            return None
        finally:
            if img:
                img.close()

    @staticmethod
    def get_image_from_clipboard() -> Optional[QImage]:
        """Retrieves an image from the system clipboard."""
        try:
            clipboard = QGuiApplication.clipboard()
            image = clipboard.image()
            if not image.isNull():
                return image
        except Exception as e:
            logger.error(f"Error getting image from clipboard: {e}")
        return None

    @staticmethod
    def qimage_to_bytes(
        image: QImage, format: str = "JPEG", quality: int = 90
    ) -> Optional[bytes]:
        """Converts a QImage object to bytes in the specified format."""
        try:
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)

            success = image.save(buffer, format.upper(), quality)
            buffer.close()

            if success:
                return byte_array.data()
        except Exception as e:
            logger.error(f"Error converting QImage to bytes: {e}")
        return None

    @staticmethod
    def validate_image_data(data: bytes) -> bool:
        """Basic validation to check if byte data represents a known image format."""
        try:
            image = QImage()
            return image.loadFromData(data)
        except Exception:
            return False


class ThumbnailService(QObject):
    thumbnailReady = pyqtSignal(str, dict)
    previewThumbnailsFound = pyqtSignal(str, list)

    def __init__(
        self,
        parent: QObject | None = None,
        cache_dir: str = constants.CACHE_DIR,
        max_size_mb: int = constants.DEFAULT_CACHE_MAX_MB,
        expiry_days: int = constants.DEFAULT_CACHE_EXPIRY_DAYS,
    ):
        super().__init__(parent)
        logger.debug("ThumbnailService initialized.")

        # Initialize internal cache and utils
        self._cache = _ImageCache(cache_dir, max_size_mb, expiry_days)
        self._utils = _ImageUtils()

        self._setup_cache_clean_timer()
        self._thumbnail_cache: dict[str, dict] = {}
        self._thumbnail_request_queue = deque()
        self._requested_paths = set()
        self._active_thumbnail_tasks = set()
        self._thumbnail_sent_cache: OrderedDict[str, None] = OrderedDict()
        self._MAX_SENT_CACHE = 500  # max thumbnail emit history

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
            if not self._is_recently_sent(cache_key):
                self._mark_sent(cache_key)
                self.thumbnailReady.emit(
                    normalized_path,
                    {"path": cached_path, "status": "hit", "error_msg": None},
                )
            return

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

        # --- ThumbnailService.request_thumbnail (tambah di awal) ---
        if self._is_recently_sent(key):
            cached = self.get_cached_thumbnail(normalized_path, item_type)
            if cached:  # kirim lagi ke UI
                self.thumbnailReady.emit(normalized_path, cached)
            return  # selesai, tanpa antre worker

        if key in self._requested_paths or key in self._active_thumbnail_tasks:
            return

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
                self._mark_sent(k)
                self.thumbnailReady.emit(p, result_dict)

            def _on_error(error_info, p=item_path, t=item_type):
                k = f"{t}:{p}"
                self._active_thumbnail_tasks.discard(k)
                self._handle_thumbnail_error(p, error_info)

            worker = run_in_background(self._get_thumbnail_task, item_path, item_type)
            worker.signals.result.connect(_on_result)
            worker.signals.error.connect(_on_error)

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

    def _is_recently_sent(self, key: str) -> bool:
        return key in self._thumbnail_sent_cache

    def _mark_sent(self, key: str):
        self._thumbnail_sent_cache[key] = None
        self._thumbnail_sent_cache.move_to_end(key)
        if len(self._thumbnail_sent_cache) > self._MAX_SENT_CACHE:
            self._thumbnail_sent_cache.popitem(last=False)
