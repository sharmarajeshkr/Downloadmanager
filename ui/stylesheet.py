"""
WITTGrp-style QSS Stylesheet - Dark professional theme
"""

STYLESHEET = """
* {
    outline: none;
}

QMainWindow, QDialog, QWidget {
    background-color: #1e1e2e;
    color: #e2e2e3;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* ── Toolbar ─────────────────────────────────────────────── */
QToolBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #282a36, stop:1 #1e1e2e);
    border-bottom: 2px solid #0A84FF;
    spacing: 2px;
    padding: 2px 6px;
}

QToolButton {
    background: transparent;
    color: #e2e2e3;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: 600;
}

QToolButton:hover {
    background: rgba(10, 132, 255, 0.15);
    border: 1px solid rgba(10, 132, 255, 0.4);
    color: #ffffff;
}

QToolButton:pressed {
    background: rgba(10, 132, 255, 0.3);
}

/* ── Menu Bar ─────────────────────────────────────────────── */
QMenuBar {
    background-color: #282a36;
    color: #e2e2e3;
    border-bottom: 1px solid #3b4252;
    padding: 2px;
}

QMenuBar::item:selected {
    background: #0A84FF;
    border-radius: 4px;
}

QMenu {
    background-color: #282a36;
    color: #e2e2e3;
    border: 1px solid #3b4252;
    border-radius: 4px;
    padding: 2px;
}

QMenu::item:selected {
    background: rgba(10, 132, 255, 0.3);
    border-radius: 4px;
}

QMenu::separator {
    height: 1px;
    background: #3b4252;
    margin: 4px 8px;
}

/* ── Table View ───────────────────────────────────────────── */
QTableWidget {
    background-color: #1e1e2e;
    alternate-background-color: #222436;
    color: #e2e2e3;
    gridline-color: #3b4252;
    border: none;
    selection-background-color: rgba(10, 132, 255, 0.25);
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 3px 6px;
    border: none;
}

QTableWidget::item:hover {
    background: rgba(10, 132, 255, 0.1);
}

QHeaderView::section {
    background: #282a36;
    color: #0A84FF;
    font-weight: 700;
    font-size: 12px;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #1e1e2e;
    border-bottom: 1px solid #3b4252;
}

QHeaderView::section:hover {
    background: #3b4252;
}

/* ── Progress Bar ─────────────────────────────────────────── */
QProgressBar {
    background-color: #282a36;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #0A84FF;
    border-radius: 6px;
}

/* ── Status Bar ───────────────────────────────────────────── */
QStatusBar {
    background-color: #282a36;
    color: #a0a0c0;
    border-top: 1px solid #3b4252;
    font-size: 12px;
    padding: 4px 8px;
}

QStatusBar::item {
    border: none;
}

/* ── Buttons ──────────────────────────────────────────────── */
QPushButton {
    background: #0A84FF;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background: #47A1FF;
}

QPushButton:pressed {
    background: #0066CC;
}

QPushButton:disabled {
    background: #3b4252;
    color: #8892b0;
}

QPushButton#btn_cancel, QPushButton#btn_secondary {
    background: #282a36;
    color: #a0a0c0;
    border: 1px solid #3b4252;
}

QPushButton#btn_cancel:hover, QPushButton#btn_secondary:hover {
    background: #3b4252;
    color: #ffffff;
}

/* ── Input Fields ─────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #282a36;
    color: #e2e2e3;
    border: 1px solid #3b4252;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #0A84FF;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #0A84FF;
    background-color: #2d303e;
}

QLineEdit::placeholder {
    color: #6272a4;
}

/* ── ComboBox ─────────────────────────────────────────────── */
QComboBox {
    background-color: #282a36;
    color: #e2e2e3;
    border: 1px solid #3b4252;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 100px;
}

QComboBox:hover {
    border: 1px solid #0A84FF;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #0A84FF;
    width: 0;
    height: 0;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #282a36;
    color: #e2e2e3;
    border: 1px solid #3b4252;
    border-radius: 6px;
    selection-background-color: rgba(10, 132, 255, 0.2);
}

/* ── SpinBox ──────────────────────────────────────────────── */
QSpinBox {
    background-color: #282a36;
    color: #e2e2e3;
    border: 1px solid #3b4252;
    border-radius: 4px;
    padding: 4px 8px;
}

QSpinBox:focus {
    border-color: #0A84FF;
}

/* ── GroupBox ─────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #3b4252;
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px;
    color: #0A84FF;
    font-weight: 700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #1e1e2e;
}

/* ── CheckBox ─────────────────────────────────────────────── */
QCheckBox {
    spacing: 8px;
    color: #c0c0e0;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #3b4252;
    background: #282a36;
}

QCheckBox::indicator:checked {
    background: #0A84FF;
    border-color: #0A84FF;
    image: none;
}

QCheckBox::indicator:hover {
    border-color: #0A84FF;
}

/* ── TabWidget ────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #3b4252;
    border-radius: 6px;
    background: #1e1e2e;
}

QTabBar::tab {
    background: #282a36;
    color: #a0a0c0;
    border: 1px solid #3b4252;
    border-bottom: none;
    padding: 8px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background: #0A84FF;
    border-color: #0A84FF;
    color: #ffffff;
    font-weight: 700;
}

QTabBar::tab:hover:!selected {
    background: rgba(10, 132, 255, 0.15);
    color: #ffffff;
}

/* ── ScrollBar ────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1e1e2e;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #3b4252;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #0A84FF;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #1e1e2e;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #3b4252;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #0A84FF;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Splitter ─────────────────────────────────────────────── */
QSplitter::handle {
    background: #3b4252;
    height: 1px;
}

/* ── Label ────────────────────────────────────────────────── */
QLabel {
    color: #c0c0e0;
}

QLabel#title_label {
    color: #0A84FF;
    font-size: 19px;
    font-weight: 700;
}

QLabel#subtitle_label {
    color: #8892b0;
    font-size: 13px;
}

/* ── Tooltip ──────────────────────────────────────────────── */
QToolTip {
    background-color: #282a36;
    color: #e2e2e3;
    border: 1px solid #0A84FF;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}
"""
