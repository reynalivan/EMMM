# App/viewmodels/mod list vm.py


import dataclasses
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool
from PyQt6.QtGui import QPixmap
from app.models.game_model import Game
from app.models.mod_item_model import (
    ModStatus,
    BaseModItem,
    ObjectItem,
    CharacterObjectItem,
    GenericObjectItem,
    FolderItem,
)
from app.utils.logger_utils import logger
from app.utils.async_utils import Worker
from app.utils.logger_utils import logger
from app.services.thumbnail_service import ThumbnailService
from app.services.database_service import DatabaseService
from app.services.mod_service import ModService
from app.services.workflow_service import WorkflowService
from app.utils.system_utils import SystemUtils
from app.core.constants import CONTEXT_OBJECTLIST, CONTEXT_FOLDERGRID


class ModListViewModel(QObject):
    """
    Manages state and logic for both the objectlist and foldergrid panels,
    adapting its behavior based on the provided context.
    """

    # ---Signals for UI State & Feedback ---

    loading_started = pyqtSignal()
    loading_finished = pyqtSignal()
    items_updated = pyqtSignal(list)
    item_needs_update = pyqtSignal(object)
    item_processing_started = pyqtSignal(str)
    item_processing_finished = pyqtSignal(str, bool)
    toast_requested = pyqtSignal(
        str, str
    )  # message, level ('info', 'error', 'success')

    # ---Signals for Panel-Specific UI ---

    path_changed = pyqtSignal(Path)
    selection_changed = pyqtSignal(bool)

    # ---Signals for Bulk Operations ---

    bulk_operation_started = pyqtSignal()
    bulk_operation_finished = pyqtSignal(list)  # list of failed items

    # ---Signals for Cross-ViewModel Communication ("Efek Domino") ---

    active_object_modified = pyqtSignal(object)
    active_object_deleted = pyqtSignal()
    foldergrid_item_modified = pyqtSignal(object)

    def __init__(
        self,
        context: str,
        mod_service: ModService,
        workflow_service: WorkflowService,
        database_service: DatabaseService,
        thumbnail_service: ThumbnailService,
        system_utils: SystemUtils,
    ):
        super().__init__()
        # ---Injected Services ---
        self.context = context  # 'objectlist' or 'foldergrid'
        self.mod_service = mod_service
        self.workflow_service = workflow_service
        self.database_service = database_service
        self.thumbnail_service = thumbnail_service
        self.system_utils = system_utils

        # ---Internal State ---
        self.master_list = []
        self.displayed_items = []
        self.selected_item_ids = set()
        self.active_filters = {}
        self.search_query = ""
        self.current_path = None
        self.current_load_token = 0
        self._hydrating_ids = set()
        self.current_game: Game | None = None
        self.navigation_root: Path | None = None
        self._processing_ids = set()

        self.thumbnail_service.thumbnail_generated.connect(self._on_thumbnail_generated)

    # ---Loading and Data Management ---

    def load_items(
        self, path: Path, game: Game | None = None, is_new_root: bool = False
    ):
        """
        Flow 2.2 & 2.3: Starts the two-stage loading process (Skeleton stage).
        This version is cleaned up to prevent item stacking and redundant signals.
        """
        if not path or not path.is_dir():
            self.toast_requested.emit(f"Invalid path provided: {path}", "error")
            return

        # 1. Race Condition Prevention

        self.current_load_token += 1
        token_for_this_load = self.current_load_token
        logger.info(f"Loading items for '{path}' with token {token_for_this_load}")

        # 2. Reset Internal State

        self.master_list = []
        self.displayed_items = []
        self.current_path = path
        self.current_game = game
        if is_new_root:
            self.navigation_root = path

        # 3. Emit Signals to Update UI State
        # The View's _on_loading_started slot should handle clearing the old items
        # and showing the shimmer effect. This is the single source of truth for "loading".

        self.loading_started.emit()

        # Update breadcrumb path after starting the loading state

        if self.context == "foldergrid":
            self.path_changed.emit(self.current_path)

        # 4. Start Background Task

        worker = Worker(self.mod_service.get_item_skeletons, path, self.context)
        worker.signals.result.connect(
            lambda result: self._on_skeletons_loaded(result, token_for_this_load)
        )
        worker.signals.error.connect(self._on_skeletons_error)

        thread_pool = QThreadPool.globalInstance()
        if thread_pool:
            thread_pool.start(worker)

    def unload_items(self):
        """Clears all items from the view and state to save memory and reset the view."""
        logger.info(f"Unloading all items for context: '{self.context}'")
        self.master_list = []
        self.displayed_items = []
        self.current_path = None
        self.current_load_token += 1  # Invalidate any ongoing loads

        # Emit signal with empty list to clear the UI

        self.items_updated.emit([])

        # Reset navigation root

        self.navigation_root = None

        # If this is foldergrid, also clear the breadcrumb

        if self.context == "foldergrid":
            self.path_changed.emit(Path())

    def request_item_hydration(self, item_id: str):
        """Flow 2.2 & 2.3: Lazy-loads full details for a visible item."""
        if item_id in self._hydrating_ids:
            return  # Already being processed

        item = next((i for i in self.master_list if i.id == item_id), None)

        # Guard clauses: don't hydrate if not found, not a skeleton, or no game context

        if not item or not item.is_skeleton or not self.current_game:
            return

        self._hydrating_ids.add(item_id)

        worker = Worker(
            self.mod_service.hydrate_item, item, self.current_game.name, self.context
        )
        worker.signals.result.connect(self._on_item_hydrated)
        worker.signals.error.connect(
            lambda err, id=item_id: self._on_hydration_error(err, id)
        )

        thread_pool = QThreadPool.globalInstance()
        if thread_pool:
            thread_pool.start(worker)
        else:
            logger.critical(
                f"Could not get QThreadPool instance for hydrating item {item_id}."
            )
            self._on_hydration_error((None, "Thread pool unavailable", ""), item_id)

    def update_item_in_list(self, updated_item):
        """Flow 5.1: Updates a single item in the master list and refreshes the view."""
        if not updated_item:
            return

        logger.info(
            f"Receiving external update for item '{updated_item.actual_name}' in context '{self.context}'"
        )
        try:
            # Change items on Master List
            master_idx = next(
                i
                for i, item in enumerate(self.master_list)
                if item.id == updated_item.id
            )
            self.master_list[master_idx] = updated_item

            # Change also on the displayed list
            display_idx = next(
                i
                for i, item in enumerate(self.displayed_items)
                if item.id == updated_item.id
            )
            self.displayed_items[display_idx] = updated_item

            # Ask UI to update a specific widget
            self.item_needs_update.emit(self._create_dict_from_item(updated_item))
        except StopIteration:
            logger.warning(
                f"Item {updated_item.id} to update was not found in the list."
            )

    # ---Filtering and Searching ---

    def set_filters(self, filters: dict):
        """Flow 5.1: Sets the active filters and triggers a view update."""
        pass

    def on_search_query_changed(self, query: str):
        """Flow 5.1: Sets the search query and triggers a view update (debounced)."""
        pass

    # ---Single Item Actions ---

    def toggle_item_status(self, item_id: str):
        """
        Flow 3.1a: Initiates the background task to toggle an item's status.
        """
        if item_id in self._processing_ids:
            logger.warning(
                f"Item '{item_id}' is already being processed. Ignoring request."
            )
            return

        item_to_toggle = next(
            (item for item in self.master_list if item.id == item_id), None
        )

        if not item_to_toggle:
            logger.error(
                f"toggle_item_status: Item with ID '{item_id}' not found in master list."
            )
            return

        logger.info(f"Toggling status for item: {item_to_toggle.actual_name}")

        # 1. Mark the item as being processed & tell UI

        self._processing_ids.add(item_id)
        self.item_processing_started.emit(item_id)

        # 2. Create and run a worker in the background thread

        worker = Worker(self.mod_service.toggle_status, item_to_toggle)
        worker.signals.result.connect(
            lambda result, id=item_id: self._on_toggle_status_finished(id, result)
        )
        worker.signals.error.connect(
            lambda error, id=item_id: self._on_toggle_status_error(id, error)
        )

        thread_pool = QThreadPool.globalInstance()
        if thread_pool:
            thread_pool.start(worker)
        else:
            logger.critical(
                f"Could not get QThreadPool instance for toggling item {item_id}."
            )
            self._on_toggle_status_error(item_id, (None, "Thread pool unavailable", ""))

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
        """
        Flow 4.3: Finds the item by its ID and requests SystemUtils
        to open its folder path in the system's file explorer.
        """
        logger.info(f"Request received to open item '{item_id}' in explorer.")

        # 1. Find the item model in the master list using its ID.
        item = next((i for i in self.master_list if i.id == item_id), None)

        if not item:
            logger.error(
                f"Cannot open in explorer: Item with id '{item_id}' not found."
            )
            self.toast_requested.emit("Could not find the selected item.", "error")
            return

        # 2. Get the folder path from the item model.
        path_to_open = item.folder_path

        # 3. Delegate the action to the utility class.
        self.system_utils.open_path_in_explorer(path_to_open)

    # ---Selection Management ---

    def set_item_selected(self, item_id: str, is_selected: bool):
        """Flow 3.2: Updates the set of selected item IDs."""
        pass

    # ---Bulk & Creation Actions ---

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

    def _create_dict_from_item(self, item: BaseModItem) -> dict:
        """A helper function to convert any BaseModItem object to a dict for the view."""
        # 1. Start with attributes common to all items

        data = {
            "id": item.id,
            "actual_name": item.actual_name,
            "is_enabled": (item.status == ModStatus.ENABLED),
            "is_pinned": item.is_pinned,
            "is_skeleton": item.is_skeleton,
            "folder_path": item.folder_path,
        }
        # 2. Add attributes specific to the item type

        if isinstance(item, ObjectItem):
            if isinstance(item, CharacterObjectItem):
                data.update(
                    {
                        "thumbnail_path": item.thumbnail_path,
                        "object_type": item.object_type,
                        "tags": item.tags,
                        "gender": item.gender,
                        "rarity": item.rarity,
                        "element": item.element,
                    }
                )
            elif isinstance(item, GenericObjectItem):
                data.update(
                    {
                        "thumbnail_path": item.thumbnail_path,
                        "object_type": item.object_type,
                        "tags": item.tags,
                    }
                )
        elif isinstance(item, FolderItem):
            data.update(
                {
                    "author": item.author,
                    "description": item.description,
                    "tags": item.tags,
                    "preview_images": item.preview_images,
                    "is_navigable": item.is_navigable,
                    "is_safe": item.is_safe,
                }
            )
        return data

    # ---Private/Internal Logic ---

    def apply_filters_and_search(self):
        """Filters, sorts, and converts the master list to dicts for the view."""
        # In a future step, actual filtering logic will go here.
        # For now, it just takes the entire master_list.
        filtered_items = self.master_list

        # The sorting logic you have is excellent and should be kept.
        sorted_list = sorted(
            filtered_items,
            key=lambda item: (
                not item.is_pinned,
                item.status != ModStatus.ENABLED,
                item.actual_name.lower(),
            ),
        )
        self.displayed_items = sorted_list

        # --- FIX: Ensure we always emit the complete, correctly formatted data ---
        # The view should not need to know about model objects, only data dictionaries.
        # This helper function needs to be implemented in your ViewModel.
        view_data = [self._create_dict_from_item(item) for item in self.displayed_items]

        logger.info(
            f"Applying filters and emitting {len(view_data)} items to the view."
        )
        self.items_updated.emit(view_data)

    # ---Private Slots for Async Results ---

    def _on_skeletons_loaded(self, result: dict, received_token: int):
        """Handles the result from the skeleton loading worker."""
        # Race Condition Check: If this result is from an old request, ignore it.

        if received_token != self.current_load_token:
            logger.warning(
                f"Ignoring stale skeleton load result with token {received_token}"
            )
            return

        self.loading_finished.emit()  # Hide shimmer

        if not result["success"]:
            self.toast_requested.emit(f"Error: {result['error']}", "error")
            self.items_updated.emit([])  # Ensure view is empty

            return

        logger.info(f"Successfully loaded {len(result['items'])} skeletons.")
        self.master_list = result["items"]
        self.apply_filters_and_search()

    def _on_skeletons_error(self, error_info: tuple):
        """Handles unexpected errors from the worker thread."""
        self.loading_finished.emit()  # Hide shimmer

        exctype, value, tb = error_info
        logger.critical(f"Failed to load skeletons: {value}\n{tb}")
        self.toast_requested.emit(
            "A critical error occurred while loading mods.", "error"
        )

    def _on_item_hydrated(self, hydrated_item: BaseModItem):
        """
        Updates the master list with the hydrated item and notifies the view.
        This method now correctly differentiates between ObjectItem and FolderItem.
        """
        self._hydrating_ids.discard(hydrated_item.id)

        # ---SECTION: Differentiate item type ---

        # 1. Create a base dictionary with common attributes

        base_data = {
            "id": hydrated_item.id,
            "actual_name": hydrated_item.actual_name,
            "is_enabled": hydrated_item.status,
            "is_pinned": hydrated_item.is_pinned,
            "is_skeleton": hydrated_item.is_skeleton,
        }

        hydrated_data = {}

        # 2. Check the instance type and add specific attributes

        if isinstance(hydrated_item, ObjectItem):
            if isinstance(hydrated_item, CharacterObjectItem):
                # It's an item for the objectlist

                object_item_data = {
                    "thumbnail_path": hydrated_item.thumbnail_path,
                    "object_type": hydrated_item.object_type,
                    "tags": hydrated_item.tags,
                    "gender": hydrated_item.gender,
                    "rarity": hydrated_item.rarity,
                    "element": hydrated_item.element,
                }
                hydrated_data = {**base_data, **object_item_data}
            elif isinstance(hydrated_item, GenericObjectItem):
                # It's a generic object item

                generic_item_data = {
                    "thumbnail_path": hydrated_item.thumbnail_path,
                    "object_type": hydrated_item.object_type,
                    "tags": hydrated_item.tags,
                }
                hydrated_data = {**base_data, **generic_item_data}
        elif isinstance(hydrated_item, FolderItem):
            # It's an item for the foldergrid

            folder_item_data = {
                "author": hydrated_item.author,
                "description": hydrated_item.description,
                "tags": hydrated_item.tags,
                "preview_images": hydrated_item.preview_images,
                "is_navigable": hydrated_item.is_navigable,
                "is_safe": hydrated_item.is_safe,
            }
            hydrated_data = {**base_data, **folder_item_data}

        else:
            logger.error(
                f"Received an unknown item type during hydration: {type(hydrated_item)}"
            )
            return
        # ---END REVISED SECTION ---

        try:
            # The rest of the logic for the list and signal issuers remain the same

            master_idx = self.master_list.index(
                next(i for i in self.master_list if i.id == hydrated_item.id)
            )
            self.master_list[master_idx] = hydrated_item

            display_idx = self.displayed_items.index(
                next(i for i in self.displayed_items if i.id == hydrated_item.id)
            )
            self.displayed_items[display_idx] = hydrated_item

            hydrated_data = self._create_dict_from_item(hydrated_item)
            self.item_needs_update.emit(hydrated_data)
        except (ValueError, StopIteration):
            logger.warning(
                f"Could not find item {hydrated_item.id} to update post-hydration. List may have been reloaded."
            )

    def _on_hydration_error(self, error_info: tuple, item_id: str):
        """Handles errors during hydration and cleans up."""
        self._hydrating_ids.discard(item_id)
        exctype, value, tb = error_info
        logger.error(f"Failed to hydrate item {item_id}: {value}\n{tb}")

    def _on_toggle_status_finished(self, item_id: str, result: dict):
        """Handles the result of a single item status toggle operation."""
        self._processing_ids.discard(item_id)  # Delete from the process list

        if not result.get("success"):
            error_msg = result.get("error", "An unknown error occurred.")
            self.toast_requested.emit(error_msg, "error")
            self.item_processing_finished.emit(
                item_id, False
            )  # Send the finished signal (fail)

            return

        # ---Success Path ---
        # Create an immutable new item object with updated data

        try:
            old_item = next(i for i in self.master_list if i.id == item_id)

            # Create DICT from new data to be passing to datoclasses.replace

            new_data_from_service = result["data"]
            update_payload = {
                "folder_path": new_data_from_service["new_path"],
                "status": new_data_from_service["new_status"],
            }
            new_item = dataclasses.replace(old_item, **update_payload)

            # Change the old item with the new one on the internal list

            master_idx = self.master_list.index(old_item)
            self.master_list[master_idx] = new_item

            # Also update the list that is displayed if the item is there

            if old_item in self.displayed_items:
                display_idx = self.displayed_items.index(old_item)
                self.displayed_items[display_idx] = new_item

            logger.info(f"Successfully toggled status for item: {new_item.actual_name}")

            # Send signals to UI for updates

            self.item_needs_update.emit(self._create_dict_from_item(new_item))
            self.item_processing_finished.emit(
                item_id, True
            )  # Send the finished signal (success)

            # If the context is an objectlist, tell the orchestrator (mainwindowviewmodel)
            # that an object item has been modified.

            if self.context == CONTEXT_OBJECTLIST:
                self.active_object_modified.emit(new_item)
            elif self.context == CONTEXT_FOLDERGRID:
                self.foldergrid_item_modified.emit(new_item)

        except (StopIteration, KeyError) as e:
            logger.error(f"Error updating item state after toggle: {e}", exc_info=True)
            self.item_processing_finished.emit(item_id, False)

    # ADD THIS NEW SLOT

    def _on_toggle_status_error(self, item_id: str, error_info: tuple):
        """Handles unexpected worker errors during toggle."""
        self._processing_ids.discard(item_id)
        self.item_processing_finished.emit(item_id, False)  # Make sure UI is unblock

        exctype, value, tb = error_info
        logger.critical(
            f"A worker error occurred while toggling item {item_id}: {value}\n{tb}"
        )
        self.toast_requested.emit(
            "A critical error occurred. Please check the logs.", "error"
        )

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

    def get_thumbnail(
        self, item_id: str, source_path: Path | None, default_type: str
    ) -> QPixmap:
        """
        Flow 2.4, Step 2: A wrapper method that delegates the thumbnail request to the service.
        This decouples the View from having to know about the ThumbnailService directly.
        """
        return self.thumbnail_service.get_thumbnail(
            item_id=item_id, source_path=source_path, default_type=default_type
        )

    def get_initial_name(self, name: str):
        """
        Generates an initial from the name for avatar display.
        """
        return self.system_utils.get_initial_name(name, length=2)

    def _on_thumbnail_generated(self, item_id: str, cache_path: Path):
        """
        Receives a signal from ThumbnailService when a new thumbnail is ready on disk.
        Updates the internal item model and triggers a targeted UI refresh.
        """
        logger.debug(
            f"Received generated thumbnail for item '{item_id}' at '{cache_path}'"
        )
        try:
            # 1. Find the appropriate item in Master_list

            item_to_update = next(
                item for item in self.master_list if item.id == item_id
            )
            if not item_to_update:
                logger.warning(
                    f"Item '{item_id}' no longer in list when its thumbnail was ready."
                )
                return

            updated_item = item_to_update

            # ---Revised Logic: Check Item Type Before Updating ---
            # 2. Only update the model if it is Objectitem

            if isinstance(item_to_update, ObjectItem):
                # Update the thumbnail_path to point to the new cache file.
                # This helps in case of a full refresh, it can load from cache directly.

                updated_item = dataclasses.replace(
                    item_to_update, thumbnail_path=cache_path
                )

                # Replace the old item with the new one in the internal state

                master_idx = self.master_list.index(item_to_update)
                self.master_list[master_idx] = updated_item

                if item_to_update in self.displayed_items:
                    display_idx = self.displayed_items.index(item_to_update)
                    self.displayed_items[display_idx] = updated_item

            # For FolderItem, we don't need to change the model. The fact that the
            # thumbnail exists in the cache is enough. We just need to trigger a UI update.

            # 4. Use the existing 'item_needs_update' signal to trigger UI refresh
            #    targeted to just one widget.

            view_data = self._create_dict_from_item(updated_item)
            self.item_needs_update.emit(view_data)

        except (StopIteration, ValueError):
            logger.warning(
                f"Item '{item_id}' not found in list when its thumbnail was ready. It may have been unloaded."
            )
