import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

SVG_DIR = os.path.join(os.path.dirname(__file__), "assets", "svg")


class CustomTitleBar(QWidget):
    """Custom frameless title bar with drag support and window controls."""
    def __init__(self, parent, title="🚀 WITTGrp Download Manager"):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(38)
        self.setStyleSheet("background: #1e1e2e; border-bottom: 1px solid #3b4252;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #e2e2e3; font-weight: 600; font-size: 13px; border: none;")
        layout.addWidget(title_label)
        layout.addStretch()

        self.btn_min = QPushButton()
        self.btn_min.setIcon(QIcon(os.path.join(SVG_DIR, 'min.svg')))
        self.btn_max = QPushButton()
        self.btn_max.setIcon(QIcon(os.path.join(SVG_DIR, 'max.svg')))
        self.btn_close = QPushButton()
        self.btn_close.setIcon(QIcon(os.path.join(SVG_DIR, 'close.svg')))

        for btn in (self.btn_min, self.btn_max, self.btn_close):
            btn.setFixedSize(45, 38)
            btn.setStyleSheet("""
                QPushButton { background: transparent; color: #8892b0; border: none; font-size: 14px; border-radius: 0px; padding-bottom: 4px; outline: none; }
                QPushButton:hover { background: #3b4252; color: #ffffff; }
            """)
            layout.addWidget(btn)

        self.btn_close.setStyleSheet("""
            QPushButton { background: transparent; color: #8892b0; border: none; font-size: 14px; border-radius: 0px; padding-bottom: 4px; outline: none; }
            QPushButton:hover { background: #e81123; color: #ffffff; }
        """)

        self.btn_min.clicked.connect(self.parent.showMinimized)
        self.btn_max.clicked.connect(self.toggle_max_restore)
        self.btn_close.clicked.connect(self.parent.close)

        self.start_pos = None

    def toggle_max_restore(self):
        # Dialogs might not have isMaximized, so handle safely
        if hasattr(self.parent, 'isMaximized') and hasattr(self.parent, 'showNormal') and hasattr(self.parent, 'showMaximized'):
            if self.parent.isMaximized():
                self.parent.showNormal()
            else:
                self.parent.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.start_pos is not None:
            self.parent.move(event.globalPosition().toPoint() - self.start_pos)

    def mouseReleaseEvent(self, event):
        self.start_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_max_restore()
