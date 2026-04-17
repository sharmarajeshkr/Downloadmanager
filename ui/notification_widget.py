"""
Custom Notification System for WITTGrp
"""
import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QApplication, QGraphicsDropShadowEffect, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath

class ModernNotification(QWidget):
    """
    A sleek, modern floating notification widget.
    Slides in from the bottom-right corner of the parent window or screen.
    """
    closed = pyqtSignal(object)  # Emits self when closed

    def __init__(self, title: str, message: str, parent=None, duration_ms=4000, 
                 icon_text="ℹ\ufe0f", bg_color="#1E1E1E", accent_color="#0A84FF"):
        super().__init__(parent)
        self.title_text = title
        self.msg_text = message
        self.duration_ms = duration_ms
        self._bg_color = bg_color
        self._accent_color = accent_color
        
        # Make the widget a frameless floating window
        # Tool | FramelessWindowHint keeps it from showing in taskbar and removes border
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setFixedWidth(320)
        self.setMinimumHeight(80)
        
        self._build_ui(icon_text)
        
        # Setup auto-close timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close_animation)
        self.timer.setSingleShot(True)
        
        # Drag state (optional dismiss on click)
        self.mousePressEvent = lambda e: self.close_animation()

    def _build_ui(self, icon_text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Main container with rounded corners
        self.container = QWidget(self)
        self.container.setObjectName("NotifContainer")
        self.container.setStyleSheet(f"""
            QWidget#NotifContainer {{
                background-color: {self._bg_color};
                border-radius: 8px;
                border: 1px solid #333333;
                border-left: 4px solid {self._accent_color};
            }}
        """)
        
        # Add soft drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
        
        clayout = QHBoxLayout(self.container)
        clayout.setContentsMargins(12, 12, 12, 12)
        clayout.setSpacing(12)
        
        # Icon
        icon_lbl = QLabel(icon_text)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 16))
        icon_lbl.setStyleSheet(f"color: {self._accent_color};")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        clayout.addWidget(icon_lbl)
        
        # Text details
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_lbl = QLabel(self.title_text)
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: white;")
        title_lbl.setWordWrap(True)
        text_layout.addWidget(title_lbl)
        
        msg_lbl = QLabel(self.msg_text)
        msg_lbl.setFont(QFont("Segoe UI", 9))
        msg_lbl.setStyleSheet("color: #AAAAAA;")
        msg_lbl.setWordWrap(True)
        text_layout.addWidget(msg_lbl)
        text_layout.addStretch()
        
        clayout.addLayout(text_layout, 1)
        
        # Close 'x' button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; 
                color: #888; 
                font-size: 16px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        close_btn.clicked.connect(self.close_animation)
        
        # We wrap the button to keep it top-right aligned regardless of text height
        btn_layout = QVBoxLayout()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        clayout.addLayout(btn_layout)
        
        layout.addWidget(self.container)

    def show_animation(self):
        """Show the notification with a slide-up and fade-in animation."""
        self.show()
        self.adjustSize()
        
        # Position at the bottom right of the screen (or parent if preferred)
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Calculate standard bottom-right position
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 20
        
        # Note: If multiple notifications are stacked, the NotificationManager calculates the new Y
        self.target_y = getattr(self, 'target_y', y)
        self.target_x = x
        
        # Start positioned slightly below to slide up
        start_rect = QRect(x, self.target_y + 40, self.width(), self.height())
        end_rect = QRect(x, self.target_y, self.width(), self.height())
        
        self.setGeometry(start_rect)
        self.setWindowOpacity(0.0)
        
        # Slide Animation
        self.anim_geom = QPropertyAnimation(self, b"geometry")
        self.anim_geom.setDuration(300)
        self.anim_geom.setStartValue(start_rect)
        self.anim_geom.setEndValue(end_rect)
        self.anim_geom.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # Fade Animation
        self.anim_alpha = QPropertyAnimation(self, b"windowOpacity")
        self.anim_alpha.setDuration(300)
        self.anim_alpha.setStartValue(0.0)
        self.anim_alpha.setEndValue(1.0)
        
        self.anim_geom.start()
        self.anim_alpha.start()
        
        if self.duration_ms > 0:
            self.timer.start(self.duration_ms)

    def close_animation(self):
        """Slide down and fade out."""
        self.timer.stop()
        
        start_rect = self.geometry()
        end_rect = QRect(start_rect.x(), start_rect.y() + 40, start_rect.width(), start_rect.height())
        
        self.anim_geom = QPropertyAnimation(self, b"geometry")
        self.anim_geom.setDuration(250)
        self.anim_geom.setStartValue(start_rect)
        self.anim_geom.setEndValue(end_rect)
        self.anim_geom.setEasingCurve(QEasingCurve.Type.InCubic)
        
        self.anim_alpha = QPropertyAnimation(self, b"windowOpacity")
        self.anim_alpha.setDuration(250)
        self.anim_alpha.setStartValue(1.0)
        self.anim_alpha.setEndValue(0.0)
        
        self.anim_alpha.finished.connect(self._on_closed)
        
        self.anim_geom.start()
        self.anim_alpha.start()

    def _on_closed(self):
        self.closed.emit(self)
        self.close()

class NotificationManager:
    """Class to manage multiple stacked notifications."""
    _instance = None
    
    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        self.active_notifications = []
        self.spacing = 10
        self.margin_bottom = 50 # Default taskbar clearance
        
    def notify(self, title: str, message: str, icon="ℹ\ufe0f", action="info"):
        """
        Shows a toast notification.
        action can be 'info', 'success', 'warning', 'error' for different accent colors.
        """
        accents = {
            'info': '#0A84FF',
            'success': '#30D158',
            'warning': '#FF9F0A',
            'error': '#FF453A'
        }
        color = accents.get(action, '#0A84FF')
        
        # Determine icon by action if not manually overridden
        if icon == "ℹ\ufe0f":
            if action == 'success': icon = "✓"
            elif action == 'warning': icon = "⚠️"
            elif action == 'error': icon = "❌"
            elif action == 'info': icon = "⬇" # Download icon by default for IDM
        
        notif = ModernNotification(title, message, icon_text=icon, accent_color=color)
        notif.closed.connect(self._remove_notification)
        
        # Calculate target Y position by stacking above existing notifications
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Assume standard widget height offscreen first
        base_y = screen.height() - self.margin_bottom
        total_offset = 0
        
        for active in self.active_notifications:
            total_offset += active.height() + self.spacing
            
        notif.target_y = base_y - total_offset - notif.height()
        
        self.active_notifications.append(notif)
        notif.show_animation()
        
    def _remove_notification(self, notif_ref):
        if notif_ref in self.active_notifications:
            self.active_notifications.remove(notif_ref)
            self._rearrange()
            
    def _rearrange(self):
        """Slide existing notifications down when one above is dismissed."""
        screen = QApplication.primaryScreen().availableGeometry()
        base_y = screen.height() - self.margin_bottom
        
        current_offset = 0
        for notif in self.active_notifications:
            new_y = base_y - current_offset - notif.height()
            
            if notif.geometry().y() != new_y:
                # Animate to new position
                anim = QPropertyAnimation(notif, b"geometry")
                anim.setDuration(250)
                anim.setStartValue(notif.geometry())
                anim.setEndValue(QRect(notif.geometry().x(), new_y, notif.width(), notif.height()))
                anim.setEasingCurve(QEasingCurve.Type.OutBounce)
                anim.start()
                # Keep reference to avoid garbage collection
                notif._anim_ref = anim
                
            current_offset += notif.height() + self.spacing
