"""
Settings Dialog - Configure all IDM preferences
"""
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QFormLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QCheckBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)  # Emits changed settings dict

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("WITTGrp Settings & Preferences")
        self.setMinimumSize(700, 550)
        self.setModal(True)
        self._settings = db.get_all_settings() if db else {}
        self._categories = db.get_categories() if db else []
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QWidget()
        header.setStyleSheet("background: #0f3460; padding: 16px;")
        hh = QVBoxLayout(header)
        title = QLabel("⚙  Settings & Preferences")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #e94560; background: transparent;")
        subtitle = QLabel("Configure download preferences, paths, and integrations")
        subtitle.setStyleSheet("color: #8090b0; background: transparent; font-size: 12px;")
        hh.addWidget(title)
        hh.addWidget(subtitle)
        layout.addWidget(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._general_tab(), "General")
        self.tabs.addTab(self._connection_tab(), "Connection")
        self.tabs.addTab(self._categories_tab(), "Categories")
        self.tabs.addTab(self._integration_tab(), "Integration")

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 12, 16, 16)
        btn_row.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("btn_cancel")
        self.cancel_btn.setMinimumWidth(100)
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setMinimumWidth(140)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._save)

    def _general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        path_group = QGroupBox("Default Save Location")
        pfl = QFormLayout(path_group)

        self.default_path_edit = QLineEdit()
        browse = QPushButton("Browse")
        browse.setObjectName("btn_secondary")
        browse.setMaximumWidth(80)
        browse.clicked.connect(lambda: self._browse_folder(self.default_path_edit))
        row = QHBoxLayout()
        row.addWidget(self.default_path_edit)
        row.addWidget(browse)
        pfl.addRow("Default folder:", row)
        layout.addWidget(path_group)

        dl_group = QGroupBox("Download Behavior")
        dfl = QFormLayout(dl_group)
        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 10)
        self.max_concurrent_spin.setSuffix("  simultaneous downloads")
        dfl.addRow("Max concurrent:", self.max_concurrent_spin)

        self.show_add_dialog_check = QCheckBox("Show 'Add New Download' dialog")
        dfl.addRow("", self.show_add_dialog_check)

        self.start_on_boot_check = QCheckBox("Start WITTGrp with Windows")
        dfl.addRow("", self.start_on_boot_check)
        layout.addWidget(dl_group)

        layout.addStretch()
        return w

    def _connection_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        conn_group = QGroupBox("Connection Settings")
        cfl = QFormLayout(conn_group)

        self.default_connections_spin = QSpinBox()
        self.default_connections_spin.setRange(1, 32)
        self.default_connections_spin.setSuffix("  connections per file")
        cfl.addRow("Default connections:", self.default_connections_spin)
        layout.addWidget(conn_group)

        speed_group = QGroupBox("Bandwidth Control")
        sfl = QFormLayout(speed_group)
        self.global_speed_check = QCheckBox("Enable global speed limit")
        self.global_speed_spin = QSpinBox()
        self.global_speed_spin.setRange(64, 1000000)
        self.global_speed_spin.setValue(10240)
        self.global_speed_spin.setSuffix("  KB/s")
        self.global_speed_spin.setEnabled(False)
        self.global_speed_check.toggled.connect(self.global_speed_spin.setEnabled)
        sfl.addRow("", self.global_speed_check)
        sfl.addRow("Global limit:", self.global_speed_spin)
        layout.addWidget(speed_group)

        layout.addStretch()
        return w

    def _categories_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        label = QLabel("Configure extension-to-category mappings and save folders:")
        label.setStyleSheet("color: #8090b0; font-size: 12px;")
        layout.addWidget(label)

        self.cat_table = QTableWidget(0, 3)
        self.cat_table.setHorizontalHeaderLabels(["Category", "Extensions (comma-separated)", "Save Folder"])
        self.cat_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.cat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.cat_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cat_table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        layout.addWidget(self.cat_table)

        btn_row = QHBoxLayout()
        add_cat_btn = QPushButton("+ Add Category")
        add_cat_btn.setObjectName("btn_secondary")
        add_cat_btn.clicked.connect(self._add_category_row)
        btn_row.addWidget(add_cat_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return w

    def _integration_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        browser_group = QGroupBox("Browser Extension")
        bfl = QFormLayout(browser_group)

        self.ext_port_spin = QSpinBox()
        self.ext_port_spin.setRange(1024, 65535)
        self.ext_port_spin.setValue(9614)
        bfl.addRow("Extension server port:", self.ext_port_spin)

        install_label = QLabel(
            '<a href="#" style="color:#e94560;">How to install the browser extension →</a>'
        )
        install_label.setOpenExternalLinks(False)
        bfl.addRow("", install_label)
        layout.addWidget(browser_group)

        sys_group = QGroupBox("System Integration")
        sfl = QFormLayout(sys_group)
        self.clipboard_check = QCheckBox("Monitor clipboard for download links")
        self.tray_check = QCheckBox("Show system tray icon")
        self.minimize_tray_check = QCheckBox("Minimize to tray on close")
        sfl.addRow("", self.clipboard_check)
        sfl.addRow("", self.tray_check)
        sfl.addRow("", self.minimize_tray_check)
        layout.addWidget(sys_group)

        layout.addStretch()
        return w

    def _load_values(self):
        s = self._settings
        self.default_path_edit.setText(s.get('save_path', r'D:\idm\downloads'))
        self.max_concurrent_spin.setValue(int(s.get('max_concurrent', 3)))
        self.show_add_dialog_check.setChecked(s.get('show_add_dialog', 'true') == 'true')
        self.default_connections_spin.setValue(int(s.get('default_connections', 8)))
        self.clipboard_check.setChecked(s.get('monitor_clipboard', 'true') == 'true')
        self.tray_check.setChecked(s.get('tray_icon', 'true') == 'true')
        self.minimize_tray_check.setChecked(s.get('minimize_to_tray', 'true') == 'true')
        self.ext_port_spin.setValue(int(s.get('extension_server_port', 9614)))

        # Load categories
        for cat in self._categories:
            self._add_category_row(cat)

    def _add_category_row(self, cat_data: dict = None):
        row = self.cat_table.rowCount()
        self.cat_table.insertRow(row)
        if cat_data:
            self.cat_table.setItem(row, 0, QTableWidgetItem(cat_data['name']))
            self.cat_table.setItem(row, 1, QTableWidgetItem(", ".join(cat_data.get('extensions', []))))
            self.cat_table.setItem(row, 2, QTableWidgetItem(cat_data.get('save_path', '')))
        else:
            self.cat_table.setItem(row, 0, QTableWidgetItem("New Category"))
            self.cat_table.setItem(row, 1, QTableWidgetItem(""))
            self.cat_table.setItem(row, 2, QTableWidgetItem(r"D:\idm\downloads\Other"))

    def _browse_folder(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", line_edit.text())
        if folder:
            line_edit.setText(folder)

    def _save(self):
        s = {
            'save_path': self.default_path_edit.text(),
            'max_concurrent': str(self.max_concurrent_spin.value()),
            'show_add_dialog': 'true' if self.show_add_dialog_check.isChecked() else 'false',
            'default_connections': str(self.default_connections_spin.value()),
            'monitor_clipboard': 'true' if self.clipboard_check.isChecked() else 'false',
            'tray_icon': 'true' if self.tray_check.isChecked() else 'false',
            'minimize_to_tray': 'true' if self.minimize_tray_check.isChecked() else 'false',
            'extension_server_port': str(self.ext_port_spin.value()),
        }
        if self.db:
            for k, v in s.items():
                self.db.set_setting(k, v)

            # Save categories
            for row in range(self.cat_table.rowCount()):
                name = (self.cat_table.item(row, 0) or QTableWidgetItem()).text().strip()
                exts_raw = (self.cat_table.item(row, 1) or QTableWidgetItem()).text().strip()
                path = (self.cat_table.item(row, 2) or QTableWidgetItem()).text().strip()
                if name:
                    exts = [e.strip().lstrip('.').lower() for e in exts_raw.split(',') if e.strip()]
                    self.db.update_category(name, exts, path)

        self.settings_changed.emit(s)
        self.accept()
