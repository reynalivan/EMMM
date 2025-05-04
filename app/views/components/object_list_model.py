from app.models.object_item_model import ObjectItemModel
from PyQt6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    Qt,
)


class ObjectListModel(QAbstractListModel):
    def __init__(self, items: list[ObjectItemModel], parent=None):
        super().__init__(parent)
        self._items = items

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role=int(Qt.ItemDataRole.UserRole)):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        if role == int(Qt.ItemDataRole.UserRole):
            return self._items[index.row()]
        return None

    def update_items(self, items: list[ObjectItemModel]):
        self.beginResetModel()
        self._items = items
        self.endResetModel()
