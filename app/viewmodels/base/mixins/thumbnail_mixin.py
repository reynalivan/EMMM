# app/viewmodels/mixins/thumbnail_mixin.py

from typing import Union
from app.models.object_item_model import ObjectItemModel
from app.models.folder_item_model import FolderItemModel
from app.utils.logger_utils import logger
from app.utils.signal_utils import safe_connect

ItemModelType = Union[ObjectItemModel, FolderItemModel]


class ThumbnailMixin:
    """
    Mixin to handle thumbnail logic:
    - request from service
    - emit update signal
    - reload/update specific item
    """

    # Expected members from parent:
    # - self._thumbnail_service
    # - self.itemThumbnailNeedsUpdate (pyqtSignal)
    # - self._get_item_type()

    def _connect_thumbnail_signal(self):
        if not self._thumbnail_service:
            logger.warning(
                "ThumbnailMixin: No thumbnail service found in parent class."
            )
            return
        safe_connect(
            self._thumbnail_service.thumbnailReady,
            self._on_thumbnail_ready,
            self,
        )

    def request_thumbnail_for(self, item_model: ItemModelType):
        """Request or emit cached thumbnail for a given item."""
        if not item_model or not self._thumbnail_service:
            return

        cached = self._thumbnail_service.get_cached_thumbnail(
            item_model.path, self._get_item_type()
        )
        if cached:
            self.itemThumbnailNeedsUpdate.emit(item_model.path, cached)
            return
        else:
            self._thumbnail_service.request_thumbnail(
                item_model.path, self._get_item_type()
            )

    def _on_thumbnail_ready(self, item_path: str, result: dict):
        """Handles thumbnail results and emits signal for UI update."""
        # logger.debug(f"Thumbnail ready for: {item_path}")
        self.itemThumbnailNeedsUpdate.emit(item_path, result)
