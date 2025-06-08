# app/core/signals.py
from PyQt6.QtCore import QObject, pyqtSignal


class GlobalSignals(QObject):
    """
    A singleton class for application-wide signals.
    Helps to decouple components that don't have a direct relationship.

    Note: Use this sparingly. Most communication should be handled by signals
    within specific ViewModels to maintain a clear MVVM data flow.
    """

    # Used by deep services (like DatabaseService) to request a UI toast
    # without needing a direct reference to any ViewModel or View.
    # Emits: message (str), level (str, e.g., 'info', 'warning', 'error')
    toast_requested = pyqtSignal(str, str)

    # Can be used by any component to request logging a message.
    # A central logger handler will connect to this.
    # Emits: level (str, e.g., 'INFO', 'ERROR'), message (str)
    log_message_requested = pyqtSignal(str, str)


# Create a single, global instance that can be imported anywhere
global_signals = GlobalSignals()
