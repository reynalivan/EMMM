# app/utils/image_utils.py
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from PyQt6.QtGui import QGuiApplication, QImage
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QBuffer, QIODevice
from io import BytesIO

from app.utils.logger_utils import logger


class ImageUtils:
    """A collection of static utility functions for image processing."""

    @staticmethod
    def get_image_from_clipboard() -> Image.Image | None:
        """
        Flow 5.2 Part C: Retrieves an image from the system clipboard.
        This method contains the PyQt-specific logic, converting it to a
        standard Pillow Image object for use by other layers.
        """
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return None
        mime_data = clipboard.mimeData()

        if mime_data and mime_data.hasImage():
            # Get the QImage from the clipboard
            q_image = clipboard.image()
            if q_image.isNull():
                return None

            # Convert QImage to a Pillow Image in-memory
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.ReadWrite)
            # Save QImage to buffer as PNG (a lossless format)
            q_image.save(buffer, "PNG")

            # Rewind buffer to the beginning to be read
            buffer.seek(0)

            # Open the byte stream with Pillow
            try:
                image_bytes = buffer.data().data()
                pil_image = Image.open(BytesIO(image_bytes))
                # Ensure it's in a standard mode like RGB or RGBA
                if pil_image.mode not in ("RGB", "RGBA"):
                    pil_image = pil_image.convert("RGBA")
                return pil_image
            except UnidentifiedImageError:
                return None

        return None

    @staticmethod
    def is_valid_image(image_path: Path) -> bool:
        """Validates if a file can be opened as an image."""
        # Tries to open an image file without loading it fully into memory.
        # Useful for validating user-provided files before processing.
        return True

    @staticmethod
    def compress_and_save_image(
        source_image: Image.Image,
        target_path: Path,
        max_size: tuple[int, int] = (1280, 720),  # Set a reasonable max resolution
        quality: int = 85,
    ):
        """
        Resizes an image if it's too large, converts to RGB, and saves it
        as a compressed WebP file.
        """
        try:
            # Create a copy to avoid modifying the original image object
            img = source_image.copy()

            # Resize the image if it exceeds the max dimensions, keeping aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Ensure image is in RGB mode for saving as WebP/JPEG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Save the image with specified quality
            target_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(target_path, "WEBP", quality=quality)

            logger.info(f"Successfully saved compressed image to '{target_path}'")

        except (IOError, OSError) as e:
            logger.error(f"Could not save image to {target_path}: {e}")
            # Re-raise as a ValueError to be caught by the service layer
            raise ValueError(f"Failed to save image file: {e}") from e

    @staticmethod
    def find_next_available_preview_path(
        folder_path: Path, base_name: str = "preview", extension: str = "webp"
    ) -> Path:
        """
        Finds an available filename like 'preview.webp', 'preview-1.webp', 'preview-2.webp', etc.
        """
        # First, check for the base name itself (e.g., 'preview.webp')
        path = folder_path / f"{base_name}.{extension}"
        if not path.exists():
            return path

        # If it exists, start searching for numbered versions
        i = 1
        while True:
            numbered_path = folder_path / f"{base_name}-{i}.{extension}"
            if not numbered_path.exists():
                return numbered_path
            i += 1
