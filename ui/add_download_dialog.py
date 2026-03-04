"""
Add Download Dialog - URL input, filename, save path, connections
"""
import os
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QSpinBox, QComboBox, QCheckBox,
    QGroupBox, QFormLayout, QProgressBar, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QIcon
from core.file_manager import filename_from_url, probe_url, get_category, format_size
from ui.titlebar import CustomTitleBar

SVG_DIR = os.path.join(os.path.dirname(__file__), "assets", "svg")


class ProbeThread(QThread):
    result = pyqtSignal(str, int, bool, str)  # final_url, size, accepts_ranges, content_disposition

    def __init__(self, url, referer=''):
        super().__init__()
        self.url = url
        self.referer = referer

    def run(self):
        headers = {'Referer': self.referer} if self.referer else {}
        final_url, size, accepts, cd = probe_url(self.url, headers)
        self.result.emit(final_url, size, accepts, cd)


class AddDownloadDialog(QDialog):
    download_requested = pyqtSignal(dict)  # Emitted with download params

    def __init__(self, parent=None, url: str = '', filename: str = '',
                 referer: str = '', extra_headers: dict = None,
                 categories: list = None, db=None):
        super().__init__(parent)
        self.categories = categories or []
        self.db = db
        self.extra_headers = extra_headers or {}
        self._probe_thread = None
        self._auto_probe_done = False   # True after ANY probe fires (blocks timer re-fire only)
        self._probe_in_progress = False  # True while yt-dlp is running
        self._probed_size = 0
        self._original_url = url        # Keep the original YouTube/page URL

        self.setWindowTitle("Add New Download")
        self.setMinimumSize(580, 520)
        self.resize(640, 600)
        self.setModal(True)

        self._typing_timer = QTimer(self)
        self._typing_timer.setSingleShot(True)
        self._typing_timer.timeout.connect(self._probe_url)

        self._build_ui()

        # Set initial values with signals BLOCKED so we don't trigger premature probes
        self.url_edit.blockSignals(True)
        self.filename_edit.blockSignals(True)
        if url:
            self.url_edit.setText(url)
        if filename:
            self.filename_edit.setText(filename)
            self._auto_probe_done = True  # filename supplied — no need to probe
            # Explicitly resolve the category for the pre-filled filename
            cat = get_category(filename, self.categories)
            idx = self.category_combo.findText(cat)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
        if referer:
            self.referer_edit.setText(referer)
        self.url_edit.blockSignals(False)
        self.filename_edit.blockSignals(False)

        # Now connect signals (AFTER initial values are set)
        self._connect_signals()

        # Set initial save path
        self._refresh_save_path()

        # If we have a URL but no filename yet, kick off the probe once
        if url and not filename:
            self._typing_timer.start(400)  # short delay to let the dialog render first


    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 12, 16, 14)

        # ── Header ──────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        icon_lbl = QLabel("⬇")
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            "background:#0A84FF; color:#fff; border-radius:6px;"
            "font-size:14px; font-weight:700;"
        )
        title_lbl = QLabel("Add New Download")
        title_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color:#0A84FF;")
        hdr.addWidget(icon_lbl)
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        layout.addLayout(hdr)

        # ── Download URL ─────────────────────────────────────────
        url_group = QGroupBox("Download URL")
        url_fl = QFormLayout(url_group)
        url_fl.setSpacing(8)
        url_fl.setContentsMargins(10, 14, 10, 10)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/file.mp4")
        url_fl.addRow("URL:", self.url_edit)

        self.referer_edit = QLineEdit()
        self.referer_edit.setPlaceholderText("(optional) page where video was found")
        url_fl.addRow("Referer:", self.referer_edit)

        probe_status_row = QHBoxLayout()
        self.probe_btn = QPushButton("Detect Info")
        self.probe_btn.setObjectName("btn_secondary")
        self.probe_btn.setMaximumWidth(130)
        probe_status_row.addWidget(self.probe_btn)
        probe_status_row.addSpacing(8)
        self.probe_status = QLabel("")
        self.probe_status.setObjectName("subtitle_label")
        probe_status_row.addWidget(self.probe_status)
        probe_status_row.addStretch()
        url_fl.addRow("", probe_status_row)

        layout.addWidget(url_group)

        # ── File Info ────────────────────────────────────────────
        file_group = QGroupBox("File Info")
        file_fl = QFormLayout(file_group)
        file_fl.setSpacing(16)
        file_fl.setContentsMargins(10, 14, 10, 14)

        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("filename.ext")
        file_fl.addRow("Filename:", self.filename_edit)

        self.size_label = QLabel("Unknown")
        self.size_label.setObjectName("subtitle_label")
        file_fl.addRow("Size:", self.size_label)

        self.category_combo = QComboBox()
        cat_names = [c['name'] for c in self.categories] if self.categories else \
            ['Videos', 'Music', 'Documents', 'Programs', 'Archives', 'Other']
        self.category_combo.addItems(cat_names)
        file_fl.addRow("Category:", self.category_combo)

        save_row = QHBoxLayout()
        save_row.setSpacing(6)
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setPlaceholderText("Save location")
        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.setObjectName("btn_secondary")
        self.browse_btn.setFixedWidth(80)
        save_row.addWidget(self.save_path_edit)
        save_row.addWidget(self.browse_btn)
        file_fl.addRow("Save to:", save_row)

        layout.addWidget(file_group)

        # ── Download Options ─────────────────────────────────────
        opt_group = QGroupBox("Download Options")
        opt_fl = QFormLayout(opt_group)
        opt_fl.setSpacing(8)
        opt_fl.setContentsMargins(10, 14, 10, 10)

        self.conn_spin = QSpinBox()
        self.conn_spin.setRange(1, 32)
        self.conn_spin.setValue(8)
        self.conn_spin.setSuffix(" connections")
        opt_fl.addRow("Parallel Connections:", self.conn_spin)

        self.speed_check = QCheckBox("Enable speed limit")
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 100000)
        self.speed_spin.setValue(1024)
        self.speed_spin.setSuffix(" KB/s")
        self.speed_spin.setEnabled(False)
        speed_row = QHBoxLayout()
        speed_row.setSpacing(6)
        speed_row.addWidget(self.speed_check)
        speed_row.addWidget(self.speed_spin)
        speed_row.addStretch()
        opt_fl.addRow("Speed Limit:", speed_row)

        layout.addWidget(opt_group)

        # ── Buttons ──────────────────────────────────────────────
        layout.addStretch(1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("btn_cancel")
        self.cancel_btn.setMinimumWidth(100)
        self.ok_btn = QPushButton("+ Start Download")
        self.ok_btn.setMinimumWidth(150)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.ok_btn)
        layout.addLayout(btn_row)

    def _connect_signals(self):
        self.probe_btn.clicked.connect(self._probe_url)
        self.browse_btn.clicked.connect(self._browse_save_path)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self._accept)
        self.url_edit.textChanged.connect(self._on_url_changed)
        self.filename_edit.textChanged.connect(self._on_filename_changed)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self.speed_check.toggled.connect(self.speed_spin.setEnabled)

    def _on_url_changed(self, text):
        # User changed URL manually — reset auto-probe state
        self._auto_probe_done = False
        self._original_url = text

        # Only auto-fill filename from URL if it has a proper extension (e.g. file.mp4)
        if text and not self.filename_edit.text():
            name = filename_from_url(text)
            if name and '.' in name:
                self.filename_edit.blockSignals(True)
                self.filename_edit.setText(name)
                self.filename_edit.blockSignals(False)
                self._on_filename_changed(name)

        # Auto-probe 800 ms after the user stops typing
        if text.strip().startswith('http'):
            self._typing_timer.start(800)
        else:
            self._typing_timer.stop()

    def _on_filename_changed(self, name):
        cat = get_category(name, self.categories)
        idx = self.category_combo.findText(cat)
        if idx >= 0:
            if self.category_combo.currentIndex() == idx:
                # Same category, but filename changed - must refresh path manually
                self._refresh_save_path()
            else:
                self.category_combo.setCurrentIndex(idx)

    def _on_category_changed(self, cat_name):
        self._refresh_save_path()

    def _refresh_save_path(self):
        cat_name = self.category_combo.currentText()
        fname = self.filename_edit.text()
        if not fname:
            fname = "download" # placeholder until detected

        for c in self.categories:
            if c['name'] == cat_name:
                self.save_path_edit.setText(os.path.join(c['save_path'], fname))
                break

    def _probe_url(self):
        url = self.url_edit.text().strip()
        if not url or not url.startswith('http'):
            return
        if self._probe_in_progress:
            return  # Already probing, don't start another
        if self._auto_probe_done and not self.probe_btn.isEnabled():
            return  # Guard: timer re-fire while probe in progress
        self._auto_probe_done = True    # Block the 800ms timer from firing again
        self._probe_in_progress = True
        self.probe_status.setText("\u231b Detecting file info\u2026")
        self.probe_btn.setEnabled(False)
        # Always probe the original URL, not a CDN redirect
        probe_target = self._original_url or url
        referer = self.referer_edit.text().strip()
        self._probe_thread = ProbeThread(probe_target, referer)
        self._probe_thread.result.connect(self._on_probe_result)
        self._probe_thread.start()

    def _on_probe_result(self, final_url, size, accepts_ranges, content_disposition):
        self._probe_in_progress = False
        self.probe_btn.setEnabled(True)
        self._typing_timer.stop()    # Stop any pending timer re-fire

        # Update URL field to CDN URL WITHOUT triggering _on_url_changed
        if final_url and final_url != self.url_edit.text():
            self.url_edit.blockSignals(True)
            self.url_edit.setText(final_url)
            self.url_edit.blockSignals(False)

        # Extract filename: use _original_url for YouTube-style page URLs
        name = filename_from_url(self._original_url or final_url, content_disposition)
        if name and name != self.filename_edit.text():
            self.filename_edit.blockSignals(True)
            self.filename_edit.setText(name)
            self.filename_edit.blockSignals(False)
            self._on_filename_changed(name)

        if size > 0:
            self._probed_size = size
            self.size_label.setText(format_size(size) + (" (resumable)" if accepts_ranges else ""))
            self.probe_status.setText("\u2713 File info detected" + ("" if accepts_ranges else " (no resume support)"))
        else:
            self._auto_probe_done = False  # Allow manual retry via button
            self.size_label.setText("Unknown (streaming?)")
            self.probe_status.setText("\u26a0 Could not detect file size \u2014 click Detect Info to retry")

    def _browse_save_path(self):
        fname = self.filename_edit.text() or "download"
        current = self.save_path_edit.text() or os.path.expanduser("~\\Downloads")
        folder = QFileDialog.getExistingDirectory(self, "Select Save Folder", current)
        if folder:
            self.save_path_edit.setText(os.path.join(folder, fname))

    def _accept(self):
        url = self.url_edit.text().strip()
        if not url:
            self.url_edit.setFocus()
            return
        filename = self.filename_edit.text().strip() or filename_from_url(url)
        save_path = self.save_path_edit.text().strip()
        if not save_path:
            cat = self.category_combo.currentText()
            from core.file_manager import get_save_path
            save_path = get_save_path(filename, cat, self.categories)

        params = {
            'url': url,
            'filename': filename,
            'filepath': save_path if save_path.endswith(filename) else os.path.join(save_path, filename),
            'connections': self.conn_spin.value(),
            'speed_limit': self.speed_spin.value() * 1024 if self.speed_check.isChecked() else 0,
            'referer': self.referer_edit.text().strip(),
            'extra_headers': self.extra_headers,
            'category': self.category_combo.currentText(),
            'priority': 1,
            'size': getattr(self, '_probed_size', 0),
            'skip_probe': True,
        }
        self.download_requested.emit(params)
        self.accept()
