# app/views/components/object_list_delegate.py
from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtCore import QSize, Qt

from app.views.components.object_list_item_widget import ObjectListItemWidget


class ObjectListDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        model = index.data(Qt.ItemDataRole.UserRole)
        if model:
            return ObjectListItemWidget(model).sizeHint()
        return super().sizeHint(option, index)
