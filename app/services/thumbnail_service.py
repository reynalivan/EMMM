# app/services/thumbnail_service.py

from typing import Literal
from PyQt6.QtCore import QObject, pyqtSignal
from app.utils.image_cache import ImageCache
from app.utils.image_utils import ImageUtils
from app.utils.logger_utils import logger
from app.utils.async_utils import Worker, run_in_background
from app.core import constants
import os
import glob


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
        self._cache = image_cache
        self._utils = image_utils
        logger.debug("ThumbnailService initialized.")

    def get_thumbnail_async(
        self, item_path: str, item_type: Literal["object", "folder"]
    ):
        logger.debug(
            f"Requesting thumbnail async for '{item_path}' (type: {item_type})"
        )
        worker = run_in_background(self._get_thumbnail_task, item_path, item_type)
        worker.signals.result.connect(
            lambda result_dict, p=item_path: self.thumbnailReady.emit(p, result_dict)
        )
        worker.signals.error.connect(
            lambda error_info, p=item_path: self._handle_thumbnail_error(p, error_info)
        )

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
        cache_key = f"{item_type}_{os.path.basename(item_path)}_{os.path.getmtime(item_path)}".replace(
            os.sep, "_"
        )
        logger.debug(f"Cache key for {item_path}: {cache_key}")

        cached_path = self._cache.get(cache_key)
        if cached_path and os.path.exists(cached_path):
            logger.debug(f"Cache hit for '{item_path}' -> {cached_path}")
            return {"path": cached_path, "status": "hit", "error_msg": None}

        logger.debug(f"Cache miss for '{item_path}'. Finding source image...")
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
            logger.debug(f"No source image found for '{item_path}'.")
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

    def _find_object_thumbnail_source(self, folder_path: str) -> str | None:
        try:
            suffix = constants.THUMBNAIL_OBJECT_SUFFIX
            extensions = constants.SUPPORTED_THUMB_EXTENSIONS
            all_found_files = []

            for ext in extensions:
                pattern_glob = os.path.join(folder_path, f"*{suffix}.{ext}")
                matches = glob.glob(pattern_glob)
                all_found_files.extend(matches)

            if not all_found_files:
                logger.debug(
                    f"No files found matching pattern *{suffix}.<ext> in {folder_path}"
                )
                return None

            preferred_order = [".png", ".jpg", ".jpeg", ".webp", ".gif"]

            for pref_ext in preferred_order:
                for file_path in all_found_files:
                    if file_path.lower().endswith(pref_ext):
                        logger.debug(
                            f"Prioritized thumbnail source found ({pref_ext}): {file_path}"
                        )
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
            all_previews = []
            all_fallbacks = []

            for ext in extensions:
                pattern_glob = os.path.join(folder_path, f"{prefix}*.{ext}")
                matches = glob.glob(pattern_glob)
                all_previews.extend(matches)

            if all_previews:
                logger.debug(
                    f"Found {len(all_previews)} specific preview(s) in {folder_path}"
                )
                return sorted(all_previews)

            logger.debug(
                f"No specific previews found in {folder_path}, falling back to any image."
            )
            fallback_patterns = [f"*.{ext}" for ext in extensions]
            object_thumb_suffix = constants.THUMBNAIL_OBJECT_SUFFIX

            for ext_pattern in fallback_patterns:
                pattern_glob = os.path.join(folder_path, ext_pattern)
                matches = glob.glob(pattern_glob)
                all_fallbacks.extend(
                    m
                    for m in matches
                    if not os.path.basename(m).startswith(prefix)
                    and not (
                        os.path.splitext(os.path.basename(m))[0].endswith(
                            f"_{object_thumb_suffix}"
                        )
                        or os.path.splitext(os.path.basename(m))[0].endswith(
                            f"-{object_thumb_suffix}"
                        )
                    )
                )

            unique_fallbacks = sorted(list(set(all_fallbacks)))
            logger.debug(
                f"Found {len(unique_fallbacks)} fallback image(s) in {folder_path}"
            )
            return unique_fallbacks

        except AttributeError as e:
            logger.error(
                f"AttributeError accessing constants in _find_preview_thumbnail_sources: {e}."
            )
            return []
        except Exception as e:
            logger.error(
                f"Error finding preview thumbnail sources in {folder_path}: {e}",
                exc_info=True,
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
