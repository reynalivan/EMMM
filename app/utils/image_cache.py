# app/utils/image_cache.py

import os
import time
import hashlib
import shutil
from typing import Optional
from ..core import constants
from ..utils.logger_utils import logger


class ImageCache:
    """
    Handles caching of image data (thumbnails) to disk.
    """

    def __init__(
        self,
        cache_dir: str = constants.CACHE_DIR,
        max_size_mb: int = constants.DEFAULT_CACHE_MAX_MB,  # TODO: Implement size limit
        expiry_days: int = constants.DEFAULT_CACHE_EXPIRY_DAYS,
    ):  # TODO: Implement expiry
        """Initializes the cache, creates cache directory if needed."""
        self._cache_dir = os.path.abspath(cache_dir)
        self._max_size_bytes = max_size_mb * 1024 * 1024 if max_size_mb > 0 else 0
        self._expiry_seconds = expiry_days * 24 * 60 * 60 if expiry_days > 0 else 0

        try:
            # Create cache directory including intermediate dirs, ignore if already exists
            os.makedirs(self._cache_dir, exist_ok=True)
            logger.info(f"Image cache directory initialized at: {self._cache_dir}")
        except OSError as e:
            # Log critical error if directory cannot be created
            logger.critical(
                f"FATAL: Failed to create cache directory '{self._cache_dir}': {e}",
                exc_info=True,
            )
            # Consider raising error to stop application or disable caching functionality
            raise RuntimeError(
                f"Cannot create cache directory: {self._cache_dir}"
            ) from e

    def _get_cache_filepath(self, key: str) -> str:
        """Generates a unique and safe file path within the cache directory from a key."""
        # Use SHA1 hash of the key for filename to avoid issues with invalid chars or length
        hashed_key = hashlib.sha1(key.encode("utf-8")).hexdigest()
        # Assume PNG output from create_thumbnail for now
        # TODO: Maybe store extension or derive from data if needed later
        filename = f"{hashed_key}.png"
        return os.path.join(self._cache_dir, filename)

    def put(self, key: str, data: bytes) -> Optional[str]:
        """
        Saves data bytes to a file in the cache directory using the generated key.

        Args:
            key: Unique identifier for the data.
            data: The image data as bytes.

        Returns:
            The absolute path to the saved cache file if successful, otherwise None.
        """
        file_path = self._get_cache_filepath(key)
        logger.debug(
            f"Caching data for key '{key}' to '{file_path}' ({len(data)} bytes)"
        )
        try:
            # Write data in binary mode, overwriting if exists
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
            # Attempt to remove partially written file if error occurred?
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            return None  # Return None on failure

    def get(self, key: str) -> Optional[str]:
        """
        Gets the file path for a cached item if it exists and is valid (not expired).

        Args:
            key: The unique identifier.

        Returns:
            Absolute path to the cache file, or None if not found or expired.
        """
        file_path = self._get_cache_filepath(key)

        # 1. Check existence
        if not os.path.isfile(file_path):  # Use isfile for robustness
            # logger.debug(f"Cache miss (not found): {key}") # Keep lean
            return None

        # 2. Check expiry (if enabled)
        if self._expiry_seconds > 0:
            try:
                file_mod_time = os.path.getmtime(file_path)
                file_age = time.time() - file_mod_time
                if file_age > self._expiry_seconds:
                    logger.info(
                        f"Cache expired for key '{key}', removing '{file_path}' (Age: {file_age:.0f}s > {self._expiry_seconds}s)"
                    )
                    self.remove(key)  # Attempt to remove expired file
                    return None  # Return None as it's expired
            except OSError as e:
                logger.warning(
                    f"Could not get modification time for cache file '{file_path}': {e}"
                )
                # Treat as invalid if we cannot check expiry? Or proceed? Let's treat as invalid.
                return None

        # logger.debug(f"Cache hit: {key} -> {file_path}") # Keep lean
        return file_path  # Return path if exists and not expired

    def remove(self, key: str) -> bool:
        """Removes a specific item from the cache by key."""
        file_path = self._get_cache_filepath(key)
        logger.debug(f"Attempting to remove cache file: {file_path}")
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Removed cache file: {file_path}")
                return True
            except OSError as e:
                logger.error(
                    f"Failed to remove cache file '{file_path}': {e}", exc_info=True
                )
                return False
        else:
            # logger.warning(f"Cache file to remove not found: {file_path}") # Keep lean
            return False  # Indicate file wasn't there to remove

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
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(
                    file_path
                ):  # Should generally not have subdirs with current key generation
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error(f"Failed to delete cache item '{file_path}': {e}")
                success = False  # Mark failure if any deletion fails
        logger.info("Cache clear operation finished.")
        return success

    def _manage_cache(self) -> None:
        """Manage cache size: remove oldest files if exceeding max size."""
        if self._max_size_bytes <= 0:
            return  # No limit set

        try:
            total_size = 0
            file_infos = []

            for filename in os.listdir(self._cache_dir):
                filepath = os.path.join(self._cache_dir, filename)
                if os.path.isfile(filepath):
                    try:
                        stat = os.stat(filepath)
                        total_size += stat.st_size
                        file_infos.append((filepath, stat.st_mtime, stat.st_size))
                    except OSError:
                        continue  # Skip unreadable files

            if total_size <= self._max_size_bytes:
                return  # Cache size is OK

            logger.warning(
                f"Image cache size {total_size} exceeds limit {self._max_size_bytes}, cleaning up..."
            )

            # Sort files by modification time (oldest first)
            file_infos.sort(key=lambda x: x[1])

            # Start deleting oldest until under limit
            for filepath, _, filesize in file_infos:
                try:
                    os.remove(filepath)
                    total_size -= filesize
                    logger.info(f"Deleted old cache file: {filepath}")

                    if total_size <= self._max_size_bytes:
                        break  # Done after enough space freed
                except OSError as e:
                    logger.error(
                        f"Failed to delete cache file '{filepath}': {e}", exc_info=True
                    )

        except Exception as e:
            logger.error(f"Error managing cache size: {e}", exc_info=True)

    def clean_expired(self) -> None:
        """Remove cache files that are expired based on modification time."""
        if self._expiry_seconds <= 0:
            return  # Expiry check disabled

        try:
            now = time.time()
            expired_files = []

            for filename in os.listdir(self._cache_dir):
                filepath = os.path.join(self._cache_dir, filename)
                if os.path.isfile(filepath):
                    try:
                        mod_time = os.path.getmtime(filepath)
                        if now - mod_time > self._expiry_seconds:
                            expired_files.append(filepath)
                    except OSError:
                        continue  # Skip unreadable files

            for filepath in expired_files:
                try:
                    os.remove(filepath)
                    logger.info(f"Deleted expired cache file: {filepath}")
                except OSError as e:
                    logger.error(
                        f"Failed to delete expired cache file '{filepath}': {e}",
                        exc_info=True,
                    )

            if expired_files:
                logger.info(
                    f"Expired cache clean complete. Deleted {len(expired_files)} files."
                )

        except Exception as e:
            logger.error(f"Error during expired cache cleaning: {e}", exc_info=True)
