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
    """Create a stylish splash screen."""
    pix = QPixmap(480, 280)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)

    # Background
    grad = QLinearGradient(0, 0, 480, 280)
    grad.setColorAt(0, QColor("#3b4252"))
    grad.setColorAt(0.5, QColor("#282a36"))
    grad.setColorAt(1, QColor("#1e1e2e"))
    painter.fillRect(0, 0, 480, 280, grad)

    # Accent bar
    painter.fillRect(0, 0, 480, 5, QColor("#0A84FF"))

    # Icon
    painter.setPen(QColor("#0A84FF"))
    painter.setFont(QFont("Segoe UI", 64, QFont.Weight.Bold))
    painter.drawText(20, 110, "⬇")

    # Title
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
    painter.drawText(110, 95, "WITTGrp")

    painter.setPen(QColor("#0A84FF"))
    painter.setFont(QFont("Segoe UI", 13))
    painter.drawText(110, 120, "WITTGrp Download Manage")

    painter.setPen(QColor("#6080a0"))
    painter.setFont(QFont("Segoe UI", 11))
    painter.drawText(110, 145, "Multi-threaded • Resumable • Fast")

    # Bottom bar
    painter.fillRect(0, 250, 480, 30, QColor("#282a36"))
    painter.setPen(QColor("#6080a0"))
    painter.setFont(QFont("Segoe UI", 10))
    painter.drawText(20, 270, "Loading… please wait")
    painter.drawText(380, 270, "v1.0.0")

    painter.end()

    splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.setFont(QFont("Segoe UI", 11))
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
