"""
Statistics Panel — Live metric cards showing Vehicle Count, Average Speed,
and Traffic Density with color-coded badges.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QGroupBox,
)
from PyQt6.QtCore import Qt

from utils.constants import (
    THEME_BG_CARD, THEME_BORDER, THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY, THEME_ACCENT,
    COLOR_DENSITY_LOW, COLOR_DENSITY_MEDIUM,
    COLOR_DENSITY_HIGH, COLOR_DENSITY_JAM,
)


class MetricCard(QFrame):
    """A single metric display card with icon, value, and label."""

    def __init__(self, icon: str, label: str, initial_value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("card_frame")
        self._setup_ui(icon, label, initial_value)

    def _setup_ui(self, icon: str, label: str, initial_value: str):
        self.setStyleSheet(
            f"QFrame#card_frame {{ "
            f"  background-color: {THEME_BG_CARD}; "
            f"  border: 1px solid {THEME_BORDER}; "
            f"  border-radius: 12px; "
            f"  padding: 16px; "
            f"}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Icon + label row
        header = QLabel(f"{icon}  {label}")
        header.setObjectName("metric_label")
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(header)

        # Large value
        self.value_label = QLabel(initial_value)
        self.value_label.setObjectName("metric_value")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)

    def set_value_color(self, color: str):
        self.value_label.setStyleSheet(
            f"font-size: 28px; font-weight: 800; color: {color}; background: transparent;"
        )


class StatsPanel(QWidget):
    """Three metric cards showing Vehicle Count, Average Speed, and Traffic Density."""

    DENSITY_COLORS = {
        "LOW": COLOR_DENSITY_LOW,
        "MEDIUM": COLOR_DENSITY_MEDIUM,
        "HIGH": COLOR_DENSITY_HIGH,
        "TRAFFIC JAM": COLOR_DENSITY_JAM,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("  LIVE STATISTICS")
        cards_layout = QHBoxLayout(group)
        cards_layout.setSpacing(8)

        self.card_vehicles = MetricCard("🚗", "VEHICLES", "0")
        self.card_speed = MetricCard("⚡", "AVG SPEED", "0 km/h")
        self.card_density = MetricCard("🚦", "DENSITY", "LOW")

        # Set default density color
        self.card_density.set_value_color(COLOR_DENSITY_LOW)

        cards_layout.addWidget(self.card_vehicles)
        cards_layout.addWidget(self.card_speed)
        cards_layout.addWidget(self.card_density)

        layout.addWidget(group)

    def update_stats(self, vehicle_count: int, avg_speed: float, density: str):
        """Update all three metric cards."""
        self.card_vehicles.set_value(str(vehicle_count))
        self.card_speed.set_value(f"{avg_speed} km/h")
        self.card_density.set_value(density)

        # Color-code density
        color = self.DENSITY_COLORS.get(density, COLOR_DENSITY_LOW)
        self.card_density.set_value_color(color)
