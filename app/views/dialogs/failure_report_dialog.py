# app/views/dialogs/failure_report_dialog.py

from typing import List, Dict
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidgetItem
from qfluentwidgets import TableWidget, TitleLabel, PushButton

class FailureReportDialog(QDialog):
    """
    A dialog to display a detailed report of items that failed during a
    bulk operation, such as mod creation.
    """

    def __init__(self, failed_items: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Failure Report")
        self.setMinimumSize(600, 400)

        # --- UI Components ---
        title = TitleLabel("Operation Failed for Some Items", self)

        self.report_table = TableWidget(self)
        self.report_table.setColumnCount(2)
        self.report_table.setHorizontalHeaderLabels(["Source File / Folder", "Reason for Failure"])
        self.report_table.horizontalHeader().setStretchLastSection(True)
        self.report_table.setEditTriggers(self.report_table.EditTrigger.NoEditTriggers)

        self.populate_table(failed_items)

        close_button = PushButton("Close")

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        main_layout.addWidget(title)
        main_layout.addWidget(self.report_table, 1)
        main_layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

        # --- Connections ---
        close_button.clicked.connect(self.accept)

    def populate_table(self, failed_items: List[Dict]):
        """Fills the table with the failure data."""
        self.report_table.setRowCount(len(failed_items))
        for row, item in enumerate(failed_items):
            source_name = item.get("source", "Unknown")
            reason = item.get("reason", "No reason provided.")

            self.report_table.setItem(row, 0, QTableWidgetItem(source_name))
            self.report_table.setItem(row, 1, QTableWidgetItem(reason))

        self.report_table.resizeRowsToContents()