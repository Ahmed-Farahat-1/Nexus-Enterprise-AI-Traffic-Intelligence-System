"""
Vehicle Table Panel — Live dashboard table with persistent session data.

v2.1 Changes:
    - FIXED: Accepts session_data dict instead of per-frame vehicle list.
    - FIXED: Uses setUpdatesEnabled() to prevent table flickering.
    - FIXED: Shows active vehicles + recently-seen vehicles (dimmed).
    - FIXED: In-place cell updates (reuses QTableWidgetItems).
    - Columns: Track ID | Speed | Direction | Type & Color | Plate | Driver Status
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QFont

from typing import List, Dict

from utils.constants import (
    THEME_DANGER, THEME_WARNING, THEME_SUCCESS,
    THEME_TEXT_PRIMARY, THEME_ACCENT,
    VEHICLE_ACTIVE_TIMEOUT_FRAMES,
)


# Row background colors for behaviors
BEHAVIOR_ROW_COLORS = {
    "WRONG WAY": QColor(248, 81, 73, 40),      # Red tint
    "SUDDEN STOP": QColor(210, 153, 34, 40),    # Orange tint
    "STOPPED": QColor(100, 100, 100, 20),       # Dim gray
}

# Text accent colors for behaviors
BEHAVIOR_TEXT_COLORS = {
    "WRONG WAY": QColor(THEME_DANGER),
    "SUDDEN STOP": QColor(THEME_WARNING),
    "NORMAL": QColor(THEME_SUCCESS),
    "SLOW": QColor("#d29922"),
    "STOPPED": QColor("#6e7681"),
}

# Direction display
DIRECTION_ARROWS = {
    "UP": "↑ UP",
    "DOWN": "↓ DOWN",
    "UNKNOWN": "— —",
}

# Inactive vehicle styling
INACTIVE_BG = QColor(40, 42, 48, 15)
INACTIVE_FG = QColor("#4a4f57")


class VehicleTablePanel(QWidget):
    """
    Live vehicle dashboard table with 6 columns.

    v2.1: Updated via session_data dict for persistent, flicker-free display.
    Shows both active (live) and recently-seen (dimmed) vehicles.
    """

    COLUMNS = [
        "Track ID",
        "Speed (km/h)",
        "Direction",
        "Type & Color",
        "Plate Number",
        "Driver Status",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("  🚗 VEHICLE DASHBOARD")
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(8, 20, 8, 8)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(180)
        self.table.setMaximumHeight(300)

        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)     # Track ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)     # Speed
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)     # Direction
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)   # Type & Color
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)   # Plate
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)   # Driver Status

        self.table.setColumnWidth(0, 70)    # Track ID
        self.table.setColumnWidth(1, 95)    # Speed
        self.table.setColumnWidth(2, 85)    # Direction

        group_layout.addWidget(self.table)
        layout.addWidget(group)

    # ==========================================
    # 📊 SESSION-BASED UPDATE (v2.1 — flicker-free)
    # ==========================================

    def update_from_session(self, session_data: dict, current_frame: int):
        """
        Update table from persistent session_data dictionary.

        Shows active vehicles and recently-seen vehicles (within the
        VEHICLE_ACTIVE_TIMEOUT_FRAMES window). Uses setUpdatesEnabled()
        to batch all visual changes into a single repaint, eliminating
        flickering.

        Args:
            session_data: Dict[track_id, vehicle_dict] from VideoThread.
            current_frame: Current video frame number for timeout calc.
        """
        # --- Prevent flickering: suspend repaints during update ---
        self.table.setUpdatesEnabled(False)

        try:
            # Filter: show active + recently-seen vehicles
            display = []
            for tid, v in session_data.items():
                frames_since = current_frame - v.get("last_seen_frame", 0)
                is_active = v.get("active", False)
                if is_active or frames_since <= VEHICLE_ACTIVE_TIMEOUT_FRAMES:
                    display.append((v, is_active))

            # Sort: active first (by track ID), then inactive (by track ID)
            display.sort(key=lambda x: (not x[1], x[0]["track_id"]))

            # Resize only when vehicle count changes (avoids full rebuild)
            if self.table.rowCount() != len(display):
                self.table.setRowCount(len(display))

            for row, (v, is_active) in enumerate(display):
                behavior = v.get("behavior", "NORMAL")

                # Speed: show live speed for active, avg for inactive
                if is_active:
                    speed_text = f"{v['speed_kmh']}"
                else:
                    speed_text = f"avg {v.get('avg_speed_kmh', 0)}"

                items_data = [
                    str(v["track_id"]),
                    speed_text,
                    DIRECTION_ARROWS.get(v.get("direction", "UNKNOWN"), "— —"),
                    v.get("vehicle_desc", "⏳"),
                    v.get("plate_number", "—"),
                    v.get("driver_status", "N/A"),
                ]

                # Row background based on behavior or inactive state
                if is_active:
                    bg_color = BEHAVIOR_ROW_COLORS.get(behavior, QColor(0, 0, 0, 0))
                else:
                    bg_color = INACTIVE_BG

                behavior_color = BEHAVIOR_TEXT_COLORS.get(
                    behavior, QColor(THEME_TEXT_PRIMARY)
                )

                for col, text in enumerate(items_data):
                    # Reuse existing QTableWidgetItem or create new one
                    item = self.table.item(row, col)
                    if item is None:
                        item = QTableWidgetItem(text)
                        self.table.setItem(row, col, item)
                    else:
                        # Only update text if changed (reduces paint events)
                        if item.text() != text:
                            item.setText(text)

                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setBackground(QBrush(bg_color))

                    # --- Inactive vehicles: dim all text ---
                    if not is_active:
                        item.setForeground(QBrush(INACTIVE_FG))
                        font = item.font()
                        font.setBold(False)
                        item.setFont(font)
                        continue

                    # --- Active vehicle column-specific styling ---
                    if col == 0:  # Track ID — bold accent
                        item.setForeground(QBrush(QColor(THEME_ACCENT)))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)

                    elif col == 1:  # Speed — color by behavior
                        item.setForeground(QBrush(behavior_color))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)

                    elif col == 2:  # Direction — color by direction
                        direction = v.get("direction", "UNKNOWN")
                        if direction == "UP":
                            item.setForeground(QBrush(QColor("#58a6ff")))
                        elif direction == "DOWN":
                            item.setForeground(QBrush(QColor("#3fb950")))
                        else:
                            item.setForeground(QBrush(QColor("#6e7681")))

                    elif col == 3:  # Type & Color
                        desc = v.get("vehicle_desc", "⏳")
                        if desc in ("⏳", "Unknown"):
                            item.setForeground(QBrush(QColor("#6e7681")))
                        else:
                            item.setForeground(QBrush(QColor("#e6edf3")))

                    elif col == 4:  # Plate Number
                        plate = v.get("plate_number", "—")
                        if plate and plate not in ("—", "Unreadable"):
                            item.setForeground(QBrush(QColor("#39d2c0")))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        else:
                            item.setForeground(QBrush(QColor("#6e7681")))
                            font = item.font()
                            font.setBold(False)
                            item.setFont(font)

                    elif col == 5:  # Driver Status
                        status = v.get("driver_status", "N/A")
                        if any(x in status for x in ("N/A", "?", "Unknown")):
                            item.setForeground(QBrush(QColor("#6e7681")))
                        elif "❌" in status:
                            item.setForeground(QBrush(QColor(THEME_DANGER)))
                        else:
                            item.setForeground(QBrush(QColor(THEME_SUCCESS)))

        finally:
            # --- Resume repaints: single composite repaint ---
            self.table.setUpdatesEnabled(True)

    def clear(self):
        """Clear all vehicle rows."""
        self.table.setRowCount(0)
