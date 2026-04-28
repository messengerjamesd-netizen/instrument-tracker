import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QSplashScreen


def _splash_image_path():
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # PyInstaller extracts data files here, inside _internal/
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "splash.png")


def make_splash(icon_path: str) -> QSplashScreen:
    splash_path = _splash_image_path()

    if os.path.exists(splash_path):
        pix = QPixmap(splash_path)
    elif os.path.exists(icon_path):
        # Fallback: scale up the icon
        pix = QPixmap(icon_path).scaled(
            600, 600,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    else:
        pix = QPixmap(600, 600)
        pix.fill(Qt.black)

    # Scale to a reasonable splash size while keeping the image square/proportional
    screen = None
    try:
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
    except Exception:
        pass

    if screen:
        sg = screen.geometry()
        max_w = int(sg.width() * 0.45)
        max_h = int(sg.height() * 0.65)
    else:
        max_w, max_h = 600, 600

    pix = pix.scaled(
        max_w, max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    splash = QSplashScreen(pix, Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(
        Qt.SplashScreen | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
    )
    return splash
