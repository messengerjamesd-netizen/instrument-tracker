import sys
import os
import time

APP_VERSION     = "2.0"
APP_GITHUB_REPO = "messengerjamesd-netizen/instrument-tracker"

def _splash_msg(splash, app, text):
    """Show a status message on the splash and process events so it renders."""
    from PySide6.QtCore import Qt
    splash.showMessage(text, Qt.AlignBottom | Qt.AlignHCenter)
    app.processEvents()

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

# Force Windows Media Foundation for camera capture. PySide6 6.20 defaults
# to the ffmpeg backend, which is unreliable with Surface Pro cameras
# (errors with "not enough memory" or stays active without delivering frames).
# Must be set BEFORE any PySide6 multimedia import.
os.environ.setdefault("QT_MEDIA_BACKEND", "windows")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

import database as db
import config as cfg
from ui.main_window import MainWindow
from ui.themes import apply_theme
from ui.splash import make_splash
from ui.camera_manager import CameraManager

MIN_SPLASH_SECONDS = 2.5


def _icon_path():
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # PyInstaller extracts data files here, inside _internal/
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "icon.ico")


def _warmup():
    """Silent import-only run triggered by the installer to pre-warm Windows Defender's cache."""
    import cv2  # noqa: F401 — forces DLL scan now, during install, not on first user launch
    from PySide6.QtMultimedia import QMediaDevices  # noqa: F401
    sys.exit(0)


def main():
    if "--warmup" in sys.argv:
        _warmup()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    conf = cfg.load_config()
    apply_theme(app, conf["theme"], conf["font_size"],
                conf["custom_primary"], conf["custom_secondary"])

    icon_path = _icon_path()
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Show splash immediately and track how long it's been up
    splash_start = time.time()
    splash = make_splash(icon_path)
    splash.show()
    app.processEvents()

    # Do startup work
    try:
        _splash_msg(splash, app, "Initializing database…")
        db.initialize_db()
    except Exception as e:
        from PySide6.QtWidgets import QMessageBox
        splash.close()
        QMessageBox.critical(
            None, "Startup Error",
            f"Could not open the database:\n{e}\n\n"
            f"Location: {db.get_db_path()}"
        )
        sys.exit(1)

    _splash_msg(splash, app, "Loading…")
    window = MainWindow()

    # Enforce minimum splash display time without blocking the UI thread
    while time.time() - splash_start < MIN_SPLASH_SECONDS:
        app.processEvents()
        time.sleep(0.05)

    # PIN lock check before revealing the window
    if conf.get("pin_enabled") and conf.get("pin_hash"):
        from PySide6.QtWidgets import QDialog
        from ui.pin_dialog import PINLockDialog
        splash.close()
        pin_dlg = PINLockDialog(conf["pin_hash"])
        if pin_dlg.exec() != QDialog.Accepted:
            sys.exit(0)

    original_flags = window.windowFlags()
    window.setWindowFlags(original_flags | Qt.WindowStaysOnTopHint)
    window.showMaximized()
    splash.finish(window)

    def _drop_always_on_top():
        window.setWindowFlags(original_flags)
        window.showMaximized()

    from PySide6.QtCore import QTimer
    QTimer.singleShot(500, _drop_always_on_top)

    # Start update check in background (no-op if repo is placeholder or offline)
    if not APP_GITHUB_REPO.startswith("PLACEHOLDER"):
        window._current_version = APP_VERSION
        window.start_update_check(APP_VERSION, APP_GITHUB_REPO)

    # Clean up camera on exit
    app.aboutToQuit.connect(CameraManager.instance().shutdown)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
