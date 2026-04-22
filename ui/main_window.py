"""
Main Window — Root window that assembles all panels into the Traffic
Intelligence System dashboard layout.

v2.0 Changes:
    - Added VehicleTablePanel for rich per-vehicle data display.
    - Wired FrameResult.vehicles to the vehicle table.
    - Updated events panel to pass vehicle_desc and plate_number.
    - Added model loading progress indicator.

Layout:
┌──────────────────────────────────────────────────┐
│  TOP BAR: Title | Status | FPS                   │
├──────────────────────┬───────────────────────────┤
│                      │  Control Panel             │
│                      ├───────────────────────────┤
│   Video Panel        │  Stats Panel (3 cards)     │
│   (65% width)        ├───────────────────────────┤
│                      │  Vehicle Dashboard (NEW)   │
│                      ├───────────────────────────┤
│                      │  Charts Panel (3 graphs)   │
│                      ├───────────────────────────┤
│                      │  Events Panel (table)      │
└──────────────────────┴───────────────────────────┘
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLabel, QFrame, QFileDialog, QScrollArea,
    QMessageBox, QApplication, QDialog, QTextBrowser,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from ui.styles import DARK_THEME_QSS
from ui.video_panel import VideoPanel
from ui.control_panel import ControlPanel
from ui.stats_panel import StatsPanel
from ui.charts_panel import ChartsPanel
from ui.events_panel import EventsPanel
from ui.vehicle_table_panel import VehicleTablePanel  # NEW in v2.0

from core.video_thread import VideoThread, SourceType
from core.traffic_analyzer import FrameResult

from utils.constants import (
    APP_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    THEME_SUCCESS, THEME_DANGER, THEME_ACCENT,
    THEME_TEXT_PRIMARY, THEME_TEXT_MUTED,
    THEME_BG_SECONDARY, THEME_BORDER,
    FONT_FAMILY,
    DIRECTION_MODE_LABELS, DIRECTION_MODE_STANDARD,
)


class MainWindow(QMainWindow):
    """
    Root application window for the Traffic Intelligence System.
    Assembles all UI panels, manages the VideoThread lifecycle,
    and wires all signals together.

    v2.0: Added VehicleTablePanel and wired multi-model pipeline data.
    """

    def __init__(self):
        super().__init__()
        self._video_thread = None
        self._setup_window()
        self._setup_ui()
        self._apply_theme()

    def _setup_window(self):
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

    def _apply_theme(self):
        self.setStyleSheet(DARK_THEME_QSS)

    # ==========================================
    # 🏗️ UI CONSTRUCTION
    # ==========================================

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- TOP BAR ---
        root_layout.addWidget(self._build_top_bar())

        # --- MAIN CONTENT (Splitter) ---
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        # Left: Video Panel
        self.video_panel = VideoPanel()
        splitter.addWidget(self.video_panel)

        # Right: Scrollable control area
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.control_panel = ControlPanel()
        self.stats_panel = StatsPanel()
        self.vehicle_table_panel = VehicleTablePanel()  # NEW in v2.0
        self.charts_panel = ChartsPanel()
        self.events_panel = EventsPanel()

        right_layout.addWidget(self.control_panel)
        right_layout.addWidget(self.stats_panel)
        right_layout.addWidget(self.vehicle_table_panel)  # NEW in v2.0
        right_layout.addWidget(self.charts_panel)
        right_layout.addWidget(self.events_panel)
        right_layout.addStretch()

        right_scroll.setWidget(right_container)
        splitter.addWidget(right_scroll)

        # Set splitter proportions (65:35)
        splitter.setSizes([650, 350])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        content_layout.addWidget(splitter)
        root_layout.addWidget(content_widget, 1)

        # --- Connect control panel signals ---
        self.control_panel.start_camera_clicked.connect(self._on_start_camera)
        self.control_panel.upload_video_clicked.connect(self._on_upload_video)
        self.control_panel.connect_ip_clicked.connect(self._on_connect_ip)
        self.control_panel.stop_clicked.connect(self._on_stop)
        self.control_panel.pause_clicked.connect(self._on_pause)

        self.control_panel.speed_toggled.connect(self._on_toggle_speed)
        self.control_panel.wrong_way_toggled.connect(self._on_toggle_wrong_way)
        self.control_panel.density_toggled.connect(self._on_toggle_density)
        self.control_panel.direction_mode_changed.connect(self._on_direction_mode_changed)
        self.control_panel.divider_slider_moved.connect(self._on_divider_slider_moved)

    def _build_top_bar(self) -> QFrame:
        """Build the top bar with title, status, and FPS."""
        bar = QFrame()
        bar.setObjectName("top_bar")
        bar.setFixedHeight(56)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(20, 0, 20, 0)
        bar_layout.setSpacing(16)

        # Title
        title = QLabel(f"🛡️  {APP_TITLE}")
        title.setObjectName("title_label")
        bar_layout.addWidget(title)

        bar_layout.addStretch()

        # FPS
        self.fps_label = QLabel("FPS: --")
        self.fps_label.setObjectName("fps_label")
        bar_layout.addWidget(self.fps_label)

        # Direction mode indicator in top bar
        self.mode_badge = QLabel(f"Mode: {DIRECTION_MODE_LABELS[DIRECTION_MODE_STANDARD]}")
        self.mode_badge.setStyleSheet(
            f"background-color: rgba(88, 166, 255, 0.12); "
            f"color: {THEME_ACCENT}; border-radius: 10px; "
            f"padding: 4px 10px; font-size: 10px; font-weight: 600;"
            f"background: transparent;"
        )
        bar_layout.addWidget(self.mode_badge)

        # Status indicator
        self.status_dot = QLabel("●")
        self.status_dot.setFixedWidth(20)
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar_layout.addWidget(self.status_dot)

        self.status_label = QLabel("Stopped")
        self.status_label.setObjectName("status_label")
        bar_layout.addWidget(self.status_label)

        self._set_status_stopped()

        return bar

    # ==========================================
    # 🎛️ STATUS HELPERS
    # ==========================================

    def _set_status_running(self):
        self.status_dot.setStyleSheet(
            f"color: {THEME_SUCCESS}; font-size: 18px; background: transparent;"
        )
        self.status_label.setText("Running")
        self.status_label.setStyleSheet(
            f"background-color: rgba(63, 185, 80, 0.15); "
            f"color: {THEME_SUCCESS}; border-radius: 10px; "
            f"padding: 4px 12px; font-size: 12px; font-weight: 600;"
        )

    def _set_status_stopped(self):
        self.status_dot.setStyleSheet(
            f"color: {THEME_DANGER}; font-size: 18px; background: transparent;"
        )
        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet(
            f"background-color: rgba(248, 81, 73, 0.15); "
            f"color: {THEME_DANGER}; border-radius: 10px; "
            f"padding: 4px 12px; font-size: 12px; font-weight: 600;"
        )

    def _set_status_loading(self):
        self.status_dot.setStyleSheet(
            f"color: {THEME_ACCENT}; font-size: 18px; background: transparent;"
        )
        self.status_label.setText("Loading Models…")
        self.status_label.setStyleSheet(
            f"background-color: rgba(88, 166, 255, 0.15); "
            f"color: {THEME_ACCENT}; border-radius: 10px; "
            f"padding: 4px 12px; font-size: 12px; font-weight: 600;"
        )

    # ==========================================
    # 🎬 VIDEO THREAD MANAGEMENT
    # ==========================================

    def _start_thread(self, source_type: SourceType, source_path: str = ""):
        """Create, configure, connect, and start the video thread."""
        # Stop existing thread if any
        self._stop_thread()

        self._video_thread = VideoThread(self)
        self._video_thread.set_source(source_type, source_path)

        # Connect signals
        self._video_thread.frame_ready.connect(self._on_frame_ready)
        self._video_thread.error_occurred.connect(self._on_error)
        self._video_thread.source_ended.connect(self._on_source_ended)
        self._video_thread.model_loaded.connect(self._on_model_loaded)
        self._video_thread.session_update.connect(self._on_session_update)
        self._video_thread.finished_processing.connect(self._on_finished_processing)

        # Update UI state
        self._set_status_loading()
        self.control_panel.set_running_state()
        self.charts_panel.reset()
        self.events_panel.clear()
        self.vehicle_table_panel.clear()  # NEW in v2.0

        self._video_thread.start()

    def _stop_thread(self):
        """Stop the video thread gracefully."""
        if self._video_thread is not None and self._video_thread.isRunning():
            self._video_thread.stop()
            self._video_thread.wait(3000)  # Wait up to 3 seconds
            self._video_thread = None

    # ==========================================
    # 📡 SLOT: Control Panel Actions
    # ==========================================

    def _on_start_camera(self):
        self._start_thread(SourceType.CAMERA)

    def _on_upload_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;All Files (*)",
        )
        if file_path:
            self._start_thread(SourceType.VIDEO_FILE, file_path)

    def _on_connect_ip(self, url: str):
        if not url:
            QMessageBox.warning(self, "Input Required",
                                "Please enter an IP camera URL.")
            return
        self._start_thread(SourceType.IP_CAMERA, url)

    def _on_stop(self):
        self._stop_thread()
        self._set_status_stopped()
        self.control_panel.set_stopped_state()
        self.video_panel.clear()
        self.vehicle_table_panel.clear()  # NEW in v2.0
        self.fps_label.setText("FPS: --")

    def _on_pause(self):
        if self._video_thread is None:
            return
        if self._video_thread.is_paused:
            self._video_thread.resume()
        else:
            self._video_thread.pause()

    def _on_toggle_speed(self, enabled: bool):
        if self._video_thread:
            self._video_thread.analyzer.speed_enabled = enabled

    def _on_toggle_wrong_way(self, enabled: bool):
        if self._video_thread:
            self._video_thread.analyzer.wrong_way_enabled = enabled

    def _on_toggle_density(self, enabled: bool):
        if self._video_thread:
            self._video_thread.analyzer.density_enabled = enabled

    def _on_direction_mode_changed(self, mode_key: str):
        """Update the analyzer's direction mode in real-time (no stream restart)."""
        if self._video_thread:
            self._video_thread.analyzer.direction_mode = mode_key
        label = DIRECTION_MODE_LABELS.get(mode_key, mode_key)
        self.mode_badge.setText(f"Mode: {label}")

    def _on_divider_slider_moved(self, ratio: float):
        """Update the analyzer's dividing lane ratio."""
        if self._video_thread:
            self._video_thread.analyzer.divider_x_ratio = ratio

    # ==========================================
    # 📡 SLOT: Video Thread Signals
    # ==========================================

    def _on_frame_ready(self, qt_image, result: FrameResult):
        """
        Handle a processed frame from the video thread.

        v2.0 Changes:
            - Updates the new VehicleTablePanel with vehicle list.
            - Passes vehicle_desc and plate_number to events panel.
        """
        # Update video display
        self.video_panel.update_frame(qt_image)

        # Update FPS
        self.fps_label.setText(f"FPS: {result.fps}")

        # Update statistics
        self.stats_panel.update_stats(
            result.vehicle_count,
            result.average_speed,
            result.density_status,
        )

        # Vehicle table is now updated via session_update signal (v2.1)

        # Update charts (throttle: every 3rd frame to reduce chart overhead)
        if result.frame_number % 3 == 0:
            self.charts_panel.update_data(
                result.vehicle_count,
                result.average_speed,
                result.density_status,
            )

        # --- CHANGED: Add events with enriched data ---
        for event in result.events:
            self.events_panel.add_event(
                event.vehicle_id,
                event.event_type,
                event.timestamp,
                event.lane,
                vehicle_desc=event.vehicle_desc,
                plate_number=event.plate_number,
            )

    def _on_model_loaded(self):
        """Called when YOLO model finishes loading."""
        self._set_status_running()

    def _on_error(self, message: str):
        """Handle errors from the video thread."""
        self._on_stop()
        QMessageBox.critical(self, "Error", message)

    def _on_source_ended(self):
        """Handle video file reaching the end."""
        self._on_stop()

    # ==========================================
    # 📊 SESSION & SUMMARY (v2.1)
    # ==========================================

    def _on_session_update(self, session_data: dict, current_frame: int):
        """Update vehicle dashboard from persistent session data (flicker-free)."""
        if self._video_thread and self._video_thread.isRunning():
            self.vehicle_table_panel.update_from_session(session_data, current_frame)

    def _on_finished_processing(self, session_data: dict):
        """Handle end-of-session: display summary popup and CSV notification."""
        if not session_data:
            return
        self._show_summary_dialog(session_data)

    def _show_summary_dialog(self, session_data: dict):
        """Display a comprehensive end-of-session summary dialog."""
        total_vehicles = len(session_data)

        # Aggregate statistics
        all_avg_speeds = []
        direction_counts = {"UP": 0, "DOWN": 0, "UNKNOWN": 0}
        detected_plates = []
        wrong_way_count = 0
        sudden_stop_count = 0

        for tid, v in session_data.items():
            avg_spd = v.get("avg_speed_kmh", 0)
            if avg_spd > 0:
                all_avg_speeds.append(avg_spd)

            d = v.get("direction", "UNKNOWN")
            direction_counts[d] = direction_counts.get(d, 0) + 1

            plate = v.get("plate_number", "—")
            if plate and plate not in ("—", "Unreadable", "⏳"):
                desc = v.get("vehicle_desc", "Vehicle")
                detected_plates.append(
                    f"ID {tid} ({desc}): <b>{plate}</b>"
                )

            if v.get("had_wrong_way"):
                wrong_way_count += 1
            if v.get("had_sudden_stop"):
                sudden_stop_count += 1

        avg_speed = (
            round(sum(all_avg_speeds) / len(all_avg_speeds), 1)
            if all_avg_speeds else 0
        )
        max_speed = round(
            max(
                (v.get("max_speed_kmh", 0) for v in session_data.values()),
                default=0,
            ),
            1,
        )

        # Build plates HTML block
        if detected_plates:
            plates_items = "".join(f"<li>{p}</li>" for p in detected_plates)
            plates_html = (
                '<h3 style="color:#39d2c0;margin-top:14px;">'
                '🔢 Detected License Plates</h3>'
                f'<ul style="color:#e6edf3;line-height:1.8;">'
                f'{plates_items}</ul>'
            )
        else:
            plates_html = (
                '<p style="color:#6e7681;margin-top:14px;">'
                'No plates detected in this session.</p>'
            )

        # Alerts HTML
        alerts_html = ""
        if wrong_way_count > 0 or sudden_stop_count > 0:
            alerts_html = (
                '<h3 style="color:#f85149;margin-top:14px;">'
                '🚨 Behavioral Alerts</h3>'
                '<table style="width:100%;border-collapse:collapse;">'
            )
            if wrong_way_count > 0:
                alerts_html += (
                    '<tr><td style="padding:4px;color:#f85149;">'
                    '⚠️ Wrong-Way Vehicles</td>'
                    f'<td style="padding:4px;color:#e6edf3;text-align:right;'
                    f'font-weight:bold;">{wrong_way_count}</td></tr>'
                )
            if sudden_stop_count > 0:
                alerts_html += (
                    '<tr><td style="padding:4px;color:#d29922;">'
                    '🛑 Sudden Stop Vehicles</td>'
                    f'<td style="padding:4px;color:#e6edf3;text-align:right;'
                    f'font-weight:bold;">{sudden_stop_count}</td></tr>'
                )
            alerts_html += '</table>'

        html = f"""
        <div style="font-family:'Segoe UI',sans-serif;padding:8px;">
            <h2 style="color:#58a6ff;text-align:center;margin-bottom:4px;">
                📊 Session Summary Report
            </h2>
            <hr style="border-color:#30363d;">

            <table style="width:100%;border-collapse:collapse;margin:8px 0;">
                <tr>
                    <td style="padding:7px;color:#8b949e;">Total Vehicles Tracked</td>
                    <td style="padding:7px;color:#58a6ff;font-weight:bold;
                        font-size:15px;text-align:right;">{total_vehicles}</td>
                </tr>
                <tr>
                    <td style="padding:7px;color:#8b949e;">Average Speed</td>
                    <td style="padding:7px;color:#3fb950;font-weight:bold;
                        font-size:15px;text-align:right;">{avg_speed} km/h</td>
                </tr>
                <tr>
                    <td style="padding:7px;color:#8b949e;">Max Speed Recorded</td>
                    <td style="padding:7px;color:#f85149;font-weight:bold;
                        font-size:15px;text-align:right;">{max_speed} km/h</td>
                </tr>
            </table>

            <h3 style="color:#d29922;margin-top:14px;">🧭 Direction Breakdown</h3>
            <table style="width:100%;border-collapse:collapse;margin:8px 0;">
                <tr>
                    <td style="padding:4px;color:#58a6ff;">↑ Upstream</td>
                    <td style="padding:4px;color:#e6edf3;text-align:right;">
                        {direction_counts.get('UP', 0)} vehicles</td>
                </tr>
                <tr>
                    <td style="padding:4px;color:#3fb950;">↓ Downstream</td>
                    <td style="padding:4px;color:#e6edf3;text-align:right;">
                        {direction_counts.get('DOWN', 0)} vehicles</td>
                </tr>
            </table>

            {alerts_html}
            {plates_html}

            <hr style="border-color:#30363d;margin-top:14px;">
            <p style="color:#3fb950;text-align:center;font-size:11px;">
                ✅ Summary automatically exported to CSV in project directory
            </p>
        </div>
        """

        dialog = QDialog(self)
        dialog.setWindowTitle("Session Summary — Traffic Intelligence")
        dialog.setMinimumSize(480, 540)
        dialog.setStyleSheet(
            "QDialog { background-color: #161b22; }"
            "QTextBrowser { background-color: #0d1117;"
            " border: 1px solid #30363d; border-radius: 8px; padding: 4px; }"
            "QPushButton { background-color: #21262d; color: #e6edf3;"
            " border: 1px solid #30363d; border-radius: 6px;"
            " padding: 8px 24px; font-weight: 600; }"
            "QPushButton:hover { background-color: #30363d;"
            " border-color: #58a6ff; }"
        )

        dlg_layout = QVBoxLayout(dialog)

        browser = QTextBrowser()
        browser.setHtml(html)
        browser.setOpenExternalLinks(False)
        dlg_layout.addWidget(browser)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(dialog.accept)
        dlg_layout.addWidget(btn_box)

        dialog.exec()

    # ==========================================
    # 🧹 CLEANUP
    # ==========================================

    def closeEvent(self, event):
        """Ensure thread is stopped when window closes."""
        self._stop_thread()
        super().closeEvent(event)
