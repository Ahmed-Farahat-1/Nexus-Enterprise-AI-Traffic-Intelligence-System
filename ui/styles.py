"""
QSS Dark Theme Stylesheet for Traffic Intelligence System.

A modern, professional dark theme inspired by GitHub's dark mode
with glassmorphism-influenced card surfaces and clean typography.
"""

from utils.constants import (
    THEME_BG_PRIMARY, THEME_BG_SECONDARY, THEME_BG_TERTIARY,
    THEME_BG_CARD, THEME_BORDER, THEME_BORDER_LIGHT,
    THEME_TEXT_PRIMARY, THEME_TEXT_SECONDARY, THEME_TEXT_MUTED,
    THEME_ACCENT, THEME_ACCENT_HOVER, THEME_SUCCESS, THEME_SUCCESS_HOVER,
    THEME_WARNING, THEME_DANGER, THEME_DANGER_HOVER,
    FONT_FAMILY, FONT_SIZE_NORMAL,
)


DARK_THEME_QSS = f"""
/* ==========================================
   GLOBAL
   ========================================== */
QWidget {{
    background-color: {THEME_BG_PRIMARY};
    color: {THEME_TEXT_PRIMARY};
    font-family: "{FONT_FAMILY}", "Helvetica Neue", Arial, sans-serif;
    font-size: {FONT_SIZE_NORMAL}px;
}}

QMainWindow {{
    background-color: {THEME_BG_PRIMARY};
}}

/* ==========================================
   SCROLL BARS
   ========================================== */
QScrollBar:vertical {{
    background: {THEME_BG_SECONDARY};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {THEME_BORDER_LIGHT};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {THEME_TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: {THEME_BG_SECONDARY};
    height: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {THEME_BORDER_LIGHT};
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {THEME_TEXT_MUTED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ==========================================
   BUTTONS
   ========================================== */
QPushButton {{
    background-color: {THEME_BG_CARD};
    color: {THEME_TEXT_PRIMARY};
    border: 1px solid {THEME_BORDER};
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 12px;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {THEME_BG_TERTIARY};
    border-color: {THEME_BORDER_LIGHT};
}}
QPushButton:pressed {{
    background-color: {THEME_BORDER};
}}
QPushButton:disabled {{
    background-color: {THEME_BG_SECONDARY};
    color: {THEME_TEXT_MUTED};
    border-color: {THEME_BG_CARD};
}}

/* Primary action button */
QPushButton#btn_start_camera {{
    background-color: {THEME_SUCCESS};
    color: #ffffff;
    border: none;
}}
QPushButton#btn_start_camera:hover {{
    background-color: {THEME_SUCCESS_HOVER};
}}
QPushButton#btn_start_camera:disabled {{
    background-color: {THEME_BORDER};
    color: {THEME_TEXT_MUTED};
}}

QPushButton#btn_stop {{
    background-color: {THEME_DANGER};
    color: #ffffff;
    border: none;
}}
QPushButton#btn_stop:hover {{
    background-color: {THEME_DANGER_HOVER};
}}
QPushButton#btn_stop:disabled {{
    background-color: {THEME_BORDER};
    color: {THEME_TEXT_MUTED};
}}

QPushButton#btn_upload {{
    background-color: {THEME_ACCENT};
    color: #ffffff;
    border: none;
}}
QPushButton#btn_upload:hover {{
    background-color: {THEME_ACCENT_HOVER};
}}

QPushButton#btn_connect_ip {{
    background-color: {THEME_WARNING};
    color: #ffffff;
    border: none;
}}

QPushButton#btn_pause {{
    background-color: {THEME_BG_CARD};
    color: {THEME_TEXT_PRIMARY};
    border: 1px solid {THEME_BORDER};
}}

/* ==========================================
   LINE EDIT (Text Input)
   ========================================== */
QLineEdit {{
    background-color: {THEME_BG_SECONDARY};
    color: {THEME_TEXT_PRIMARY};
    border: 1px solid {THEME_BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 12px;
    selection-background-color: {THEME_ACCENT};
}}
QLineEdit:focus {{
    border-color: {THEME_ACCENT};
}}
QLineEdit::placeholder {{
    color: {THEME_TEXT_MUTED};
}}

/* ==========================================
   GROUP BOX (Panels / Cards)
   ========================================== */
QGroupBox {{
    background-color: {THEME_BG_SECONDARY};
    border: 1px solid {THEME_BORDER};
    border-radius: 12px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
    font-size: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    color: {THEME_TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

/* ==========================================
   TABLE WIDGET
   ========================================== */
QTableWidget {{
    background-color: {THEME_BG_SECONDARY};
    alternate-background-color: {THEME_BG_TERTIARY};
    border: 1px solid {THEME_BORDER};
    border-radius: 8px;
    gridline-color: {THEME_BORDER};
    selection-background-color: {THEME_ACCENT};
    font-size: 11px;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border: none;
}}
QHeaderView::section {{
    background-color: {THEME_BG_CARD};
    color: {THEME_TEXT_SECONDARY};
    border: none;
    border-bottom: 2px solid {THEME_BORDER};
    padding: 8px 10px;
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

/* ==========================================
   CHECKBOX (Toggle switches)
   ========================================== */
QCheckBox {{
    spacing: 8px;
    color: {THEME_TEXT_PRIMARY};
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid {THEME_BORDER_LIGHT};
    background-color: {THEME_BG_SECONDARY};
}}
QCheckBox::indicator:checked {{
    background-color: {THEME_ACCENT};
    border-color: {THEME_ACCENT};
}}
QCheckBox::indicator:hover {{
    border-color: {THEME_ACCENT};
}}

/* ==========================================
   COMBOBOX (Dropdown)
   ========================================== */
QComboBox {{
    background-color: {THEME_BG_SECONDARY};
    color: {THEME_TEXT_PRIMARY};
    border: 1px solid {THEME_BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: {THEME_ACCENT};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left: 1px solid {THEME_BORDER};
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    background-color: {THEME_BG_CARD};
}}
QComboBox::down-arrow {{
    width: 12px;
    height: 12px;
}}
QComboBox QAbstractItemView {{
    background-color: {THEME_BG_SECONDARY};
    color: {THEME_TEXT_PRIMARY};
    border: 1px solid {THEME_BORDER};
    border-radius: 4px;
    selection-background-color: {THEME_ACCENT};
    selection-color: #ffffff;
    padding: 4px;
    outline: none;
}}

/* ==========================================
   LABELS
   ========================================== */
QLabel {{
    color: {THEME_TEXT_PRIMARY};
    background-color: transparent;
}}
QLabel#title_label {{
    font-size: 20px;
    font-weight: 800;
    color: {THEME_TEXT_PRIMARY};
    letter-spacing: 1px;
}}
QLabel#status_label {{
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 10px;
}}
QLabel#fps_label {{
    font-size: 12px;
    font-weight: 600;
    color: {THEME_ACCENT};
}}
QLabel#metric_value {{
    font-size: 28px;
    font-weight: 800;
    color: {THEME_TEXT_PRIMARY};
}}
QLabel#metric_label {{
    font-size: 10px;
    font-weight: 600;
    color: {THEME_TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QLabel#placeholder_label {{
    font-size: 16px;
    color: {THEME_TEXT_MUTED};
    font-weight: 600;
}}

/* ==========================================
   SPLITTER
   ========================================== */
QSplitter::handle {{
    background-color: {THEME_BORDER};
    width: 2px;
}}
QSplitter::handle:hover {{
    background-color: {THEME_ACCENT};
}}

/* ==========================================
   FRAME
   ========================================== */
QFrame#card_frame {{
    background-color: {THEME_BG_SECONDARY};
    border: 1px solid {THEME_BORDER};
    border-radius: 12px;
    padding: 12px;
}}

QFrame#top_bar {{
    background-color: {THEME_BG_SECONDARY};
    border-bottom: 1px solid {THEME_BORDER};
    padding: 8px 16px;
}}

QFrame#video_frame {{
    background-color: #000000;
    border: 1px solid {THEME_BORDER};
    border-radius: 12px;
}}
"""
