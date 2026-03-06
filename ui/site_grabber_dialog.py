import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from core.site_grabber import SiteGrabber
from core.file_manager import format_size, probe_url

class GrabberWorker(QThread):
    finished = pyqtSignal(list, str) # list of urls, error msg
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        try:
            grabber = SiteGrabber()
            assets = grabber.fetch_assets(self.url)
            self.finished.emit(assets, "")
        except Exception as e:
            self.finished.emit([], str(e))

class SiteGrabberDialog(QDialog):
    def __init__(self, parent=None, queue_manager=None):
        super().__init__(parent)
        self.queue_manager = queue_manager
        self.setWindowTitle("WITTGrp Site Grabber")
        self.setMinimumSize(700, 500)
        self.setModal(False) # Non-modal so user can interact with main window
        self.worker = None
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # URL Input Section
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter website URL (e.g., https://example.com) ...")
        self.url_input.returnPressed.connect(self._start_grab)
        
        self.grab_btn = QPushButton("Grab Assets")
        self.grab_btn.setObjectName("btn_primary")
        self.grab_btn.setStyleSheet("background: #0A84FF; color: white; border-radius: 4px; padding: 6px 16px; font-weight: bold;")
        self.grab_btn.clicked.connect(self._start_grab)
        
        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.grab_btn)
        layout.addLayout(url_layout)
        
        # Status
        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Indeterminate initially
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Results Table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Media File / Link", "Ext"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 80)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Actions
        btn_layout = QHBoxLayout()
        
        self.sel_all_btn = QPushButton("Select All")
        self.sel_all_btn.clicked.connect(self.table.selectAll)
        
        self.download_btn = QPushButton("⬇ Download Selected")
        self.download_btn.setObjectName("btn_secondary")
        self.download_btn.clicked.connect(self._download_selected)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.sel_all_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(self.download_btn)
        layout.addLayout(btn_layout)

    def _start_grab(self):
        url = self.url_input.text().strip()
        if not url:
            return
            
        self.grab_btn.setEnabled(False)
        self.status_label.setText(f"Crawling {url}...")
        self.progress.setVisible(True)
        self.table.setRowCount(0)
        
        self.worker = GrabberWorker(url)
        self.worker.finished.connect(self._on_grab_finished)
        self.worker.start()

    def _on_grab_finished(self, assets, err):
        self.progress.setVisible(False)
        self.grab_btn.setEnabled(True)
        
        if err:
            self.status_label.setText("Error!")
            QMessageBox.critical(self, "Grabber Error", err)
            return
            
        self.status_label.setText(f"Found {len(assets)} assets.")
        self.table.setRowCount(len(assets))
        
        for i, asset_url in enumerate(assets):
            ext = asset_url.split('.')[-1][:5] if '.' in asset_url.split('/')[-1] else ''
            self.table.setItem(i, 0, QTableWidgetItem(asset_url))
            self.table.setItem(i, 1, QTableWidgetItem(ext.upper()))
            
    def _download_selected(self):
        selected_rows = list(set(idx.row() for idx in self.table.selectedIndexes()))
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select at least one asset to download.")
            return
        
        count = 0
        for row in selected_rows:
            url_item = self.table.item(row, 0)
            if url_item:
                url = url_item.text()
                if self.queue_manager:
                    # Auto start these batch grabbed links
                    self.queue_manager.add_download(url=url, auto_start=True)
                    count += 1
                    
        self.status_label.setText(f"Sent {count} links to Download Queue.")
        QMessageBox.information(self, "Success", f"Sent {count} items to the download queue.")
