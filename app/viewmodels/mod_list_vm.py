# app/viewmodels/mod_list_vm.py
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path


class ModListViewModel(QObject):
    """
    Manages state and logic for both the objectlist and foldergrid panels,
    adapting its behavior based on the provided context.
    """

    # --- Signals for UI State & Feedback ---
    loading_started = pyqtSignal()
    loading_finished = pyqtSignal()
    items_updated = pyqtSignal(list)
    item_needs_update = pyqtSignal(object)
    item_processing_started = pyqtSignal(str)
    item_processing_finished = pyqtSignal(str, bool)
    toast_requested = pyqtSignal(
        str, str
    )  # message, level ('info', 'error', 'success')

    # --- Signals for Panel-Specific UI ---
    path_changed = pyqtSignal(Path)
    selection_changed = pyqtSignal(bool)

    # --- Signals for Bulk Operations ---
    bulk_operation_started = pyqtSignal()
    bulk_operation_finished = pyqtSignal(list)  # list of failed items

    # --- Signals for Cross-ViewModel Communication ("Efek Domino") ---
    active_object_modified = pyqtSignal(object)
    active_object_deleted = pyqtSignal()
    foldergrid_item_modified = pyqtSignal(object)

    def __init__(
        self,
        context: str,
        mod_service,
        workflow_service,
        database_service,
        system_utils,
    ):
        super().__init__()
        # --- Injected Services ---
        self.context = context  # 'objectlist' or 'foldergrid'
        self.mod_service = mod_service
        self.workflow_service = workflow_service
        self.database_service = database_service
        self.system_utils = system_utils

        # --- Internal State ---
        self.master_list = []
        self.displayed_items = []
        self.selected_item_ids = set()
        self.active_filters = {}
        self.search_query = ""
        self.current_path = None
        self.current_load_token = 0

    # --- Loading and Data Management ---
    def load_items(self, path: Path):
        """Flow 2.2 & 2.3: Starts the two-stage loading process."""
        pass

    def unload_items(self):
        """Clears all items from the view and state to save memory."""
        pass

    def request_item_hydration(self, item_id: str):
        """Flow 2.2 & 2.3: Lazy-loads full details for a visible item."""
        pass

    def update_item_in_list(self, updated_item):
        """Flow 5.1: Updates a single item in the master list and refreshes the view."""
        pass

    # --- Filtering and Searching ---
    def set_filters(self, filters: dict):
        """Flow 5.1: Sets the active filters and triggers a view update."""
        pass

    def on_search_query_changed(self, query: str):
        """Flow 5.1: Sets the search query and triggers a view update (debounced)."""
        pass

    # --- Single Item Actions ---
    def toggle_item_status(self, item_id: str):
        """Flow 3.1: Handles enabling/disabling a single item."""
        pass

    def toggle_pin_status(self, item_id: str):
        """Flow 6.3: Handles pinning/unpinning a single item."""
        pass

    def rename_item(self, item_id: str, new_name: str):
        """Flow 4.2.A: Handles renaming an item."""
        pass

    def delete_item(self, item_id: str):
        """Flow 4.2.B: Handles deleting an item to the recycle bin."""
        pass

    def open_in_explorer(self, item_id: str):
        """Flow 4.3: Opens the item's folder in the system file explorer."""
        pass

    # --- Selection Management ---
    def set_item_selected(self, item_id: str, is_selected: bool):
        """Flow 3.2: Updates the set of selected item IDs."""
        pass

    # --- Bulk & Creation Actions ---
    def initiate_bulk_action(self, action_type: str, **kwargs):
        """Flow 3.2: Central method to start any bulk action (enable, disable, tag)."""
        pass

    def initiate_create_mods(self, tasks: list):
        """Flow 4.1.A: Starts the creation workflow for new mods in foldergrid."""
        pass

    def initiate_create_objects(self, tasks: list):
        """Flow 4.1.B: Starts the creation workflow for new objects in objectlist."""
        pass

    def initiate_randomize(self):
        """Flow 6.2.B: Starts the randomization workflow for the current group."""
        pass

    # --- Private/Internal Logic ---
    def _apply_filters_and_search(self):
        """Flow 5.1: The core in-memory filtering, searching, and sorting logic."""
        pass

    # --- Private Slots for Async Results ---
    def _on_skeletons_loaded(self, result: dict, token: int):
        """Handles the result from the initial skeleton loading worker (Flow 2.2 & 2.3)."""
        pass

    def _on_item_hydrated(self, result: object):
        """Handles the result from a single item hydration worker (Flow 2.2 & 2.3)."""
        pass

    def _on_toggle_status_finished(self, item_id: str, result: dict):
        """Handles the result of a single item status toggle operation (Flow 3.1)."""
        pass

    def _on_pin_status_finished(self, item_id: str, result: dict):
        """Handles the result of a single item pin/unpin operation (Flow 6.3)."""
        pass

    def _on_rename_finished(self, item_id: str, result: dict):
        """Handles the result of a single item rename operation (Flow 4.2.A)."""
        pass

    def _on_delete_finished(self, item_id: str, result: dict):
        """Handles the result of a single item delete operation (Flow 4.2.B)."""
        pass

    def _on_bulk_action_finished(self, result: dict):
        """Handles the result of a bulk action like enable, disable, or tag (Flow 3.2)."""
        pass

    def _on_creation_finished(self, result: dict):
        """Handles the result of a mod or object creation workflow (Flow 4.1)."""
        pass

    def _on_randomize_finished(self, result: dict):
        """Handles the result of a randomize operation (Flow 6.2.B)."""
        pass
