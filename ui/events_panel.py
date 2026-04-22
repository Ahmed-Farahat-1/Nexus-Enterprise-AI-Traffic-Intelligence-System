"""
Events Panel — Live event log table showing traffic incidents.

v2.0 Changes:
    - Expanded columns to include Vehicle Description and Plate Number.
    - Now shows 6 columns: Vehicle ID | Event Type | Timestamp | Lane | Description | Plate

Displays a scrolling table of detected events (Wrong Way, Sudden Stop)
with color-coded rows and auto-scroll.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

from utils.constants import (
    MAX_EVENT_LOG_ROWS, THEME_DANGER, THEME_WARNING,
    THEME_TEXT_PRIMARY, THEME_BG_SECONDARY,
)


# Row background colors (with transparency)
EVENT_COLORS = {
    "WRONG WAY": QColor(248, 81, 73, 40),     # Red tint
    "SUDDEN STOP": QColor(210, 153, 34, 40),   # Orange tint
}

# Text accent colors
EVENT_TEXT_COLORS = {
    "WRONG WAY": QColor(THEME_DANGER),
    "SUDDEN STOP": QColor(THEME_WARNING),
}


class EventsPanel(QWidget):
    """
    Live event log table with columns:
    Vehicle ID | Event Type | Timestamp | Lane | Description | Plate

    v2.0: Added Description and Plate columns from slave model results.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("  🚨 EVENTS & ALERTS")
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(8, 20, 8, 8)

        # --- CHANGED: Expanded from 4 to 6 columns ---
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Vehicle ID", "Event Type", "Timestamp", "Lane",
            "Description", "Plate",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(150)

        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(5, 100)

        group_layout.addWidget(self.table)
        layout.addWidget(group)

    def add_event(
        self,
        vehicle_id: int,
        event_type: str,
        timestamp: str,
        lane: str,
        vehicle_desc: str = "",
        plate_number: str = "",
    ):
        """
        Add a new event row to the top of the table.

        v2.0: Now accepts vehicle_desc and plate_number from slave models.
        """
        # Remove oldest rows if over max
        while self.table.rowCount() >= MAX_EVENT_LOG_ROWS:
            self.table.removeRow(self.table.rowCount() - 1)

        # Insert at top
        self.table.insertRow(0)

        items = [
            str(vehicle_id),
            event_type,
            timestamp,
            lane,
            vehicle_desc if vehicle_desc else "—",
            plate_number if plate_number else "—",
        ]

        bg_color = EVENT_COLORS.get(event_type, QColor(0, 0, 0, 0))
        text_color = EVENT_TEXT_COLORS.get(event_type, QColor(THEME_TEXT_PRIMARY))

        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setBackground(QBrush(bg_color))

            # Color the event type text
            if col == 1:
                item.setForeground(QBrush(text_color))
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            # Plate number styling
            if col == 5 and text != "—":
                item.setForeground(QBrush(QColor("#39d2c0")))
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            self.table.setItem(0, col, item)

        # Auto-scroll to top
        self.table.scrollToTop()

    def clear(self):
        """Clear all events."""
        self.table.setRowCount(0)
