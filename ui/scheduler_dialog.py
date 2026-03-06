import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTimeEdit, QCheckBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, QTime

class SchedulerDialog(QDialog):
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("WITTGrp Scheduler")
        self.setMinimumWidth(380)
        self.setModal(True)
        
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Main Toggle
        self.enable_check = QCheckBox("Enable Schedule")
        self.enable_check.setStyleSheet("font-weight: bold; font-size: 14px; color: #0A84FF;")
        layout.addWidget(self.enable_check)

        # Time Group
        time_group = QGroupBox("Schedule Times")
        time_layout = QFormLayout(time_group)
        
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        time_layout.addRow("Start download at:", self.start_time)
        
        self.stop_time = QTimeEdit()
        self.stop_time.setDisplayFormat("HH:mm")
        time_layout.addRow("Stop download at:", self.stop_time)
        
        layout.addWidget(time_group)
        
        # Actions Group
        action_group = QGroupBox("After Schedule")
        action_layout = QVBoxLayout(action_group)
        
        self.shutdown_check = QCheckBox("Turn off computer when done")
        action_layout.addWidget(self.shutdown_check)
        
        layout.addWidget(action_group)
        
        # State Binding
        self.enable_check.toggled.connect(time_group.setEnabled)
        self.enable_check.toggled.connect(action_group.setEnabled)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save Schedule")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setObjectName("btn_primary")
        save_btn.setStyleSheet("background: #0A84FF; color: white; border-radius: 4px; padding: 6px 16px; font-weight: bold;")
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)

    def load_settings(self):
        if not self.db: return
        
        enabled = self.db.get_setting("schedule_enabled", "false") == "true"
        self.enable_check.setChecked(enabled)
        
        start = self.db.get_setting("schedule_start", "00:00")
        self.start_time.setTime(QTime.fromString(start, "HH:mm"))
        
        stop = self.db.get_setting("schedule_stop", "06:00")
        self.stop_time.setTime(QTime.fromString(stop, "HH:mm"))
        
        shutdown = self.db.get_setting("shutdown_when_done", "false") == "true"
        self.shutdown_check.setChecked(shutdown)
        
        # Trigger initial state
        self.start_time.parent().setEnabled(enabled)
        self.shutdown_check.parent().setEnabled(enabled)

    def save_settings(self):
        if not self.db: return
        
        self.db.set_setting("schedule_enabled", "true" if self.enable_check.isChecked() else "false")
        self.db.set_setting("schedule_start", self.start_time.time().toString("HH:mm"))
        self.db.set_setting("schedule_stop", self.stop_time.time().toString("HH:mm"))
        self.db.set_setting("shutdown_when_done", "true" if self.shutdown_check.isChecked() else "false")
        
        self.accept()
