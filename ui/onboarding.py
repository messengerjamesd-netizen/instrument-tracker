from PySide6.QtCore import Qt, QRect, QPoint, QEvent, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication

import config as cfg


class OnboardingStep:
    def __init__(self, title, body, tab_index=-1, highlight_fn=None, on_enter=None):
        self.title = title
        self.body = body
        self.tab_index = tab_index
        self.highlight_fn = highlight_fn  # () -> list[QWidget] | None
        self.on_enter = on_enter          # () -> None, called after tab switch


_CARD_STYLE = """
QWidget#onboarding_card {
    background-color: #1a1a2e;
    border: 2px solid #9c6fe8;
    border-radius: 12px;
}
QWidget#onboarding_card QLabel {
    color: #e0e0f0;
    background: transparent;
    border: none;
}
"""


class OnboardingOverlay(QWidget):
    _PAD = 10
    _CARD_W = 480
    _CARD_MARGIN = 20

    def __init__(self, steps: list, main_window, on_finish=None):
        super().__init__(main_window)
        self._steps = steps
        self._mw = main_window
        self._on_finish = on_finish
        self._idx = 0
        self._highlight_rects: list[QRect] = []

        self.setGeometry(main_window.rect())
        main_window.installEventFilter(self)

        self._build_card()
        self._advance_to(0)
        self.show()
        self.raise_()

    def eventFilter(self, obj, event):
        if obj is self._mw and event.type() == QEvent.Resize:
            self.setGeometry(self._mw.rect())
            self._position_card()
            self.raise_()
        return False

    def _build_card(self):
        self._card = QWidget(self)
        self._card.setObjectName("onboarding_card")
        self._card.setStyleSheet(_CARD_STYLE)

        v = QVBoxLayout(self._card)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(6)

        self._step_lbl = QLabel()
        self._step_lbl.setStyleSheet(
            "color: #9c6fe8; font-size: 11px; background: transparent; border: none;"
        )
        self._step_lbl.setAlignment(Qt.AlignRight)
        v.addWidget(self._step_lbl)

        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #e8e0ff; background: transparent; border: none;"
        )
        self._title_lbl.setWordWrap(True)
        v.addWidget(self._title_lbl)

        self._body_lbl = QLabel()
        self._body_lbl.setStyleSheet(
            "font-size: 12px; color: #b8b8cc; background: transparent; border: none;"
        )
        self._body_lbl.setWordWrap(True)
        v.addWidget(self._body_lbl)

        v.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._skip_btn = QPushButton("Skip Tour")
        self._skip_btn.setStyleSheet(
            "color: #888; background: transparent; border: none; font-size: 12px;"
        )
        self._skip_btn.setCursor(Qt.PointingHandCursor)
        self._skip_btn.clicked.connect(self._finish)
        btn_row.addWidget(self._skip_btn)
        btn_row.addStretch()

        self._prev_btn = QPushButton("← Back")
        self._prev_btn.setMinimumHeight(32)
        self._prev_btn.setMinimumWidth(80)
        self._prev_btn.setStyleSheet(
            "background: #2a2a40; color: #ccc; border: 1px solid #555;"
            " border-radius: 5px; padding: 4px 14px;"
        )
        self._prev_btn.clicked.connect(self._prev)
        btn_row.addWidget(self._prev_btn)

        self._next_btn = QPushButton("Next →")
        self._next_btn.setMinimumHeight(32)
        self._next_btn.setMinimumWidth(90)
        self._next_btn.setStyleSheet(
            "background: #9c6fe8; color: #fff; border: none;"
            " border-radius: 5px; font-weight: bold; padding: 4px 14px;"
        )
        self._next_btn.clicked.connect(self._next)
        btn_row.addWidget(self._next_btn)

        v.addLayout(btn_row)

    def _advance_to(self, idx: int):
        self._idx = idx
        step = self._steps[idx]

        if step.tab_index >= 0:
            self._mw._navigate(step.tab_index)
            QApplication.processEvents()

        if step.on_enter:
            step.on_enter()
            QApplication.processEvents()

        if step.highlight_fn:
            items = step.highlight_fn()
            rects = []
            for item in (items or []):
                if item is None:
                    continue
                if isinstance(item, QRect):
                    rects.append(item)
                elif isinstance(item, QWidget) and item.isVisible():
                    tl = item.mapTo(self._mw, QPoint(0, 0))
                    rects.append(QRect(tl, item.size()))
            self._highlight_rects = rects
        else:
            self._highlight_rects = []

        total = len(self._steps)
        self._step_lbl.setText(f"Step {idx + 1} of {total}")
        self._title_lbl.setText(step.title)
        self._body_lbl.setText(step.body)
        self._prev_btn.setVisible(idx > 0)
        is_last = idx == total - 1
        self._next_btn.setText("  Finish  " if is_last else "Next →")
        self._skip_btn.setVisible(not is_last)

        self.update()
        self._position_card()
        self._card.raise_()

    def _position_card(self):
        mw = self._mw.rect()
        w = min(self._CARD_W, mw.width() - self._CARD_MARGIN * 2)
        self._card.setFixedWidth(w)
        self._card.adjustSize()
        h = max(self._card.sizeHint().height(), 170)
        self._card.setFixedHeight(h)

        x = (mw.width() - w) // 2
        y_bottom = mw.height() - h - self._CARD_MARGIN

        if self._highlight_rects:
            avg_hl_y = sum(r.center().y() for r in self._highlight_rects) / len(self._highlight_rects)
            if avg_hl_y > mw.height() * 0.55:
                y = self._CARD_MARGIN
            else:
                y = y_bottom
        else:
            y = y_bottom

        self._card.setGeometry(x, y, w, h)

    def _next(self):
        if self._idx >= len(self._steps) - 1:
            self._finish()
        else:
            self._advance_to(self._idx + 1)

    def _prev(self):
        if self._idx > 0:
            self._advance_to(self._idx - 1)

    def _finish(self):
        c = cfg.load_config()
        c["onboarding_complete"] = True
        try:
            cfg.save_config(c)
        except Exception:
            pass
        if self._on_finish:
            self._on_finish()
        self._mw.removeEventFilter(self)
        self.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._highlight_rects:
            # Build overlay path with holes for each highlighted widget
            overlay = QPainterPath()
            overlay.addRect(QRectF(self.rect()))
            for r in self._highlight_rects:
                padded = r.adjusted(-self._PAD, -self._PAD, self._PAD, self._PAD)
                hole = QPainterPath()
                hole.addRoundedRect(QRectF(padded), 6, 6)
                overlay = overlay.subtracted(hole)
            painter.fillPath(overlay, QColor(0, 0, 0, 165))

            # Draw accent border around each highlight
            pen = QPen(QColor("#9c6fe8"), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            for r in self._highlight_rects:
                padded = r.adjusted(-self._PAD, -self._PAD, self._PAD, self._PAD)
                painter.drawRoundedRect(QRectF(padded), 6, 6)
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 165))

    def mousePressEvent(self, event):
        # Swallow clicks so they don't fall through to the app
        event.accept()
