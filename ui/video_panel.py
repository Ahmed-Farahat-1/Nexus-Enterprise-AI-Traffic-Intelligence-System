"""
Video Display Panel — Shows the live video stream with detection overlays.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from utils.constants import THEME_TEXT_MUTED


class VideoPanel(QWidget):
    """
    Video display widget that renders QImage frames with aspect-ratio
    preservation. Shows a placeholder when no source is active.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Container frame
        self.frame_container = QFrame()
        self.frame_container.setObjectName("video_frame")
        frame_layout = QVBoxLayout(self.frame_container)
        frame_layout.setContentsMargins(4, 4, 4, 4)

        # Video label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setStyleSheet("background-color: #000000; border-radius: 8px;")
        frame_layout.addWidget(self.video_label)

        layout.addWidget(self.frame_container)

        # Show placeholder
        self._show_placeholder()

    def _show_placeholder(self):
        """Display placeholder text when no video is active."""
        self.video_label.setText(
            "🎥  No Video Source Active\n\n"
            "Start a camera, upload a video,\n"
            "or connect to an IP camera."
        )
        self.video_label.setStyleSheet(
            f"background-color: #000000; border-radius: 8px; "
            f"color: {THEME_TEXT_MUTED}; font-size: 16px; font-weight: 600;"
        )

    def update_frame(self, qt_image: QImage):
        """Update the displayed frame, preserving aspect ratio."""
        pixmap = QPixmap.fromImage(qt_image)
        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled)

    def clear(self):
        """Reset to placeholder."""
        self.video_label.clear()
        self._show_placeholder()
