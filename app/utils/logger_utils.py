# app/utils/logger_utils.py

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime


# ANSI escape codes for colors
class LogColors:
    RESET = "\x1b[0m"
    GREY = "\x1b[38;21m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    RED = "\x1b[31m"
    BOLD_RED = "\x1b[31;1m"
    CYAN = "\x1b[36m"


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter to add colors to console log output.
    """

    # Base format string similar to the desired loguru format
    # We will build the final format within the format() method
    # Target example: <green>{time}</green> | <level>{level}</level> | <cyan>{name}:{func}:{line}</cyan> - <level>{message}</level>

    LOG_LEVEL_COLORS = {
        logging.DEBUG: LogColors.GREY,
        logging.INFO: LogColors.GREEN,
        logging.WARNING: LogColors.YELLOW,
        logging.ERROR: LogColors.RED,
        logging.CRITICAL: LogColors.BOLD_RED,
    }

    def __init__(self, datefmt="%B %d, %Y > %H:%M:%S"):
        # The base format string isn't crucial here as we override format()
        super().__init__(fmt="%(message)s", datefmt=datefmt)

    def format(self, record):
        # Get color based on log level
        level_color = self.LOG_LEVEL_COLORS.get(record.levelno, LogColors.RESET)
        log_level_name = record.levelname

        # Format time with green color
        time_str = self.formatTime(record, self.datefmt)
        colored_time = f"{LogColors.GREEN}{time_str}{LogColors.RESET}"

        # Format level with color and padding
        colored_level = (
            f"{level_color}{log_level_name:<8}{LogColors.RESET}"  # 8-character padding
        )

        # Format location (name, function, line) with cyan color
        clickable_location_str = f'File "{record.pathname}", line {record.lineno} |  {record.name}:{record.funcName}'
        location = f"{record.name}:{record.funcName}:{record.lineno}"
        # colored_location = f"{LogColors.CYAN}{location}{LogColors.RESET}"
        colored_location = f"{LogColors.CYAN}{clickable_location_str}{LogColors.RESET}"

        # Format the main message with the level color
        message = record.getMessage()  # Ensure message is properly formatted
        colored_message = f"{level_color}{message}{LogColors.RESET}"

        # Combine all parts
        log_entry = (
            f"{colored_time} | {colored_level} | {colored_location} - {colored_message}"
        )

        # Add traceback if there's an exception
        if record.exc_info:
            # Use the base Formatter's formatException for standard traceback
            # Add traceback in red color
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            log_entry += f"\n{LogColors.RED}{record.exc_text}{LogColors.RESET}"

        # Add 'extra' info if present (though not colored by default here)
        # You could add coloring logic for extra if needed
        extra_info = getattr(record, "extra", None)
        if extra_info:
            log_entry += f" | {extra_info}"

        return log_entry


def setup_logger():
    # === Setup log folder & file name ===
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H-%M-%S")
    log_file_name = f"LOG_EMMM_{timestamp}.log"
    log_file_path = log_dir / log_file_name

    # === Get the logger (can be named, e.g., 'app_logger') ===
    # Naming helps if you have multiple loggers
    logger = logging.getLogger("EMMM_App")
    logger.setLevel(logging.DEBUG)  # Set the lowest level on the logger itself

    # === Remove existing handlers (if this function is called again) ===
    # This prevents adding duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # === Console handler (manual coloring) ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Process all messages from DEBUG level up
    # Use our colored formatter, adjust date format if needed
    console_formatter = ColoredFormatter(
        datefmt="%B %d, %Y > %H:%M:%S"
    )  # Similar to loguru format
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # === File handler (no color, structured) ===
    # Using RotatingFileHandler for size-based rotation
    # Adjust maxBytes and backupCount as needed
    # 5 MB = 5 * 1024 * 1024 bytes
    max_bytes = 5 * 1024 * 1024
    backup_count = 10  # Similar to retention=10 in loguru
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # Log all levels to the file too
    # File format similar to your loguru format for files
    file_formatter = logging.Formatter(
        fmt="{asctime} | {levelname} | {name}:{funcName}:{lineno} - {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",  # Use '{' style for f-string like formatting
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Note: Loguru features like enqueue, compression, diagnose, backtrace (detailed)
    # don't have direct, simple equivalents in standard logging without extra libraries
    # or more complex custom implementations.

    return logger


# Initialize once for global use
logger = setup_logger()
__all__ = ["logger"]

# Example usage (can be removed if not needed in this file)
if __name__ == "__main__":
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")

    # Example with extra data (will be shown at the end of the console log)
    # Needs adjustment in the formatter for specific coloring/positioning
    # logger.bind(user="Andy").info("Message with extra data.") # loguru style
    # logging style:
    # logger.info("Message with extra data.", extra={'user': 'Andy'}) # Less common, or manual formatting

    try:
        result = 1 / 0
    except ZeroDivisionError:
        logger.error("A zero division error occurred!", exc_info=True)
        # or
        # logger.exception("A zero division error occurred!") # This is equivalent to error + exc_info=True

    # Accessing the file handler's path (assuming it's the second handler added)
    if len(logger.handlers) > 1 and isinstance(logger.handlers[1], logging.FileHandler):
        log_file_path = logger.handlers[1].baseFilename
        logger.info(f"Logger setup complete. Log file: {log_file_path}")
    else:
        logger.info("Logger setup complete. File handler not found as expected.")
