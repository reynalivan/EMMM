# app/utils/image_utils.py
# Utility functions for image manipulation.

import io
import os
from typing import Optional, Tuple, Union
from PyQt6.QtGui import QImage, QPixmap, QGuiApplication  # Import necessary Qt classes
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice  # For QImage conversion
from PIL import Image, ImageSequence
# Assuming constants are defined in app.core.constants
from app.core import constants
# Assuming logger is configured in logger_utils
from app.utils.logger_utils import logger
# Optional: Import Pillow if used for processing
# from PIL import Image

ImageSource = Union[str, bytes]


class ImageUtils:
    """Provides static utility methods for image operations."""

    @staticmethod
    def create_thumbnail(
        source: ImageSource,
        target_size: Tuple[int, int] = (constants.DEFAULT_THUMB_SIZE_W,
                                        constants.DEFAULT_THUMB_SIZE_H),
        quality: int = 85,  # Primarily for JPEG/WEBP lossy
        output_format:
        str = 'PNG'  # Default to PNG for better transparency support
    ) -> Union[bytes, None]:
        """
        Creates a thumbnail from an image file path or bytes using Pillow.

        Preserves aspect ratio, attempts to maintain transparency (outputs PNG if detected),
        and resizes the image to fit within the target_size.

        Args:
            source: Path to the image file (str) or image data (bytes).
            target_size: Tuple (max_width, max_height) for the thumbnail.
            quality: Compression quality (1-95) mainly for lossy formats like JPEG/WEBP.
            output_format: Desired output format ('PNG', 'JPEG', 'WEBP').
                           Will be overridden to PNG if transparency is detected.

        Returns:
            Thumbnail data as bytes, or None if an error occurred or Pillow is not installed.
        """
        if Image is None:  # Check if Pillow was imported successfully
            logger.critical("Pillow library is required but not installed.")
            return None

        img = None
        final_format = output_format.upper()  # Normalize format name for saving

        try:
            # --- 1. Load Image ---
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
                    logger.error(
                        f"Failed to load image from path {source}: {load_err}")
                    return None
            elif isinstance(source, bytes):
                try:
                    img = Image.open(io.BytesIO(source))
                    img.load()  # Ensure image data is loaded from buffer
                    logger.debug(
                        f"Loaded image from bytes (Format: {img.format}, Mode: {img.mode})"
                    )
                except Exception as load_err:
                    logger.error(f"Failed to load image from bytes: {load_err}")
                    return None
            else:
                logger.error(
                    f"Invalid thumbnail source type provided: {type(source)}")
                return None

            # --- 2. Handle Mode & Transparency (Determine Final Format) ---
            has_transparency = False
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P'
                                              and 'transparency' in img.info):
                has_transparency = True

            if has_transparency:
                logger.debug(
                    f"Transparency detected (mode={img.mode}). Ensuring output is PNG."
                )
                final_format = 'PNG'
                # Convert to RGBA if not already for consistent processing
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
            elif img.mode != 'RGB':
                # Convert non-transparent, non-RGB images (like L, P without alpha, CMYK) to RGB
                logger.debug(f"Converting image mode '{img.mode}' to 'RGB'.")
                img = img.convert('RGB')

            # Final check if selected format is supported for saving
            if final_format not in Image.SAVE:
                logger.warning(
                    f"Output format '{final_format}' not supported by Pillow. Defaulting to PNG."
                )
                final_format = 'PNG'

            # --- 3. Resize using thumbnail() - Preserves aspect ratio ---
            original_size = img.size
            img.thumbnail(target_size,
                          Image.Resampling.LANCZOS)  # High-quality downsampling
            logger.debug(
                f"Image resized from {original_size} to {img.size} (target <= {target_size})"
            )

            # --- 4. Save to BytesIO stream ---
            byte_stream = io.BytesIO()
            save_params = {'format': final_format}

            # Add format-specific save options
            if final_format == 'JPEG':
                save_params['quality'] = quality
                save_params['optimize'] = True
                # Ensure JPEG is saved as RGB, not RGBA (Pillow might allow it but many viewers fail)
                if img.mode == 'RGBA':
                    logger.debug(
                        "Converting RGBA to RGB before saving as JPEG.")
                    img = img.convert('RGB')
            elif final_format == 'PNG':
                save_params['optimize'] = True
                # Allow Pillow to handle compression level, optimize is usually good enough
            elif final_format == 'WEBP':
                save_params['quality'] = quality
                save_params[
                    'lossless'] = not has_transparency  # Example: use lossless for non-transparent webp?
                # WEBP supports transparency if mode is RGBA

            logger.debug(
                f"Saving thumbnail to BytesIO stream as {final_format} with params: {save_params}"
            )
            img.save(byte_stream, **save_params)

            # --- 5. Return Bytes ---
            thumbnail_bytes = byte_stream.getvalue()
            logger.debug(
                f"Thumbnail created ({len(thumbnail_bytes)} bytes, Format: {final_format})."
            )
            return thumbnail_bytes

        except Exception as e:
            # Log any other unexpected error during processing
            logger.error(f"Unexpected error creating thumbnail: {e}",
                         exc_info=True)
            return None
        finally:
            # Ensure the image object is closed to free resources
            if img:
                img.close()

    @staticmethod
    def get_image_from_clipboard() -> Optional[QImage]:
        """
        Retrieves an image from the system clipboard.

        Returns:
            QImage if a valid image is found, None otherwise.
        """
        # Implementation Note: Use QGuiApplication.clipboard().image()
        pass  # Skeleton implementation

    @staticmethod
    def qimage_to_bytes(image: QImage,
                        format: str = 'JPEG',
                        quality: int = 90) -> Optional[bytes]:
        """
        Converts a QImage object to bytes in the specified format.

        Args:
            image: The QImage to convert.
            format: 'JPEG', 'PNG', etc. (Case-insensitive).
            quality: Compression quality for lossy formats (-1 for default).

        Returns:
            Image data as bytes if successful, None otherwise.
        """
        # Implementation Note: Use QByteArray, QBuffer, image.save()
        pass  # Skeleton implementation

    @staticmethod
    def validate_image_data(data: bytes) -> bool:
        """
        (Optional) Basic validation to check if byte data represents a known image format.

        Args:
            data: Image data as bytes.

        Returns:
            True if likely a valid image format, False otherwise.
        """
        # Implementation Note: Check magic bytes or use QImage.loadFromData()
        pass  # Skeleton implementation
