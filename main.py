"""
WITTGrp Download Manager
Main application entry point
"""
import sys
import os
import logging
import warnings
import threading
import time
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('idm.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger('WITTGrp')

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt6.QtCore import Qt, QTimer, QThread
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient

from core.database import Database
from core.queue_manager import QueueManager
from core.extension_server import ExtensionServer
from ui.main_window import MainWindow
from ui.stylesheet import STYLESHEET


def create_splash_screen(app: QApplication) -> QSplashScreen:
    """Create a modern, clean splash screen with no overlapping elements."""
    W, H = 520, 290
    pix = QPixmap(W, H)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # ── Background ──────────────────────────────────────────────
    from PyQt6.QtGui import QBrush
    grad = QLinearGradient(0, 0, W, H)
    grad.setColorAt(0.0, QColor("#1e2030"))
    grad.setColorAt(1.0, QColor("#13141f"))
    painter.fillRect(0, 0, W, H, grad)

    # Top accent bar
    painter.fillRect(0, 0, W, 4, QColor("#0A84FF"))

    # ── Icon box (left column) ──────────────────────────────────
    icon_x, icon_y, icon_size = 28, 60, 76
    painter.setBrush(QBrush(QColor("#0A84FF")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(icon_x, icon_y, icon_size, icon_size, 14, 14)

    painter.setPen(QColor("#ffffff"))
    f_icon = QFont("Segoe UI", 38, QFont.Weight.Bold)
    painter.setFont(f_icon)
    # Center the arrow inside the box
    painter.drawText(
        icon_x, icon_y + 6, icon_size, icon_size,
        Qt.AlignmentFlag.AlignCenter, "⬇"
    )

    # ── Text (right column) ─────────────────────────────────────
    tx = icon_x + icon_size + 20  # text start x
    ty = icon_y                   # text start y (aligned with top of icon)

    # App name
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
    painter.drawText(tx, ty + 36, "WITTGrp")

    # Subtitle
    painter.setPen(QColor("#47A1FF"))
    painter.setFont(QFont("Segoe UI", 12))
    painter.drawText(tx, ty + 60, "Download Manager")

    # Tagline
    painter.setPen(QColor("#5a6a80"))
    painter.setFont(QFont("Segoe UI", 10))
    painter.drawText(tx, ty + 82, "Multi-threaded  •  Resumable  •  Fast")

    # ── Bottom status bar ───────────────────────────────────────
    painter.fillRect(0, H - 36, W, 36, QColor("#0d0e18"))
    painter.setPen(QColor("#47A1FF"))
    painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    painter.drawText(20, H - 10, "Loading interface…")
    painter.setPen(QColor("#3b4252"))
    painter.setFont(QFont("Segoe UI", 10))
    painter.drawText(W - 60, H - 10, "v1.0.0")

    painter.end()

    splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
    return splash


def main():
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("WITTGrp Download Manage")
    app.setOrganizationName("WITTGrp")
    app.setApplicationVersion("1.0.0")
    app.setStyleSheet(STYLESHEET)
    app.setQuitOnLastWindowClosed(False)

    # Splash screen
    splash = create_splash_screen(app)
    splash.show()
    app.processEvents()

    # Initialize database
    splash.showMessage("  Initializing database…", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("#e94560"))
    app.processEvents()
    db = Database()

    # Initialize queue manager
    splash.showMessage("  Starting download engine…", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("#e94560"))
    app.processEvents()
    queue = QueueManager(db=db)
    queue.load_from_db()

    # Start extension server
    splash.showMessage("  Starting browser integration server…", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("#e94560"))
    app.processEvents()
    port = int(db.get_setting('extension_server_port', '9614'))

    # Create main window (need it for the dialog callback)
    splash.showMessage("  Loading interface…", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("#e94560"))
    app.processEvents()
    window = MainWindow(queue_manager=queue, db=db)

    ext_server = ExtensionServer(
        port=port,
        queue_manager=queue,
        add_dialog_callback=lambda *args: window.add_url_signal.emit(args[-4], args[-3], args[-2], args[-1])
    )
    ext_server.start()

    # Watchdog thread to catch UI freezes
    main_thread_id = threading.get_ident()
    _ui_alive_time = time.time()

    def _ui_heartbeat():
        nonlocal _ui_alive_time
        _ui_alive_time = time.time()

    ui_timer = QTimer()
    ui_timer.timeout.connect(_ui_heartbeat)
    ui_timer.start(500)

    def _watchdog():
        import traceback, sys
        while True:
            time.sleep(2)
            if time.time() - _ui_alive_time > 3.0:
                with open('freeze_dump.txt', 'a') as f:
                    f.write(f"\n--- UI THREAD DEADLOCK DETECTED AT {time.ctime()} ---\n")
                    frame = sys._current_frames().get(main_thread_id)
                    if frame:
                        traceback.print_stack(frame, file=f)
                time.sleep(10) # Wait before dumping again

    threading.Thread(target=_watchdog, daemon=True).start()

    # Show main window
    QTimer.singleShot(1800, lambda: (splash.finish(window), window.show()))

    logger.info("WITTGrp started successfully")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
