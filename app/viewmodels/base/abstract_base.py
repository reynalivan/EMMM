from abc import ABCMeta, abstractmethod
from typing import Literal, List, Optional, Union
from PyQt6.QtCore import QObject
from app.models.object_item_model import ObjectItemModel
from app.models.folder_item_model import FolderItemModel

ItemModelType = Union[ObjectItemModel, FolderItemModel]


class QObjectABCMeta(type(QObject), ABCMeta):
    """Custom metaclass to merge QObject and ABCMeta"""

    pass


class QObjectAbstractItemViewModel(QObject, metaclass=QObjectABCMeta):
    """Base class that supports both QObject and abstract base class behavior."""

    @abstractmethod
    def _get_item_list(self) -> List[ItemModelType]: ...

    @abstractmethod
    def _get_item_type(self) -> Literal["object", "folder"]: ...

    @abstractmethod
    def _filter_and_sort(self): ...

    @abstractmethod
    def _load_items_for_path(self, path: Optional[str]): ...

    @abstractmethod
    def _get_current_path_context(self) -> Optional[str]: ...

    @abstractmethod
    def _after_mod_status_change(self, orig_path: str, new_path: str, result: dict): ...
