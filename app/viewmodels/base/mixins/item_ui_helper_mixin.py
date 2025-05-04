# app/viewmodels/mixins/item_ui_helper_mixin.py

import os
from typing import Union
from app.models.object_item_model import ObjectItemModel
from app.models.folder_item_model import FolderItemModel
from app.utils.logger_utils import logger

ItemModelType = Union[ObjectItemModel, FolderItemModel]


class ItemUIHelperMixin:
    """Mixin for handling add/remove item logic to internal list and displayed_items."""

    # Requires from parent:
    # - self._get_item_list() -> list
    # - self.displayed_items: list
    # - self.request_thumbnail_for(item_model)
    # - self.displayListChanged.emit(items)

    def _insert_item_to_ui(self, item_model: ItemModelType):
        items = self._get_item_list()
        norm_new = os.path.normpath(item_model.path)

        # check for stale insert
        if hasattr(self, "_current_parent_path"):
            current = getattr(self, "_current_parent_path") or ""
            if not norm_new.startswith(os.path.normpath(current)):
                logger.debug(
                    f"{self.__class__.__name__}: Ignored insert from stale path: {norm_new}"
                )
                return

        if any(os.path.normpath(i.path) == norm_new for i in items):
            logger.debug(
                f"{self.__class__.__name__}: Skip insert, already exists: {item_model.path}"
            )
            return

        items.append(item_model)
        if hasattr(self, "displayed_items"):
            self.displayed_items.append(item_model)

        self.request_thumbnail_for(item_model)
        self.displayListChanged.emit(self.displayed_items)

    def _remove_item_from_ui(self, path: str):
        norm_path = os.path.normpath(path)
        items = self._get_item_list()

        removed = [i for i in items if os.path.normpath(i.path) == norm_path]
        if not removed:
            logger.debug(f"{self.__class__.__name__}: No match to remove: {path}")
            return

        for r in removed:
            items.remove(r)
            if hasattr(self, "displayed_items") and r in self.displayed_items:
                self.displayed_items.remove(r)

        logger.info(f"{self.__class__.__name__}: Removed item(s): {path}")
        self.displayListChanged.emit(self.displayed_items)

    def set_loading(self, is_loading: bool):
        """Emit loading state to UI if state changed."""
        if getattr(self, "_is_loading", False) != is_loading:
            self._is_loading = is_loading
            self.loadingStateChanged.emit(is_loading)
