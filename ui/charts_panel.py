"""
Charts Panel — Real-time graphs using pyqtgraph for live traffic analytics.

Three charts:
1. Vehicle Count over Time
2. Average Speed over Time
3. Traffic Density Trend
"""

import time
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox
from PyQt6.QtGui import QColor, QFont

from utils.constants import (
    CHART_MAX_POINTS, CHART_BG_COLOR, CHART_GRID_COLOR,
    CHART_AXIS_COLOR, CHART_LINE_VEHICLE, CHART_LINE_SPEED,
    CHART_LINE_DENSITY, FONT_FAMILY,
)


# Map density strings to numeric values for plotting
DENSITY_MAP = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "TRAFFIC JAM": 4,
}


class ChartsPanel(QWidget):
    """
    Real-time analytics charts panel with three plots.
    Uses pyqtgraph for GPU-accelerated, low-latency rendering.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_time = time.time()

        # Data buffers
        self._times = []
        self._vehicle_counts = []
        self._avg_speeds = []
        self._density_values = []

        self._setup_ui()

    def _create_plot(self, title: str, y_label: str, color: str) -> tuple:
        """Create a styled pyqtgraph PlotWidget."""
        plot_widget = pg.PlotWidget()

        # Dark theme styling
        plot_widget.setBackground(QColor(CHART_BG_COLOR))
        plot_widget.showGrid(x=True, y=True, alpha=0.15)
        plot_widget.setTitle(title, color=CHART_AXIS_COLOR, size="11px")
        plot_widget.setMinimumHeight(110)
        plot_widget.setMaximumHeight(160)

        # Axis styling
        axis_font = QFont(FONT_FAMILY, 8)
        for axis_name in ['left', 'bottom']:
            axis = plot_widget.getAxis(axis_name)
            axis.setPen(pg.mkPen(color=CHART_AXIS_COLOR, width=1))
            axis.setTextPen(pg.mkPen(color=CHART_AXIS_COLOR))
            axis.setTickFont(axis_font)

        plot_widget.getAxis('left').setLabel(y_label, color=CHART_AXIS_COLOR)
        plot_widget.getAxis('bottom').setLabel("Time (s)", color=CHART_AXIS_COLOR)

        # Disable mouse interaction for cleaner look
        plot_widget.setMouseEnabled(x=False, y=False)
        plot_widget.hideButtons()

        # Create curve
        pen = pg.mkPen(color=QColor(color), width=2)
        curve = plot_widget.plot([], [], pen=pen)

        return plot_widget, curve

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        group = QGroupBox("  ANALYTICS")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(4)
        group_layout.setContentsMargins(8, 20, 8, 8)

        # Vehicle Count chart
        self.plot_vehicles, self.curve_vehicles = self._create_plot(
            "Vehicle Count", "Count", CHART_LINE_VEHICLE
        )
        group_layout.addWidget(self.plot_vehicles)

        # Average Speed chart
        self.plot_speed, self.curve_speed = self._create_plot(
            "Average Speed (km/h)", "Speed", CHART_LINE_SPEED
        )
        group_layout.addWidget(self.plot_speed)

        # Density Trend chart
        self.plot_density, self.curve_density = self._create_plot(
            "Traffic Density", "Level", CHART_LINE_DENSITY
        )
        # Custom Y-axis ticks for density
        self.plot_density.getAxis('left').setTicks([
            [(1, "LOW"), (2, "MED"), (3, "HIGH"), (4, "JAM")]
        ])
        self.plot_density.setYRange(0.5, 4.5, padding=0)
        group_layout.addWidget(self.plot_density)

        layout.addWidget(group)

    def update_data(self, vehicle_count: int, avg_speed: float, density: str):
        """Append new data point and refresh all three charts."""
        t = time.time() - self._start_time

        self._times.append(t)
        self._vehicle_counts.append(vehicle_count)
        self._avg_speeds.append(avg_speed)
        self._density_values.append(DENSITY_MAP.get(density, 1))

        # Trim to max points
        if len(self._times) > CHART_MAX_POINTS:
            self._times = self._times[-CHART_MAX_POINTS:]
            self._vehicle_counts = self._vehicle_counts[-CHART_MAX_POINTS:]
            self._avg_speeds = self._avg_speeds[-CHART_MAX_POINTS:]
            self._density_values = self._density_values[-CHART_MAX_POINTS:]

        # Update curves
        self.curve_vehicles.setData(self._times, self._vehicle_counts)
        self.curve_speed.setData(self._times, self._avg_speeds)
        self.curve_density.setData(self._times, self._density_values)

    def reset(self):
        """Clear all chart data."""
        self._start_time = time.time()
        self._times.clear()
        self._vehicle_counts.clear()
        self._avg_speeds.clear()
        self._density_values.clear()

        self.curve_vehicles.setData([], [])
        self.curve_speed.setData([], [])
        self.curve_density.setData([], [])
