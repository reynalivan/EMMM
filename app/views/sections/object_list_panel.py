# app/views/sections/object_list_panel.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
# Tambahkan import QPixmap
from PyQt6.QtGui import QPixmap
from app.viewmodels.object_list_vm import ObjectListVM
from app.views.components.object_list_item_widget import ObjectListItemWidget
# Hapus import ThumbnailService jika ada
# from app.services.thumbnail_service import ThumbnailService
from app.utils.logger_utils import logger
import os  # Import os untuk os.path.exists


class ObjectListPanel(QWidget):

    # Pastikan __init__ tidak lagi menerima thumbnail_service
    def __init__(self, view_model: ObjectListVM, parent: QWidget | None = None):
        super().__init__(parent)
        self.vm = view_model
        # self.thumbnail_service = thumbnail_service # Hapus jika ada
        self.list_widget = QListWidget()
        # TODO: Add filter/search/bulk widgets

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        self._connect_signals()
        logger.debug("ObjectListPanel initialized.")

    def _connect_signals(self):
        logger.debug("Connecting ObjectListPanel signals...")
        try:
            self.vm.displayListChanged.connect(self._update_display_list)
            # --- START MODIFICATION: Connect itemNeedsUpdate ---
            self.vm.itemNeedsUpdate.connect(self._update_specific_item)
            # --- END MODIFICATION ---
            self.list_widget.itemClicked.connect(self._on_item_clicked)
            # TODO: Connect other VM signals (loading, error) and UI signals
        except AttributeError as e:
            logger.error(f"Error connecting signals in ObjectListPanel: {e}")

    def _update_display_list(self, items: list):
        """Populates the list widget with items from the ViewModel."""
        logger.debug(
            f"ObjectListPanel: Updating display list with {len(items)} items.")
        # Disconnect signals temporarily to avoid issues during clear/repopulation? Optional.
        # self.list_widget.itemClicked.disconnect(self._on_item_clicked)
        self.list_widget.clear()

        if not items:
            logger.debug("ObjectListPanel: Display list is empty.")
            # Reconnect signal if disconnected
            # self.list_widget.itemClicked.connect(self._on_item_clicked)
            return

        for item_model in items:
            list_item = QListWidgetItem()
            # Widget sekarang hanya butuh model
            widget = ObjectListItemWidget(item_model)
            list_item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)

            # --- START MODIFICATION: Trigger thumbnail request for every item ---
            # Temporary approach without lazy loading: request all thumbs now
            self.vm.request_thumbnail_for(item_model)
            # --- END MODIFICATION ---

        # Reconnect signal if disconnected
        # self.list_widget.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handles clicking on an item in the list."""
        widget = self.list_widget.itemWidget(item)
        # Gunakan isinstance untuk memastikan tipe widget benar
        if isinstance(widget, ObjectListItemWidget):
            model = widget.get_item_model()
            logger.debug(f"ObjectListPanel: Item clicked - {model.path}")
            self.vm.select_object_item(model)

    # --- START MODIFICATION: Add slot to handle thumbnail updates ---
    def _update_specific_item(self, item_path: str, thumb_result: dict):
        """
        Slot to update a specific item's thumbnail when vm.itemNeedsUpdate is emitted.
        """
        # logger.debug(f"Panel trying to update item: {item_path} with result status: {thumb_result.get('status')}") # Keep lean

        # Inefficient search required by QListWidget + setItemWidget approach
        for i in range(self.list_widget.count()):
            list_item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(list_item)

            # Check if widget is correct type and its model path matches
            if isinstance(widget, ObjectListItemWidget
                          ) and widget.get_item_model().path == item_path:
                thumbnail_path = thumb_result.get('path')
                status = thumb_result.get('status')
                pixmap = None  # Default to None

                # Try to load pixmap only if status is good and path exists
                if status in ['hit', 'generated'] and thumbnail_path:
                    # Double check path exists before creating QPixmap
                    if os.path.exists(thumbnail_path):
                        try:
                            pixmap = QPixmap(thumbnail_path)
                            if pixmap.isNull():
                                logger.warning(
                                    f"Panel: QPixmap loaded as NULL for path {thumbnail_path}"
                                )
                                pixmap = None  # Reset if loading failed
                        except Exception as e:
                            logger.error(
                                f"Panel: Error creating QPixmap for {thumbnail_path}: {e}"
                            )
                            pixmap = None  # Reset on error
                    # else: logger.warning(f"Panel: Thumbnail path received but does not exist: {thumbnail_path}") # Keep lean

                # Update the widget's thumbnail (pass None if pixmap failed or status was bad)
                widget.set_thumbnail(pixmap)
                # logger.debug(f"Panel updated widget for {item_path}") # Keep lean
                return  # Stop searching once found and updated

        # logger.warning(f"Panel: Widget for path {item_path} not found for update.") # Keep lean

    # --- END MODIFICATION ---

    # TODO: Implement other slots like _show_loading, _show_error
