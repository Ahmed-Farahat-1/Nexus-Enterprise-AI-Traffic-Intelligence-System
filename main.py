"""
Traffic Intelligence System — Entry Point

A real-time desktop application for AI-powered traffic monitoring
using YOLOv8 + ByteTrack with a modern dark-themed dashboard.

v2.0: Multi-model pipeline with BLIP, EasyOCR, CLIP, and BEV
      calibrated speed estimation.

Usage:
    python main.py
"""

import sys
import logging

# Configure logging for the multi-model pipeline
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow


def main():
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Global font
    font = QFont("Segoe UI", 11)
    app.setFont(font)

    # Launch main window
    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
