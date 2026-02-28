"""
WITTGrp-style QSS Stylesheet - Dark professional theme
"""

STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* ── Toolbar ─────────────────────────────────────────────── */
QToolBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #16213e, stop:1 #0f3460);
    border-bottom: 2px solid #e94560;
    spacing: 4px;
    padding: 4px 8px;
}

QToolButton {
    background: transparent;
    color: #e0e0e0;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
}

QToolButton:hover {
    background: rgba(233, 69, 96, 0.2);
    border: 1px solid #e94560;
    color: #ffffff;
}

QToolButton:pressed {
    background: rgba(233, 69, 96, 0.4);
}

/* ── Menu Bar ─────────────────────────────────────────────── */
QMenuBar {
    background-color: #16213e;
    color: #e0e0e0;
    border-bottom: 1px solid #0f3460;
    padding: 2px;
}

QMenuBar::item:selected {
    background: #e94560;
    border-radius: 4px;
}

QMenu {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #e94560;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item:selected {
    background: rgba(233, 69, 96, 0.3);
    border-radius: 4px;
}

QMenu::separator {
    height: 1px;
    background: #0f3460;
    margin: 4px 8px;
}

/* ── Table View ───────────────────────────────────────────── */
QTableWidget {
    background-color: #16213e;
    alternate-background-color: #1a1a2e;
    color: #e0e0e0;
    gridline-color: #0f3460;
    border: none;
    selection-background-color: rgba(233, 69, 96, 0.25);
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 6px 8px;
    border: none;
}

QTableWidget::item:hover {
    background: rgba(233, 69, 96, 0.12);
}

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0f3460, stop:1 #16213e);
    color: #e94560;
    font-weight: 700;
    font-size: 12px;
    padding: 8px;
    border: none;
    border-right: 1px solid #1a1a2e;
    border-bottom: 2px solid #e94560;
}

QHeaderView::section:hover {
    background: #0f3460;
}

/* ── Progress Bar ─────────────────────────────────────────── */
QProgressBar {
    background-color: #0f3460;
    border: 1px solid #16213e;
    border-radius: 4px;
    height: 14px;
    text-align: center;
    color: #ffffff;
    font-size: 10px;
    font-weight: 600;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e94560, stop:0.5 #ff6b9d, stop:1 #e94560);
    border-radius: 3px;
}

/* ── Status Bar ───────────────────────────────────────────── */
QStatusBar {
    background-color: #0f3460;
    color: #a0a0c0;
    border-top: 1px solid #e94560;
    font-size: 12px;
    padding: 4px;
}

QStatusBar::item {
    border: none;
}

/* ── Buttons ──────────────────────────────────────────────── */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #e94560, stop:1 #c73652);
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ff6b9d, stop:1 #e94560);
}

QPushButton:pressed {
    background: #c73652;
}

QPushButton:disabled {
    background: #3a3a5a;
    color: #606080;
}

QPushButton#btn_cancel, QPushButton#btn_secondary {
    background: #2a2a4a;
    color: #a0a0c0;
    border: 1px solid #404060;
}

QPushButton#btn_cancel:hover, QPushButton#btn_secondary:hover {
    background: #3a3a5a;
    color: #ffffff;
}

/* ── Input Fields ─────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0f1b35;
    color: #e0e0e0;
    border: 1.5px solid #0f3460;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    selection-background-color: #e94560;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1.5px solid #e94560;
    background-color: #0d1a32;
}

QLineEdit::placeholder {
    color: #505070;
}

/* ── ComboBox ─────────────────────────────────────────────── */
QComboBox {
    background-color: #0f1b35;
    color: #e0e0e0;
    border: 1.5px solid #0f3460;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 120px;
}

QComboBox:hover {
    border: 1.5px solid #e94560;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #e94560;
    width: 0;
    height: 0;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #e94560;
    border-radius: 6px;
    selection-background-color: rgba(233, 69, 96, 0.3);
}

/* ── SpinBox ──────────────────────────────────────────────── */
QSpinBox {
    background-color: #0f1b35;
    color: #e0e0e0;
    border: 1.5px solid #0f3460;
    border-radius: 6px;
    padding: 6px 10px;
}

QSpinBox:focus {
    border-color: #e94560;
}

/* ── GroupBox ─────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #0f3460;
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    color: #e94560;
    font-weight: 700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #1a1a2e;
}

/* ── CheckBox ─────────────────────────────────────────────── */
QCheckBox {
    spacing: 8px;
    color: #c0c0e0;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1.5px solid #0f3460;
    background: #0f1b35;
}

QCheckBox::indicator:checked {
    background: #e94560;
    border-color: #e94560;
    image: none;
}

QCheckBox::indicator:hover {
    border-color: #e94560;
}

/* ── TabWidget ────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #0f3460;
    border-radius: 6px;
    background: #1a1a2e;
}

QTabBar::tab {
    background: #16213e;
    color: #a0a0c0;
    border: 1px solid #0f3460;
    border-bottom: none;
    padding: 8px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #e94560;
    color: #ffffff;
    font-weight: 700;
}

QTabBar::tab:hover:!selected {
    background: rgba(233, 69, 96, 0.2);
    color: #ffffff;
}

/* ── ScrollBar ────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #16213e;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #e94560;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #16213e;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #e94560;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Splitter ─────────────────────────────────────────────── */
QSplitter::handle {
    background: #e94560;
    height: 2px;
}

/* ── Label ────────────────────────────────────────────────── */
QLabel {
    color: #c0c0e0;
}

QLabel#title_label {
    color: #e94560;
    font-size: 18px;
    font-weight: 700;
}

QLabel#subtitle_label {
    color: #8080a0;
    font-size: 12px;
}

/* ── Tooltip ──────────────────────────────────────────────── */
QToolTip {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #e94560;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""
