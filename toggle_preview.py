"""Standalone mockup of 4 toggle style options."""
import sys
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter, QPainterPath, QBrush, QPen
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QButtonGroup, QFrame, QSizePolicy,
)

BG       = "#0a1628"
INPUT_BG = "#0f2040"
BORDER   = "#1a3666"
MUTED    = "#8aaad0"
ACCENT   = "#2d6bc4"
ACTIVE   = "#1a4a8a"
TEXT     = "#c8d8f0"
WHITE    = "#ffffff"


def section(title):
    lbl = QLabel(title)
    lbl.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: bold; letter-spacing: 1px; padding-top: 8px;")
    return lbl


# ── Option 1: Pill toggle ─────────────────────────────────────────────────────

class PillToggle(QWidget):
    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self._labels = labels
        self._selected = 0
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"pill_x", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pill_x = 0.0

    def get_pill_x(self): return self._pill_x
    def set_pill_x(self, v):
        self._pill_x = v
        self.update()
    pill_x = Property(float, get_pill_x, set_pill_x)

    def mousePressEvent(self, e):
        idx = 0 if e.position().x() < self.width() / 2 else 1
        if idx != self._selected:
            self._selected = idx
            target = (self.width() / 2) * idx
            self._anim.setStartValue(self._pill_x)
            self._anim.setEndValue(target)
            self._anim.start()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        # track
        track = QPainterPath()
        track.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 10, 10)
        p.fillPath(track, QColor(INPUT_BG))
        p.setPen(QPen(QColor(BORDER), 1))
        p.drawPath(track)

        # pill
        pw = r.width() / 2 - 4
        pill = QPainterPath()
        pill.addRoundedRect(self._pill_x + 2, 3, pw, r.height() - 6, 8, 8)
        p.fillPath(pill, QColor(ACTIVE))
        p.setPen(Qt.NoPen)

        # labels
        p.setPen(QColor(WHITE))
        half = r.width() // 2
        for i, lbl in enumerate(self._labels):
            p.setPen(QColor(WHITE if i == self._selected else MUTED))
            p.setFont(self.font())
            p.drawText(QRect(i * half, 0, half, r.height()), Qt.AlignCenter, lbl)

        p.end()


# ── Option 2: Flat underline tabs ────────────────────────────────────────────

def make_underline_toggle():
    w = QWidget()
    layout = QHBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    group = QButtonGroup(w)
    for i, (icon, label) in enumerate([("📷", "Camera"), ("⌨️", "Type Manually / External Scanner")]):
        btn = QPushButton(f"{icon}  {label}")
        btn.setCheckable(True)
        btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        btn.setFixedHeight(42)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                border-radius: 0;
                color: {MUTED};
                font-size: 13px;
                padding: 0 8px;
            }}
            QPushButton:checked {{
                color: {WHITE};
                border-bottom: 2px solid {ACCENT};
            }}
            QPushButton:hover:!checked {{
                color: {TEXT};
                border-bottom: 2px solid {BORDER};
            }}
        """)
        group.addButton(btn, i)
        layout.addWidget(btn, 1)

    group.button(0).setChecked(True)
    return w


# ── Option 3: Two separate cards ─────────────────────────────────────────────

def make_card_toggle():
    w = QWidget()
    layout = QHBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    group = QButtonGroup(w)
    for i, (icon, label) in enumerate([("📷", "Camera"), ("⌨️", "Type Manually /\nExternal Scanner")]):
        btn = QPushButton(f"{icon}  {label}")
        btn.setCheckable(True)
        btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        btn.setFixedHeight(54)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {INPUT_BG};
                border: 1px solid {BORDER};
                border-radius: 8px;
                color: {MUTED};
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:checked {{
                background: {ACTIVE};
                border: 1px solid {ACCENT};
                color: {WHITE};
                font-weight: bold;
            }}
            QPushButton:hover:!checked {{
                border-color: {ACCENT};
                color: {TEXT};
            }}
        """)
        group.addButton(btn, i)
        layout.addWidget(btn, 1)

    group.button(0).setChecked(True)
    return w


# ── Option 4: Vertical radio rows ────────────────────────────────────────────

def make_vertical_toggle():
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    group = QButtonGroup(w)
    options = [("📷", "Camera", "Use the built-in or USB camera to scan QR codes"),
               ("⌨️", "Type Manually / External Scanner", "Type a code or use a USB barcode scanner")]

    for i, (icon, label, sub) in enumerate(options):
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setFixedHeight(52)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {INPUT_BG};
                border: 1px solid {BORDER};
                border-radius: 8px;
                text-align: left;
                padding: 0 14px;
            }}
            QPushButton:checked {{
                background: {ACTIVE};
                border: 1px solid {ACCENT};
            }}
            QPushButton:hover:!checked {{
                border-color: {ACCENT};
            }}
        """)

        # overlay a label so we can do two-line text
        inner = QWidget(btn)
        inner.setAttribute(Qt.WA_TransparentForMouseEvents)
        row = QHBoxLayout(inner)
        row.setContentsMargins(14, 0, 14, 0)

        ico = QLabel(icon)
        ico.setStyleSheet("background: transparent; border: none; font-size: 18px;")
        row.addWidget(ico)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        title = QLabel(label)
        title.setStyleSheet(f"background: transparent; border: none; color: {WHITE}; font-weight: bold; font-size: 13px;")
        subtitle = QLabel(sub)
        subtitle.setStyleSheet(f"background: transparent; border: none; color: {MUTED}; font-size: 10px;")
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        row.addLayout(text_col)
        row.addStretch()

        # radio dot
        dot = QLabel("●" if i == 0 else "○")
        dot.setStyleSheet(f"background: transparent; border: none; color: {ACCENT}; font-size: 16px;")
        row.addWidget(dot)

        group.addButton(btn, i)
        layout.addWidget(btn)

        def on_toggle(checked, b=btn, d=dot, inner=inner):
            d.setText("●" if checked else "○")
            d.setStyleSheet(f"background: transparent; border: none; color: {'#ffffff' if checked else ACCENT}; font-size: 16px;")
        btn.toggled.connect(on_toggle)

        btn.resizeEvent = lambda e, iw=inner, b=btn: iw.setGeometry(b.rect())
        inner.setGeometry(btn.rect())

    group.button(0).setChecked(True)
    return w


# ── Main window ───────────────────────────────────────────────────────────────

app = QApplication(sys.argv)
app.setStyleSheet(f"""
    QWidget {{ background-color: {BG}; color: {TEXT};
               font-family: Segoe UI, Arial, sans-serif; font-size: 13px; }}
""")

win = QWidget()
win.setWindowTitle("Toggle Style Mockups")
win.setFixedWidth(520)

root = QVBoxLayout(win)
root.setContentsMargins(28, 24, 28, 28)
root.setSpacing(10)

def add_option(num, title, widget):
    root.addWidget(section(f"OPTION {num} — {title}"))
    root.addWidget(widget)
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet(f"color: {BORDER};")
    root.addWidget(line)

add_option(1, "PILL TOGGLE", PillToggle(["📷  Camera", "⌨️  Type / External Scanner"]))
add_option(2, "FLAT UNDERLINE TABS", make_underline_toggle())
add_option(3, "SEPARATE CARDS", make_card_toggle())
add_option(4, "VERTICAL RADIO ROWS", make_vertical_toggle())

root.addStretch()
win.show()
sys.exit(app.exec())
