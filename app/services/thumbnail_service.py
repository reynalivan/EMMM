# app/services/thumbnail_service.py

from typing import Literal  # Import Literal for type hinting
from PyQt6.QtCore import QObject, pyqtSignal  # Import QObject and pyqtSignal

# Add imports for dependencies type hinting
from app.utils.image_cache import ImageCache
from app.utils.image_utils import ImageUtils

# Keep other imports
from app.utils.logger_utils import logger
from app.utils.async_utils import Worker, run_in_background  # Keep Worker for signal connection if needed by helper
from app.core import constants  # Import constants
import os
import glob

# Use constant defined in constants.py (assuming it exists)
# SUPPORTED_EXTENSIONS = constants.SUPPORTED_IMAGE_EXTENSIONS # Example if defined in constants


class ThumbnailService(QObject):  # Inherit from QObject
    # --- Signals ---
    # Emitted when a single thumbnail result is ready (from cache or generation)
    thumbnailReady = pyqtSignal(
        str, dict
    )  # item_path, result {'path': str|None, 'status': 'hit'|'generated'|'fallback'|'error', 'error_msg': str|None}
    # Emitted when the list of preview thumbnail paths for the preview panel is ready
    previewThumbnailsFound = pyqtSignal(
        str, list)  # item_path, list[str] of image_paths

    # --- Methods ---
    def __init__(self,
                 image_cache: ImageCache,
                 image_utils: ImageUtils,
                 parent: QObject | None = None):
        """
        Initialize the ThumbnailService.

        Args:
            image_cache: Instance of ImageCache for caching thumbnails.
            image_utils: Instance of ImageUtils for image processing.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._cache = image_cache
        self._utils = image_utils
        logger.debug(
            "ThumbnailService initialized with ImageCache and ImageUtils.")

    # --- Asynchronous Methods (Public API) ---

    def get_thumbnail_async(self, item_path: str, item_type: Literal['object',
                                                                     'folder']):
        """
        Asynchronously gets the thumbnail for a given item path and type.
        Checks cache first, then finds source and generates if needed.
        Emits the `thumbnailReady` signal with the result.

        Args:
            item_path: The absolute path to the object or folder item.
            item_type: Either 'object' (for objectlist items) or 'folder' (for foldergrid items).
        """
        logger.debug(
            f"Requesting thumbnail async for '{item_path}' (type: {item_type})")
        worker = run_in_background(self._get_thumbnail_task, item_path,
                                   item_type)
        # Connect worker signals to slots that will emit the service signal
        # Pass item_path to the lambda/slot to know which request this result belongs to
        worker.signals.result.connect(lambda result_dict, p=item_path: self.
                                      thumbnailReady.emit(p, result_dict))
        worker.signals.error.connect(lambda error_info, p=item_path: self.
                                     _handle_thumbnail_error(p, error_info))

    def find_preview_thumbnails_async(self, folder_path: str):
        """
        Asynchronously finds all potential preview thumbnails (preview.* or fallback images)
        within a folder, intended for the Preview Panel.
        Emits the `previewThumbnailsFound` signal.

        Args:
            folder_path: The absolute path to the folder item selected in the grid.
        """
        logger.debug(f"Requesting preview thumbnails async for '{folder_path}'")
        worker = run_in_background(self._scan_preview_thumbnails_task,
                                   folder_path)
        # Connect worker signals
        worker.signals.result.connect(lambda paths, p=folder_path: self.
                                      previewThumbnailsFound.emit(p, paths))
        worker.signals.error.connect(lambda error_info, p=folder_path: self.
                                     _handle_scan_error(p, error_info))

    # --- Private Task Methods (Executed in Background Threads) ---

    def _get_thumbnail_task(self, item_path: str,
                            item_type: Literal['object', 'folder']) -> dict:
        """
        The actual task that runs in the background to get a single thumbnail.
        Implements the logic: check cache -> find source -> generate -> update cache.

        Args:
            item_path: The absolute path to the object or folder item.
            item_type: Either 'object' or 'folder'.

        Returns:
            A dictionary summarizing the result, to be emitted by `thumbnailReady`.
        """
        # 1. Define Cache Key
        # A simple key based on type and path (ensure filesystem safe chars if using directly)
        # Consider hashing item_path if it can be very long or contain problematic chars
        cache_key = f"{item_type}_{os.path.basename(item_path)}_{os.path.getmtime(item_path)}".replace(
            os.sep, '_')  # Example key
        logger.debug(f"Cache key for {item_path}: {cache_key}")

        # 2. Check Cache
        cached_path = self._cache.get(
            cache_key)  # Assume cache returns the path to the cached file
        if cached_path and os.path.exists(cached_path):
            logger.debug(f"Cache hit for '{item_path}' -> {cached_path}")
            return {'path': cached_path, 'status': 'hit', 'error_msg': None}

        logger.debug(f"Cache miss for '{item_path}'. Finding source image...")
        # 3. Find Source Image Path
        source_image_path: str | None = None
        try:
            if item_type == 'object':
                # Use helper (can be made private later if only used here)
                source_image_path = self._find_object_thumbnail_source(
                    item_path)
            elif item_type == 'folder':
                # Use helper
                preview_paths = self._find_preview_thumbnail_sources(item_path)
                if preview_paths:
                    source_image_path = preview_paths[
                        0]  # Use the first found preview
        except Exception as e:
            logger.warning(f"Error finding source image for '{item_path}': {e}")
            # Do not raise here, return error status dictionary
            return {
                'path': None,
                'status': 'error',
                'error_msg': f"Finding source failed: {e}"
            }

        if not source_image_path:
            logger.debug(f"No source image found for '{item_path}'.")
            return {
                'path': None,
                'status': 'fallback',
                'error_msg': "Source image not found"
            }

        logger.debug(
            f"Source image found: '{source_image_path}'. Generating thumbnail..."
        )
        # 4. Generate Thumbnail (if source was found)
        try:
            # Define target size using constants
            target_size = (constants.DEFAULT_THUMB_SIZE_W,
                           constants.DEFAULT_THUMB_SIZE_H)
            # Use ImageUtils to create thumbnail bytes
            thumbnail_bytes = self._utils.create_thumbnail(
                source_image_path, target_size)

            if not thumbnail_bytes:
                logger.error(
                    f"Thumbnail generation returned None for '{source_image_path}'."
                )
                return {
                    'path': None,
                    'status': 'error',
                    'error_msg': "Generation failed (returned None)"
                }

            # 5. Put Generated Thumbnail into Cache
            # cache.put should handle saving bytes to a file and return the path
            cached_path_after_put = self._cache.put(cache_key, thumbnail_bytes)
            if cached_path_after_put:
                logger.debug(
                    f"Generated and cached thumbnail for '{item_path}' at '{cached_path_after_put}'."
                )
                return {
                    'path': cached_path_after_put,
                    'status': 'generated',
                    'error_msg': None
                }
            else:
                logger.error(
                    f"Failed to put generated thumbnail into cache for '{item_path}'."
                )
                return {
                    'path': None,
                    'status': 'error',
                    'error_msg': "Cache put failed"
                }

        except Exception as e:
            logger.error(
                f"Error during thumbnail generation/caching for '{item_path}': {e}",
                exc_info=True)
            return {
                'path': None,
                'status': 'error',
                'error_msg': f"Generation/Cache error: {e}"
            }

    def _scan_preview_thumbnails_task(self, folder_path: str) -> list[str]:
        """
        Background task to find all preview thumbnail source paths for the Preview Panel.

        Args:
            folder_path: Absolute path to the folder.

        Returns:
            A sorted list of absolute paths to found image files.
            Raises exception on error which will be caught by the worker.
        """
        logger.debug(
            f"Scanning preview thumbnails task started for {folder_path}")
        try:
            paths = self._find_preview_thumbnail_sources(
                folder_path)  # Use helper
            logger.debug(
                f"Scan task found {len(paths)} preview paths for {folder_path}")
            return paths
        except Exception as e:
            logger.warning(
                f"Preview thumbnail scan task error for {folder_path}: {e}",
                exc_info=True)
            raise e  # Let the worker catch and emit the error signal

    # --- Private Helper / Synchronous Find Methods ---
    # These helpers contain the actual file searching logic

    def _find_object_thumbnail_source(self, folder_path: str) -> str | None:
        """
        Finds the source file for an object thumbnail (e.g., *thumb.png),
        prioritizing specific extensions like PNG over JPG.
        """
        try:
            suffix = constants.THUMBNAIL_OBJECT_SUFFIX
            # Use SUPPORTED_THUMB_EXTENSIONS which is already a tuple
            extensions = constants.SUPPORTED_THUMB_EXTENSIONS
            all_found_files = []

            # 1. Collect all matching files first
            for ext in extensions:
                pattern_glob = os.path.join(folder_path, f"*{suffix}.{ext}")
                # Note: glob might be case-sensitive on some systems (Linux)
                matches = glob.glob(pattern_glob)
                all_found_files.extend(matches)

            if not all_found_files:
                logger.debug(
                    f"No files found matching pattern *{suffix}.<ext> in {folder_path}"
                )
                return None

            # 2. Prioritize based on extension order
            # Define the preferred order (including the dot) - can be a constant later
            preferred_order = ['.png', '.jpg', '.jpeg', '.webp', '.gif']

            for pref_ext in preferred_order:
                for file_path in all_found_files:
                    # Case-insensitive check for extension matching
                    if file_path.lower().endswith(pref_ext):
                        logger.debug(
                            f"Prioritized thumbnail source found ({pref_ext}): {file_path}"
                        )
                        return file_path  # Return the first match found in preferred order

            # 3. Fallback: If no preferred extension found (should not happen if extensions list is correct),
            # return the first file found initially.
            logger.warning(
                f"No preferred extension match in {all_found_files}, returning first found: {all_found_files[0]}"
            )
            return all_found_files[0]

        except AttributeError as e:
            logger.error(
                f"AttributeError accessing constants in _find_object_thumbnail_source: {e}. Check constants.py."
            )
            return None
        except Exception as e:
            logger.error(
                f"Error finding object thumbnail source in {folder_path}: {e}",
                exc_info=True)
            return None

    def _find_preview_thumbnail_sources(self, folder_path: str) -> list[str]:
        """Finds source files for preview thumbnails (preview*.* or fallback images)."""
        result = []
        try:
            prefix = constants.THUMBNAIL_FOLDER_PREFIX
            extensions = constants.SUPPORTED_THUMB_EXTENSIONS
            all_previews = []
            all_fallbacks = []

            # 1. Look for specific preview patterns first (e.g., preview*.png)
            for ext in extensions:
                pattern_glob = os.path.join(
                    folder_path, f"{prefix}*.{ext}")  # Use prefix*.ext
                matches = glob.glob(pattern_glob)
                all_previews.extend(matches)

            if all_previews:
                # If specific previews found, sort and return them only
                logger.debug(
                    f"Found {len(all_previews)} specific preview(s) in {folder_path}"
                )
                return sorted(all_previews)

            # 2. Fallback: find any image in the folder (non-recursive)
            logger.debug(
                f"No specific previews found in {folder_path}, falling back to any image."
            )
            fallback_patterns = [f"*.{ext}" for ext in extensions]
            object_thumb_suffix = constants.THUMBNAIL_OBJECT_SUFFIX

            for ext_pattern in fallback_patterns:
                pattern_glob = os.path.join(folder_path, ext_pattern)
                matches = glob.glob(pattern_glob)
                # Avoid adding previews or object thumbs found via fallback
                all_fallbacks.extend(
                    m for m in matches
                    if not os.path.basename(m).startswith(prefix)
                    and not (os.path.splitext(os.path.basename(m))[0].endswith(
                        f"_{object_thumb_suffix}"
                    ) or os.path.splitext(os.path.basename(m))[0].endswith(
                        f"-{object_thumb_suffix}")))  # Check suffix carefully

            unique_fallbacks = sorted(list(set(all_fallbacks)))
            logger.debug(
                f"Found {len(unique_fallbacks)} fallback image(s) in {folder_path}"
            )
            return unique_fallbacks  # Return only fallbacks if no specific previews found

        except AttributeError as e:
            logger.error(
                f"AttributeError accessing constants in _find_preview_thumbnail_sources: {e}. Check constants.py."
            )
            return []
        except Exception as e:
            logger.error(
                f"Error finding preview thumbnail sources in {folder_path}: {e}",
                exc_info=True)
            return []

    def _handle_thumbnail_error(self, item_path: str, error_info: tuple):
        """Handles errors from the _get_thumbnail_task worker."""
        exctype, value, tb_str = error_info  # Traceback might be string from Worker
        logger.error(
            f"Worker error getting thumbnail for '{item_path}': {value}")
        # Emit the thumbnailReady signal indicating an error
        self.thumbnailReady.emit(item_path, {
            'path': None,
            'status': 'error',
            'error_msg': str(value)
        })

    def _handle_scan_error(self, item_path: str, error_info: tuple):
        """Handles errors from the _scan_preview_thumbnails_task worker."""
        exctype, value, tb_str = error_info
        logger.error(
            f"Worker error scanning previews for '{item_path}': {value}")
        # Emit previewThumbnailsFound with an empty list to indicate failure
        self.previewThumbnailsFound.emit(item_path, [])

    # Note: The old methods using callbacks (`find_thumbnail_in_folder_async`, etc.) are removed/replaced.
