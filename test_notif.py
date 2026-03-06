import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
from ui.notification_widget import NotificationManager

app = QApplication(sys.argv)
win = QMainWindow()
win.resize(400, 300)

btn = QPushButton("Test Notif", win)
btn.clicked.connect(lambda: NotificationManager.get().notify("Complete", "test.mp4", action="success"))
btn.move(100, 100)

win.show()

# Show 3 test notifications immediately separated by small delays to test stacking
from PyQt6.QtCore import QTimer
QTimer.singleShot(500, lambda: NotificationManager.get().notify("Started", "ubuntu.iso", action="info"))
QTimer.singleShot(1000, lambda: NotificationManager.get().notify("Downloaded", "video.mp4", action="success"))
QTimer.singleShot(1500, lambda: NotificationManager.get().notify("Error", "failed_file.zip", action="error"))

# We won't block the AI with exec(), just run for a sec then quit
QTimer.singleShot(3000, app.quit)
app.exec()
