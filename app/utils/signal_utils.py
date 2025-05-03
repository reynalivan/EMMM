from PyQt6.QtCore import QObject, pyqtBoundSignal
from app.utils.logger_utils import logger


def safe_connect(signal: pyqtBoundSignal, slot: callable, obj: QObject):
    """
    Safely connects a signal to a slot by disconnecting it first if already connected.
    """
    try:
        signal.disconnect(slot)
    except (TypeError, RuntimeError):
        pass  # Not connected before, safe to ignore
    signal.connect(slot)
    logger.debug(f"[safe_connect] Connected: {slot.__qualname__}")
