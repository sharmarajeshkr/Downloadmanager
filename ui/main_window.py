"""
Main Window - IDM-style download manager UI
"""
import os
import sys
import time
import threading
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStatusBar, QLabel, QMenu, QSystemTrayIcon, QMessageBox,
    QApplication, QProgressBar, QSplitter, QTreeWidget, QTreeWidgetItem,
    QFrame, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, QUrl, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QIcon, QAction, QFont, QColor, QBrush, QPixmap, QPainter,
    QClipboard, QDesktopServices
)

from core.downloader import DownloadStatus
from core.file_manager import format_size, format_speed, format_eta
from ui.add_download_dialog import AddDownloadDialog
from ui.settings_dialog import SettingsDialog

SVG_DIR = os.path.join(os.path.dirname(__file__), "assets", "svg")


# Column indices
COL_NAME     = 0
COL_SIZE     = 1
COL_STATUS   = 2
COL_PROGRESS = 3
COL_SPEED    = 4
COL_ETA      = 5
COL_CATEGORY = 6
COL_DATE     = 7
NUM_COLS     = 8

STATUS_COLORS = {
    'Downloading': '#4ade80',
    'Completed':   '#60a5fa',
    'Paused':      '#fbbf24',
    'Error':       '#f87171',
    'Queued':      '#a78bfa',
    'Stopped':     '#94a3b8',
    'Merging':     '#34d399',
}


class ProgressDelegate:
    """Renders progress bar inside table cell."""
    pass


class CustomTitleBar(QWidget):
    """Custom frameless title bar with drag support and window controls."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(38)
        self.setStyleSheet("background: #1e1e2e; border-bottom: 1px solid #3b4252;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)

        title_label = QLabel("🚀 WITTGrp Download Manager")
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
                QPushButton { background: transparent; color: #8892b0; border: none; font-size: 14px; border-radius: 0px; padding-bottom: 4px; }
                QPushButton:hover { background: #3b4252; color: #ffffff; }
            """)
            layout.addWidget(btn)

        self.btn_close.setStyleSheet("""
            QPushButton { background: transparent; color: #8892b0; border: none; font-size: 14px; border-radius: 0px; padding-bottom: 4px; }
            QPushButton:hover { background: #e81123; color: #ffffff; }
        """)

        self.btn_min.clicked.connect(self.parent.showMinimized)
        self.btn_max.clicked.connect(self.toggle_max_restore)
        self.btn_close.clicked.connect(self.parent.close)

        self.start_pos = None

    def toggle_max_restore(self):
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


class MainWindow(QMainWindow):
    task_update_signal = pyqtSignal(object)  # thread-safe task update
    add_url_signal = pyqtSignal(str, str, str, dict) # thread-safe add url dialog from extension

    def __init__(self, queue_manager, db):
        super().__init__()
        self.queue_manager = queue_manager
        self.db = db
        self._task_rows = {}  # task_id -> row index
        self._clipboard_last = ''

        self.setWindowTitle("WITTGrp Download Manager")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setMinimumSize(800, 350)
        self.resize(1050, 450)

        self._setup_ui()
        self._setup_tray()
        self._setup_signals()
        self._start_clipboard_monitor()
        self._load_existing_tasks()
        self._center_window()

    def _center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2,
                  (screen.height() - size.height()) // 2)

    def _toggle_sidebar(self):
        is_collapsed = self.sidebar.maximumWidth() == 0
        target_width = 180 if is_collapsed else 0

        self.sidebar_anim = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.sidebar_anim.setDuration(300)
        self.sidebar_anim.setStartValue(self.sidebar.width() if not is_collapsed else 0)
        self.sidebar_anim.setEndValue(target_width)
        self.sidebar_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.sidebar_anim.start()

    # ── UI Setup ─────────────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        self._setup_menubar()
        
        # We need to explicitly place the menubar inside our VBox to play nice with frameless
        main_layout.addWidget(self.menuBar())

        self._setup_toolbar()

        # Splitter: sidebar + download list
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Sidebar
        self.sidebar = self._build_sidebar()
        splitter.addWidget(self.sidebar)

        # Download table
        self.table = self._build_table()
        splitter.addWidget(self.table)
        splitter.setSizes([180, 900])

        main_layout.addWidget(splitter)

        # Status bar
        self._setup_statusbar()

    def _setup_menubar(self):
        mb = self.menuBar()
        file_menu = mb.addMenu("File")
        a1 = file_menu.addAction("Add URL…")
        a1.triggered.connect(self._show_add_dialog)
        a1.setShortcut("Ctrl+N")
        a2 = file_menu.addAction("Add Batch URLs…")
        a2.triggered.connect(self._show_batch_dialog)
        file_menu.addSeparator()
        a3 = file_menu.addAction("Exit")
        a3.triggered.connect(self.close)

        dl_menu = mb.addMenu("Downloads")
        a4 = dl_menu.addAction("Start All")
        a4.triggered.connect(self.queue_manager.start_all)
        a5 = dl_menu.addAction("Stop All")
        a5.triggered.connect(self.queue_manager.stop_all)
        dl_menu.addSeparator()
        a6 = dl_menu.addAction("Remove Completed")
        a6.triggered.connect(self._remove_completed)

        view_menu = mb.addMenu("View")
        a7 = view_menu.addAction("Open Downloads Folder")
        a7.triggered.connect(self._open_downloads_folder)

        tools_menu = mb.addMenu("Tools")
        a8 = tools_menu.addAction("Settings…")
        a8.triggered.connect(self._show_settings)
        a8.setShortcut("Ctrl+,")
        tools_menu.addSeparator()
        a9 = tools_menu.addAction("Browser Extension Guide…")
        a9.triggered.connect(self._show_extension_guide)

        mb.addMenu("Help")

    def _setup_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        menu_action = QAction(QIcon(os.path.join(SVG_DIR, 'menu.svg')), "Menu", self)
        menu_action.setToolTip("Toggle Sidebar")
        menu_action.triggered.connect(self._toggle_sidebar)
        tb.addAction(menu_action)
        
        tb.addSeparator()

        add_action = QAction(QIcon(os.path.join(SVG_DIR, 'add.svg')), "Add URL", self)
        add_action.setToolTip("Add new download (Ctrl+N)")
        add_action.triggered.connect(self._show_add_dialog)
        tb.addAction(add_action)

        tb.addSeparator()

        start_action = QAction(QIcon(os.path.join(SVG_DIR, 'play.svg')), "Start All", self)
        start_action.triggered.connect(self.queue_manager.start_all)
        tb.addAction(start_action)

        stop_action = QAction(QIcon(os.path.join(SVG_DIR, 'stop.svg')), "Stop All", self)
        stop_action.triggered.connect(self.queue_manager.stop_all)
        tb.addAction(stop_action)

        tb.addSeparator()

        settings_action = QAction(QIcon(os.path.join(SVG_DIR, 'settings.svg')), "Settings", self)
        settings_action.triggered.connect(self._show_settings)
        tb.addAction(settings_action)

        tb.addSeparator()

        open_folder_action = QAction(QIcon(os.path.join(SVG_DIR, 'folder.svg')), "Open Folder", self)
        open_folder_action.triggered.connect(self._open_downloads_folder)
        tb.addAction(open_folder_action)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        # Stats label
        self.speed_label = QLabel("  🚀 0 B/s  |  ⬇ 0 active  ")
        self.speed_label.setStyleSheet("color: #4ade80; font-weight: 600; padding-right: 12px;")
        tb.addWidget(self.speed_label)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("background: #1e1e2e; border-right: 1px solid #3b4252;")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(2)

        logo = QLabel("⬇ WITTGrp")
        logo.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        logo.setStyleSheet("color: #0A84FF; padding: 4px 4px 12px 4px;")
        layout.addWidget(logo)

        self.filter_tree = QTreeWidget()
        self.filter_tree.setHeaderHidden(True)
        self.filter_tree.setRootIsDecorated(False)
        self.filter_tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.filter_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.filter_tree.setStyleSheet("""
            QTreeWidget { background: transparent; border: none; outline: none; }
            QTreeWidget::item { padding: 4px 6px; border-radius: 4px; color: #e2e2e3; }
            QTreeWidget::item:selected { background: rgba(10, 132, 255, 0.25); color: #fff; }
            QTreeWidget::item:hover { background: rgba(255, 255, 255, 0.05); }
        """)
        categories = ["All Downloads", "Downloading", "Completed", "Paused",
                      "Videos", "Music", "Documents", "Programs", "Archives", "Other"]
        for cat in categories:
            item = QTreeWidgetItem([cat])
            self.filter_tree.addTopLevelItem(item)
        self.filter_tree.topLevelItem(0).setSelected(True)
        self.filter_tree.itemClicked.connect(self._filter_by_category)

        layout.addWidget(self.filter_tree)
        layout.addStretch()

        # Version label
        ver = QLabel("v1.0.0 | Port 9614")
        ver.setStyleSheet("color: #404060; font-size: 10px; padding: 4px;")
        layout.addWidget(ver)

        return sidebar

    def _build_table(self) -> QTableWidget:
        table = QTableWidget(0, NUM_COLS)
        table.setHorizontalHeaderLabels([
            "File Name", "Size", "Status", "Progress",
            "Speed", "Time Left", "Category", "Date Added"
        ])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)
        table.doubleClicked.connect(self._on_double_click)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setRowHeight(0, 44)

        hh = table.horizontalHeader()
        hh.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_PROGRESS, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_SPEED, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_ETA, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_CATEGORY, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_DATE, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(COL_SIZE, 90)
        table.setColumnWidth(COL_STATUS, 100)
        table.setColumnWidth(COL_PROGRESS, 160)
        table.setColumnWidth(COL_SPEED, 90)
        table.setColumnWidth(COL_ETA, 75)
        table.setColumnWidth(COL_CATEGORY, 90)
        table.setColumnWidth(COL_DATE, 130)

        return table

    def _setup_statusbar(self):
        sb = self.statusBar()
        self.status_label = QLabel("Ready")
        self.total_label = QLabel("")
        self.active_label = QLabel("")
        sb.addWidget(self.status_label)
        sb.addPermanentWidget(self.total_label)
        sb.addPermanentWidget(self.active_label)

    def _setup_tray(self):
        # Create icon programmatically
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setBrush(QColor("#e94560"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 32, 32, 6, 6)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "⬇")
        painter.end()

        self.tray_icon = QSystemTrayIcon(QIcon(pix), self)
        tray_menu = QMenu()
        t1 = tray_menu.addAction("Show WITTGrp")
        t1.triggered.connect(self.show_normal)
        t2 = tray_menu.addAction("Add URL…")
        t2.triggered.connect(self._show_add_dialog)
        tray_menu.addSeparator()
        t3 = tray_menu.addAction("Exit")
        t3.triggered.connect(self._quit_app)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _setup_signals(self):
        self.task_update_signal.connect(self._update_task_row)
        self.add_url_signal.connect(self._emit_add_dialog)
        # Register callback with queue manager
        self.queue_manager.on_task_update = self._on_task_update

        # Refresh timer for speed/ETA
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_stats)
        self.refresh_timer.start(1000)

    # ── Task Loading & Display ───────────────────────────────────────────

    def _load_existing_tasks(self):
        for task in self.queue_manager.get_tasks():
            self._add_task_row(task)

    def _on_task_update(self, task):
        """Called from any thread — emits signal to update UI in main thread."""
        self.task_update_signal.emit(task)

    def _add_task_row(self, task):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 40)
        self._task_rows[task.id] = row

        for col in range(NUM_COLS):
            item = QTableWidgetItem("")
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            self.table.setItem(row, col, item)

        # Progress bar widget
        pb = QProgressBar()
        pb.setRange(0, 100)
        pb.setValue(0)
        pb.setTextVisible(True)
        pb.setFormat("%p%")
        self.table.setCellWidget(row, COL_PROGRESS, pb)

        self._refresh_task_row(row, task)

    def _update_task_row(self, task):
        if task.id not in self._task_rows:
            self._add_task_row(task)
        else:
            row = self._task_rows[task.id]
            self._refresh_task_row(row, task)
        self._refresh_stats()

    def _refresh_task_row(self, row: int, task):
        status_str = task.status.value if hasattr(task.status, 'value') else str(task.status)
        color = STATUS_COLORS.get(status_str, '#c0c0e0')

        # Name
        self.table.item(row, COL_NAME).setText(task.filename)
        # Size
        self.table.item(row, COL_SIZE).setText(format_size(task.total_size))
        # Status
        status_item = self.table.item(row, COL_STATUS)
        status_item.setText(status_str)
        status_item.setForeground(QBrush(QColor(color)))
        # Speed
        self.table.item(row, COL_SPEED).setText(
            format_speed(task.speed) if task.speed > 0 and status_str == 'Downloading' else "—"
        )
        # ETA
        self.table.item(row, COL_ETA).setText(
            format_eta(task.eta) if task.eta > 0 else "—"
        )
        # Category
        self.table.item(row, COL_CATEGORY).setText(task.category)
        # Date
        import datetime
        self.table.item(row, COL_DATE).setText(
            datetime.datetime.fromtimestamp(task.added_at).strftime("%m/%d %H:%M")
        )
        # Progress bar
        pb = self.table.cellWidget(row, COL_PROGRESS)
        if pb and task.total_size > 0:
            pct = int(task.downloaded / task.total_size * 100)
            pb.setValue(pct)
            pb.setFormat(f"{pct}% — {format_size(task.downloaded)}")
        elif pb and status_str == 'Completed':
            pb.setValue(100)
            pb.setFormat("100% ✓")

    def _refresh_stats(self):
        tasks = self.queue_manager.get_tasks()
        active = [t for t in tasks if t.status == DownloadStatus.DOWNLOADING]
        total_speed = sum(t.speed for t in active)
        self.speed_label.setText(
            f"  🚀 {format_speed(total_speed)}  |  ⬇ {len(active)} active  "
        )
        self.status_label.setText(
            f"  Total: {len(tasks)} | Active: {len(active)} | "
            f"Completed: {sum(1 for t in tasks if t.status == DownloadStatus.COMPLETED)}"
        )

    # ── Context Menu ─────────────────────────────────────────────────────

    def _show_context_menu(self, position):
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        task_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        task = self.queue_manager.get_task(task_id)
        if not task:
            return

        menu = QMenu(self)
        status = task.status

        if status == DownloadStatus.DOWNLOADING:
            m1 = menu.addAction("⏸  Pause")
            m1.triggered.connect(lambda: self._pause_task(task_id))
            m2 = menu.addAction("⏹  Stop")
            m2.triggered.connect(lambda: self._stop_task(task_id))
        elif status in (DownloadStatus.PAUSED, DownloadStatus.STOPPED, DownloadStatus.QUEUED):
            m3 = menu.addAction("▶  Resume")
            m3.triggered.connect(lambda: self._resume_task(task_id))
        elif status == DownloadStatus.ERROR:
            m4 = menu.addAction("🔄  Retry")
            m4.triggered.connect(lambda: self._retry_task(task_id))

        menu.addSeparator()
        if status == DownloadStatus.COMPLETED:
            m5 = menu.addAction("📂  Open File")
            m5.triggered.connect(lambda: self._open_file(task))
            m6 = menu.addAction("📁  Open Folder")
            m6.triggered.connect(lambda: self._open_file_folder(task))
        m7 = menu.addAction("🔗  Copy URL")
        m7.triggered.connect(lambda: self._copy_url(task))
        menu.addSeparator()
        m8 = menu.addAction("❌  Remove")
        m8.triggered.connect(lambda: self._remove_task(task_id, delete=False))
        m9 = menu.addAction("🗑  Remove & Delete File")
        m9.triggered.connect(lambda: self._remove_task(task_id, delete=True))

        menu.exec(self.table.viewport().mapToGlobal(position))

    def _on_double_click(self, index):
        row = index.row()
        task_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        task = self.queue_manager.get_task(task_id)
        if task and task.status == DownloadStatus.COMPLETED:
            self._open_file(task)

    # ── Actions ──────────────────────────────────────────────────────────

    def _emit_add_dialog(self, url, filename, referer, extra_headers):
        self._show_add_dialog(False, url, filename, referer, extra_headers)

    def _show_add_dialog(self, _checked=False, url='', filename='', referer='', extra_headers=None):
        dlg = AddDownloadDialog(
            parent=self,
            url=url, filename=filename,
            referer=referer, extra_headers=extra_headers,
            categories=self.db.get_categories(),
            db=self.db,
        )
        dlg.download_requested.connect(self._on_download_requested)
        dlg.exec()

    def _show_batch_dialog(self):
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getMultiLineText(
            self, "Add Batch URLs",
            "Enter one URL per line:"
        )
        if ok and text.strip():
            urls = [u.strip() for u in text.strip().splitlines() if u.strip()]
            for url in urls:
                self.queue_manager.add_download(url=url, auto_start=True)
            self._load_existing_tasks()

    def _on_download_requested(self, params: dict):
        task_id = self.queue_manager.add_download(
            url=params['url'],
            filename=params.get('filename'),
            save_path=params.get('filepath'),
            connections=params.get('connections', 8),
            speed_limit=params.get('speed_limit', 0),
            referer=params.get('referer', ''),
            extra_headers=params.get('extra_headers', {}),
            auto_start=True,
            size=params.get('size', 0),
            skip_probe=params.get('skip_probe', False),
        )
        self.tray_icon.showMessage(
            "WITTGrp - Download Started",
            f"⬇ {params.get('filename', 'File')}",
            QSystemTrayIcon.MessageIcon.Information, 3000
        )

    def _show_settings(self):
        dlg = SettingsDialog(parent=self, db=self.db)
        dlg.exec()

    def _show_extension_guide(self):
        ext_path = os.path.abspath("browser_extension/chrome")
        QMessageBox.information(self, "Browser Extension Installation",
            f"Extension folder: {ext_path}\n\n"
            "To install in Chrome/Brave/Opera:\n"
            "1. Open: chrome://extensions\n"
            "2. Enable 'Developer mode'\n"
            "3. Click 'Load unpacked'\n"
            "4. Select the folder above\n\n"
            "The extension will automatically capture video and file links and send them to WITTGrp Download Manager."
        )

    def _pause_task(self, task_id):
        self.queue_manager.pause(task_id)

    def _resume_task(self, task_id):
        self.queue_manager.resume(task_id)

    def _stop_task(self, task_id):
        self.queue_manager.stop(task_id)

    def _retry_task(self, task_id):
        task = self.queue_manager.get_task(task_id)
        if task:
            task.status = DownloadStatus.QUEUED
            task._downloader = None
            self.queue_manager._try_start_next()

    def _remove_task(self, task_id: str, delete: bool = False):
        self.queue_manager.remove(task_id, delete_file=delete)
        if task_id in self._task_rows:
            row = self._task_rows.pop(task_id)
            self.table.removeRow(row)
            # Re-index
            self._task_rows = {tid: (r if r < row else r - 1)
                               for tid, r in self._task_rows.items()}

    def _remove_completed(self):
        to_remove = [t.id for t in self.queue_manager.get_tasks()
                     if t.status == DownloadStatus.COMPLETED]
        for tid in to_remove:
            self._remove_task(tid)

    def _open_file(self, task):
        if os.path.exists(task.filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(task.filepath))

    def _open_file_folder(self, task):
        folder = os.path.dirname(task.filepath)
        if os.path.isdir(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _copy_url(self, task):
        QApplication.clipboard().setText(task.url)

    def _open_downloads_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(r"D:\idm\downloads"))

    def _filter_by_category(self, item):
        filter_text = item.text(0)
        for row in range(self.table.rowCount()):
            cat_item = self.table.item(row, COL_CATEGORY)
            status_item = self.table.item(row, COL_STATUS)
            if filter_text == "All Downloads":
                self.table.setRowHidden(row, False)
            elif filter_text in ("Downloading", "Completed", "Paused"):
                hidden = status_item.text() != filter_text if status_item else True
                self.table.setRowHidden(row, hidden)
            else:
                hidden = cat_item.text() != filter_text if cat_item else True
                self.table.setRowHidden(row, hidden)

    # ── Clipboard Monitor ────────────────────────────────────────────────

    def _start_clipboard_monitor(self):
        def monitor():
            while True:
                time.sleep(1)
                try:
                    if self.db.get_setting('monitor_clipboard', 'true') == 'true':
                        clipboard = QApplication.clipboard()
                        text = clipboard.text().strip()
                        if text != self._clipboard_last and self._is_downloadable_url(text):
                            self._clipboard_last = text
                            self.task_update_signal.emit(type('CB', (), {'id': '__clipboard__', 'url': text, '_cb': True})())
                except Exception:
                    pass
        t = threading.Thread(target=monitor, daemon=True)
        t.start()

    def _is_downloadable_url(self, text: str) -> bool:
        if not text.startswith(('http://', 'https://', 'ftp://')):
            return False
        lower = text.lower()
        # Direct file extensions
        EXT = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mp3',
               '.flac', '.zip', '.rar', '.7z', '.exe', '.msi', '.pdf', '.doc',
               '.docx', '.iso', '.apk', '.dmg', '.tar.gz', '.epub', '.m4v')
        return any(lower.split('?')[0].endswith(ext) for ext in EXT)

    # ── Tray ─────────────────────────────────────────────────────────────

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_normal()

    def show_normal(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        if self.db.get_setting('minimize_to_tray', 'true') == 'true':
            event.ignore()
            self.hide()
            self.tray_icon.showMessage("WITTGrp", "Running in background", 2000)
        else:
            self._quit_app()

    def _quit_app(self):
        self.queue_manager.stop_all()
        self.tray_icon.hide()
        QApplication.quit()
