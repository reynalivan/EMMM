# App/viewmodels/base item vm.py
from typing import Set, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

from app.models.object_item_model import ObjectItemModel
from app.models.folder_item_model import FolderItemModel
from app.services.data_loader_service import DataLoaderService
from app.services.mod_management_service import ModManagementService
from app.services.thumbnail_service import ThumbnailService
from app.utils.async_utils import AsyncStatusManager
from app.utils.logger_utils import logger
from app.viewmodels.base.mixins.thumbnail_mixin import ThumbnailMixin
from app.viewmodels.base.mixins.mod_status_mixin import ModStatusMixin
from app.viewmodels.base.mixins.file_watcher_mixin import FileWatcherMixin
from app.viewmodels.base.mixins.item_ui_helper_mixin import ItemUIHelperMixin
from app.viewmodels.base.abstract_base import QObjectAbstractItemViewModel


class BaseItemViewModel(
    QObjectAbstractItemViewModel,
    ModStatusMixin,
    ThumbnailMixin,
    FileWatcherMixin,
    ItemUIHelperMixin,
):
    """
    Base ViewModel for item lists, providing common functionality
    for loading state, enable/disable, and thumbnail handling.
    """

    # ---Signals ---
    batchSummaryReady = pyqtSignal(dict)  # { success: int, failed: int }
    displayListChanged = pyqtSignal(list)  # List[item model type]
    resetFilterState = pyqtSignal()
    loadingStateChanged = pyqtSignal(bool)  # Overall list loading
    pre_mod_status_change = pyqtSignal(str)  # path
    status_changed = pyqtSignal()
    showError = pyqtSignal(str, str)  # title, message
    objectItemPathChanged = pyqtSignal(str, str)  # (old_path, new_path)

    # For InfoBar notifications handled by the Panel
    operation_started = pyqtSignal(str, str)  # item_path (original), operation_title
    operation_finished = pyqtSignal(
        str, str, str, str, bool
    )  # original_path, final_path, title, content, success(bool)

    # For specific item UI state control handled by the Panel
    setItemLoadingState = pyqtSignal(
        str, bool
    )  # item_path (original or final), is_loading (bool)

    updateItemDisplay = pyqtSignal(
        str, dict
    )  # item_path (final), update_payload (dict: status, display_name, path)

    # Specific signal for thumbnail updates
    itemThumbnailNeedsUpdate = pyqtSignal(
        str, dict
    )  # item_path (original), thumbnail_result (dict from service)

    # ---End Signals ---

    def __init__(
        self,
        data_loader: DataLoaderService,
        mod_manager: ModManagementService,
        thumbnail_service: ThumbnailService,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._data_loader = data_loader
        self._mod_manager = mod_manager
        self._thumbnail_service = thumbnail_service
        self._is_loading = False  # Overall list loading state
        self._suppressed_renames: Set[str] = set()
        self._is_handling_status_changes: bool = False

        # Temp storage for item state before toggle, used for revert on failure
        self._original_state_on_toggle: Dict[str, Dict[str, Any]] = {}
        self._status_manager = AsyncStatusManager(self)
        self._init_filewatcher_logic()
        self._connect_internal_signals()

    def _connect_internal_signals(self):
        self._connect_mod_status_signal()
        self._connect_thumbnail_signal()
        self._connect_file_watcher_signals()
