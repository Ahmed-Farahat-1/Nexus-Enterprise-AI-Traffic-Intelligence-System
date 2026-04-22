"""
Control Panel — Buttons, inputs, and feature toggles.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QCheckBox, QGroupBox, QLabel, QFrame,
    QComboBox, QSlider,
)
from PyQt6.QtCore import pyqtSignal, Qt

from utils.constants import (
    DIRECTION_MODE_STANDARD, DIRECTION_MODE_REVERSED,
    DIRECTION_MODE_LABELS,
)


class ControlPanel(QWidget):
    """
    Control panel with video source buttons, IP camera input,
    transport controls (pause/resume/stop), and feature toggles.
    """

    # Signals
    start_camera_clicked = pyqtSignal()
    upload_video_clicked = pyqtSignal()
    connect_ip_clicked = pyqtSignal(str)  # emits URL
    stop_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()

    # Feature toggles
    speed_toggled = pyqtSignal(bool)
    wrong_way_toggled = pyqtSignal(bool)
    density_toggled = pyqtSignal(bool)

    # Direction mode changed — emits mode key string ("standard" / "reversed")
    direction_mode_changed = pyqtSignal(str)

    # Adjustable line divider — emits float 0.1 to 0.9
    divider_slider_moved = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_paused = False
        self._setup_ui()
        self._connect_signals()
        self.set_stopped_state()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # --- Source Controls ---
        source_group = QGroupBox("  VIDEO SOURCE")
        source_layout = QVBoxLayout(source_group)
        source_layout.setSpacing(8)

        self.btn_start_camera = QPushButton("▶  Start Camera")
        self.btn_start_camera.setObjectName("btn_start_camera")
        self.btn_start_camera.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_upload = QPushButton("📁  Upload Video")
        self.btn_upload.setObjectName("btn_upload")
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)

        # IP Camera row
        ip_row = QHBoxLayout()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("rtsp://camera-url...")
        self.btn_connect_ip = QPushButton("🔗  Connect")
        self.btn_connect_ip.setObjectName("btn_connect_ip")
        self.btn_connect_ip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect_ip.setMinimumWidth(100)
        ip_row.addWidget(self.ip_input, 1)
        ip_row.addWidget(self.btn_connect_ip)

        source_layout.addWidget(self.btn_start_camera)
        source_layout.addWidget(self.btn_upload)
        source_layout.addLayout(ip_row)

        layout.addWidget(source_group)

        # --- Transport Controls ---
        transport_group = QGroupBox("  CONTROLS")
        transport_layout = QHBoxLayout(transport_group)
        transport_layout.setSpacing(8)

        self.btn_pause = QPushButton("⏸  Pause")
        self.btn_pause.setObjectName("btn_pause")
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_stop = QPushButton("⏹  Stop")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)

        transport_layout.addWidget(self.btn_pause)
        transport_layout.addWidget(self.btn_stop)

        layout.addWidget(transport_group)

        # --- Feature Toggles & Direction Mode ---
        toggle_group = QGroupBox("  FEATURES")
        toggle_layout = QVBoxLayout(toggle_group)
        toggle_layout.setSpacing(6)

        # Direction mode dropdown
        direction_label = QLabel("🔄  Traffic Direction Mode")
        direction_label.setStyleSheet("font-weight: 600; font-size: 12px; background: transparent;")
        toggle_layout.addWidget(direction_label)

        self.combo_direction = QComboBox()
        self.combo_direction.setObjectName("combo_direction")
        self.combo_direction.setCursor(Qt.CursorShape.PointingHandCursor)
        # Populate with mode labels, storing the mode key in item data
        for mode_key, label in DIRECTION_MODE_LABELS.items():
            self.combo_direction.addItem(label, mode_key)
        toggle_layout.addWidget(self.combo_direction)

        # Current mode indicator
        self.direction_mode_indicator = QLabel(
            f"Active: {DIRECTION_MODE_LABELS[DIRECTION_MODE_STANDARD]}"
        )
        self.direction_mode_indicator.setObjectName("metric_label")
        self.direction_mode_indicator.setStyleSheet(
            "font-size: 10px; color: #8b949e; padding: 2px 0 8px 0; background: transparent;"
        )
        toggle_layout.addWidget(self.direction_mode_indicator)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #30363d; max-height: 1px;")
        toggle_layout.addWidget(sep)

        self.chk_speed = QCheckBox("⚡  Speed Estimation")
        self.chk_speed.setChecked(True)
        self.chk_speed.setCursor(Qt.CursorShape.PointingHandCursor)

        self.chk_wrong_way = QCheckBox("🚨  Wrong-Way Detection")
        self.chk_wrong_way.setChecked(True)
        self.chk_wrong_way.setCursor(Qt.CursorShape.PointingHandCursor)

        self.chk_density = QCheckBox("🚦  Density Analysis")
        self.chk_density.setChecked(True)
        self.chk_density.setCursor(Qt.CursorShape.PointingHandCursor)

        toggle_layout.addWidget(self.chk_speed)
        toggle_layout.addWidget(self.chk_wrong_way)
        toggle_layout.addWidget(self.chk_density)

        # Separator line
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background-color: #30363d; max-height: 1px;")
        toggle_layout.addWidget(sep2)

        # Interactive Lane Divider Slider
        slider_label = QLabel("↔️  Lane Divider Position")
        slider_label.setStyleSheet("font-weight: 600; font-size: 11px; background: transparent;")
        toggle_layout.addWidget(slider_label)

        self.slider_divider = QSlider(Qt.Orientation.Horizontal)
        self.slider_divider.setMinimum(10)
        self.slider_divider.setMaximum(90)
        self.slider_divider.setValue(50)  # Center default
        self.slider_divider.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_layout.addWidget(self.slider_divider)

        layout.addWidget(toggle_group)
        layout.addStretch()

    def _connect_signals(self):
        self.btn_start_camera.clicked.connect(self.start_camera_clicked)
        self.btn_upload.clicked.connect(self.upload_video_clicked)
        self.btn_connect_ip.clicked.connect(
            lambda: self.connect_ip_clicked.emit(self.ip_input.text().strip())
        )
        self.btn_stop.clicked.connect(self.stop_clicked)
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.chk_speed.toggled.connect(self.speed_toggled)
        self.chk_wrong_way.toggled.connect(self.wrong_way_toggled)
        self.chk_density.toggled.connect(self.density_toggled)

        # Direction mode combo
        self.combo_direction.currentIndexChanged.connect(self._on_direction_mode_changed)

        # Divider slider
        self.slider_divider.valueChanged.connect(self._on_slider_moved)

    def _on_slider_moved(self, value: int):
        self.divider_slider_moved.emit(value / 100.0)

    def _toggle_pause(self):
        self._is_paused = not self._is_paused
        if self._is_paused:
            self.btn_pause.setText("▶  Resume")
        else:
            self.btn_pause.setText("⏸  Pause")
        self.pause_clicked.emit()

    def _on_direction_mode_changed(self, index: int):
        """Handle direction mode dropdown change."""
        mode_key = self.combo_direction.itemData(index)
        mode_label = self.combo_direction.itemText(index)
        # Update indicator label
        self.direction_mode_indicator.setText(f"Active: {mode_label}")
        # Emit signal with mode key
        self.direction_mode_changed.emit(mode_key)

    def set_running_state(self):
        """Update button states when processing is active."""
        self.btn_start_camera.setEnabled(False)
        self.btn_upload.setEnabled(False)
        self.btn_connect_ip.setEnabled(False)
        self.ip_input.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self._is_paused = False
        self.btn_pause.setText("⏸  Pause")

    def set_stopped_state(self):
        """Update button states when processing is stopped."""
        self.btn_start_camera.setEnabled(True)
        self.btn_upload.setEnabled(True)
        self.btn_connect_ip.setEnabled(True)
        self.ip_input.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self._is_paused = False
        self.btn_pause.setText("⏸  Pause")
