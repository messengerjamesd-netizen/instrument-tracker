from datetime import datetime

from PySide6.QtCore import Qt, Signal, QRect, QPropertyAnimation, QEasingCurve, Property, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QPainterPath, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QMessageBox, QSizePolicy, QFrame, QDialogButtonBox,
    QPlainTextEdit, QLineEdit, QButtonGroup, QScrollArea, QRadioButton,
)
import database as db
from ui.camera_dialog import CameraDialog, PhotoCaptureDialog
from ui.checkout_dialog import CheckoutDialog


ACTION_LABELS = {
    "check_out":       "Checked Out",
    "check_in":        "Checked In",
    "needs_repair":    "Needs Repair",
    "out_for_repair":  "Out for Repair",
    "repair_returned": "Returned from Repair",
    "summer_hold":     "Summer Hold",
}


def _relative_time(timestamp_str):
    try:
        try:
            ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
        secs = int((datetime.now() - ts).total_seconds())
        if secs < 60:
            return "just now"
        if secs < 3600:
            m = secs // 60
            return f"{m} min ago"
        if secs < 86400:
            h = secs // 3600
            return f"{h} hr ago"
        d = secs // 86400
        return f"{d} day{'s' if d != 1 else ''} ago"
    except Exception:
        return timestamp_str


class _PillToggle(QWidget):
    """Animated pill-style toggle between two options."""
    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self._labels = labels
        self._selected = 0
        self.setFixedHeight(54)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"pill_x", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pill_x = 0.0

    def selected(self):
        return self._selected

    def get_pill_x(self): return getattr(self, '_pill_x', 0.0)
    def set_pill_x(self, v):
        self._pill_x = v
        self.update()
    pill_x = Property(float, get_pill_x, set_pill_x)

    def mousePressEvent(self, e):
        idx = 0 if e.position().x() < self.width() / 2 else 1
        if idx != self._selected:
            self._selected = idx
            self._anim.setStartValue(self._pill_x)
            self._anim.setEndValue((self.width() / 2) * idx)
            self._anim.start()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        track = QPainterPath()
        track.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 10, 10)
        p.fillPath(track, QColor("#0f2040"))
        p.setPen(QPen(QColor("#1a3666"), 1))
        p.drawPath(track)

        pw = r.width() / 2 - 4
        pill = QPainterPath()
        pill.addRoundedRect(self._pill_x + 2, 3, pw, r.height() - 6, 8, 8)
        p.fillPath(pill, QColor("#1a4a8a"))
        p.setPen(Qt.NoPen)

        half = r.width() // 2
        for i, lbl in enumerate(self._labels):
            p.setPen(QColor("#ffffff" if i == self._selected else "#8aaad0"))
            p.setFont(self.font())
            p.drawText(QRect(i * half, 0, half, r.height()), Qt.AlignCenter, lbl)

        p.end()


class _CardButton(QFrame):
    """Clickable card widget used for the main action buttons."""
    clicked = Signal()

    def __init__(self, icon, title, desc, primary=False, parent=None):
        super().__init__(parent)
        self._primary = primary
        self.setCursor(Qt.PointingHandCursor)
        self._apply_normal_style()

        title_color = "#7eb8f7" if primary else "#ffffff"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 26, 24, 26)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 34px; background: transparent; border: none;")
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(f"font-weight: bold; color: {title_color}; background: transparent; border: none;")
        desc_lbl = QLabel(desc)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setStyleSheet("color: #5a7aaa; background: transparent; border: none;")
        desc_lbl.setWordWrap(True)

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)

    def _apply_normal_style(self):
        p = self._primary
        bg     = "#102a5a" if p else "#0f2040"
        border = "#2d6bc4" if p else "#1a3666"
        self.setStyleSheet(f"""
            _CardButton {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            _CardButton:hover {{
                background: {"#1a3a70" if p else "#162840"};
                border-color: {"#4a8ae4" if p else "#2d6bc4"};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ScannerInputDialog(QDialog):
    """Waits for an external QR/barcode scanner to type a code and press Enter."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        self.scanned_value = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        layout.addWidget(QLabel("Scan the QR code with your external scanner,\n"
                                "or type the code manually and press Enter:"))

        self.input = QLineEdit()
        self.input.setPlaceholderText("Waiting for scan…")
        self.input.setMinimumHeight(36)
        self.input.returnPressed.connect(self._on_enter)
        layout.addWidget(self.input)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_enter)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.input.setFocus()

    def _on_enter(self):
        value = self.input.text().strip()
        if value:
            self.scanned_value = value
            self.accept()


class CheckinDialog(QDialog):
    """Confirm check-in with optional condition photo and notes."""

    def __init__(self, instrument, parent=None, active_checkouts=None):
        super().__init__(parent)
        self.instrument = instrument
        self.condition_photo_path = ""
        self.notes = ""
        self.student_db_id = None  # None = full check-in; set to specific ID for partial
        self._active_checkouts = active_checkouts or []

        name = instrument["name"]
        serial = instrument["serial_number"] or "no serial"
        self.setWindowTitle(f"Check In — {name}")
        self.setMinimumWidth(460)
        self._build_ui(name, serial)

    def _build_ui(self, name, serial):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        hdr = QLabel(f"<b>{name}</b>  <span style='color:#5a7aaa'>({serial})</span>")
        hdr.setStyleSheet("font-size: 15px;")
        layout.addWidget(hdr)

        self._student_picker_group = None
        if len(self._active_checkouts) > 1:
            layout.addWidget(QLabel("Who is returning this instrument?"))
            self._student_picker_group = QButtonGroup(self)
            for i, co in enumerate(self._active_checkouts):
                rb = QRadioButton(co["student_name"])
                rb.setProperty("student_db_id", co["student_id"])
                if i == 0:
                    rb.setChecked(True)
                self._student_picker_group.addButton(rb, i)
                layout.addWidget(rb)
            rb_all = QRadioButton("All students — fully return instrument (mark Available)")
            rb_all.setProperty("student_db_id", None)
            self._student_picker_group.addButton(rb_all, len(self._active_checkouts))
            layout.addWidget(rb_all)
        else:
            try:
                student_name = self.instrument["student_name"]
            except (IndexError, KeyError):
                student_name = None
            if not student_name and self._active_checkouts:
                student_name = self._active_checkouts[0]["student_name"]
            if student_name:
                layout.addWidget(QLabel(f"Currently checked out to: <b>{student_name}</b>"))

        layout.addWidget(self._separator())

        # Condition photo
        layout.addWidget(QLabel("Optional photo:"))
        cond_row = QHBoxLayout()
        self.cond_thumb = QLabel()
        self.cond_thumb.setFixedSize(80, 60)
        self.cond_thumb.setStyleSheet(
            "background:#0f2040; border:1px solid #1a3666; border-radius:4px;"
        )
        self.cond_thumb.setAlignment(Qt.AlignCenter)
        self.cond_thumb.setText("—")
        cond_btn = QPushButton("📷  Photograph Instrument Condition")
        cond_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cond_btn.setMinimumHeight(36)
        cond_btn.clicked.connect(self._take_condition_photo)
        cond_clear = QPushButton("Clear")
        cond_clear.clicked.connect(self._clear_condition_photo)
        cond_row.addWidget(self.cond_thumb)
        cond_row.addWidget(cond_btn)
        cond_row.addWidget(cond_clear)
        layout.addLayout(cond_row)

        layout.addWidget(self._separator())

        # Condition notes
        layout.addWidget(QLabel("Condition notes:"))
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes about instrument condition…")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        layout.addWidget(self._separator())

        btns = QDialogButtonBox()
        confirm = btns.addButton("Complete Check In", QDialogButtonBox.AcceptRole)
        confirm.setObjectName("primary")
        btns.addButton("Cancel", QDialogButtonBox.RejectRole)
        btns.accepted.connect(self._confirm)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def _take_condition_photo(self):
        dlg = PhotoCaptureDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.captured_path:
            self.condition_photo_path = dlg.captured_path
            pix = QPixmap(dlg.captured_path).scaled(
                self.cond_thumb.width(), self.cond_thumb.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.cond_thumb.setPixmap(pix)
            self.cond_thumb.setText("")

    def _clear_condition_photo(self):
        self.condition_photo_path = ""
        self.cond_thumb.setPixmap(QPixmap())
        self.cond_thumb.setText("—")

    def _confirm(self):
        self.notes = self.notes_edit.toPlainText().strip()
        if self._student_picker_group:
            checked = self._student_picker_group.checkedButton()
            self.student_db_id = checked.property("student_db_id") if checked else None
        self.accept()


class _ResponsiveCards(QWidget):
    """Lays out two cards side-by-side above 500px, stacked below."""
    def __init__(self, card1, card2, parent=None):
        super().__init__(parent)
        self._card1 = card1
        self._card2 = card2
        card1.setParent(self)
        card2.setParent(self)
        self._horizontal = True

    def sizeHint(self):
        from PySide6.QtCore import QSize
        ch = max(self._card1.sizeHint().height(), self._card2.sizeHint().height())
        return QSize(400, ch)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        gap = 16
        if w >= 500:
            half = (w - gap) // 2
            h = max(self._card1.sizeHint().height(), self._card2.sizeHint().height())
            self._card1.setGeometry(0, 0, half, h)
            self._card2.setGeometry(half + gap, 0, w - half - gap, h)
            self.setFixedHeight(h)
        else:
            h = self._card1.sizeHint().height()
            self._card1.setGeometry(0, 0, w, h)
            self._card2.setGeometry(0, h + gap, w, h)
            self.setFixedHeight(h * 2 + gap)


class _ClickableFrame(QFrame):
    clicked = Signal(int)

    def __init__(self, instrument_id, parent=None):
        super().__init__(parent)
        self._instrument_id = instrument_id
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._instrument_id)
        super().mousePressEvent(event)


class ActionsTab(QWidget):
    navigate_to_instrument = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._activity_items = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Fixed top section (toggle + cards) ───────────────────────────────
        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(40, 40, 40, 20)
        top_layout.setSpacing(16)

        title = QLabel("Instrument Actions")
        title.setObjectName("section_title")
        top_layout.addWidget(title)

        self._mode_toggle = _PillToggle(["📷  Camera", "⌨️  Manual / Scanner"])
        top_layout.addWidget(self._mode_toggle)

        # Responsive card row — switches to vertical below 500px wide
        self._co_card = _CardButton("📤", "Check Out", "Assign an instrument to a student.", primary=True)
        self._co_card.clicked.connect(self._checkout)
        self._ci_card = _CardButton("📥", "Check In", "Return an instrument to inventory.")
        self._ci_card.clicked.connect(self._checkin)

        cards = _ResponsiveCards(self._co_card, self._ci_card)
        top_layout.addWidget(cards)
        top_layout.addSpacing(12)

        # Recent activity header
        divider_row = QHBoxLayout()
        divider_row.setSpacing(10)
        act_label = QLabel("RECENT ACTIVITY")
        act_label.setStyleSheet(
            "font-weight: bold; color: #8aaad0; letter-spacing: 1px;"
        )
        divider_row.addWidget(act_label)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #1a3666;")
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        divider_row.addWidget(line)
        top_layout.addLayout(divider_row)

        outer.addWidget(top)

        # ── Scrollable activity list ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        activity_container = QWidget()
        scroll.setWidget(activity_container)

        activity_page = QVBoxLayout(activity_container)
        activity_page.setContentsMargins(40, 8, 40, 40)
        activity_page.setSpacing(0)

        self._activity_layout = QVBoxLayout()
        self._activity_layout.setSpacing(6)
        activity_page.addLayout(self._activity_layout)
        activity_page.addStretch()

        self._refresh_activity()

    def refresh(self):
        self._refresh_activity()

    def _refresh_activity(self):
        # Clear old items
        while self._activity_layout.count():
            item = self._activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = db.get_recent_activity(20)
        if not rows:
            empty = QLabel("No activity yet.")
            empty.setStyleSheet("color: #3a5a8a; padding: 10px 0;")
            self._activity_layout.addWidget(empty)
            return

        for row in rows:
            action  = row["action"]
            instr   = row["instrument_name"] or "Unknown Instrument"
            serial  = row["serial_number"] or ""
            student = row["student_name"] or ""
            ts      = _relative_time(row["timestamp"])
            label   = ACTION_LABELS.get(action, action)
            is_out  = action == "check_out"

            item_frame = _ClickableFrame(row["instrument_id"])
            item_frame.clicked.connect(self.navigate_to_instrument)
            item_frame.setStyleSheet(
                "_ClickableFrame { background: #0d1e3a; border: 1px solid #1a3666; border-radius: 6px; }"
                "_ClickableFrame:hover { border-color: #2d6bc4; }"
            )
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(14, 10, 14, 10)
            item_layout.setSpacing(10)

            # Left: instrument name + detail
            left = QVBoxLayout()
            left.setSpacing(2)
            name_lbl = QLabel(f"{instr}{(' (S/N: ' + serial + ')') if serial else ''}")
            name_lbl.setStyleSheet(
                "font-weight: 600; color: #c8d8f0; background: transparent; border: none;"
            )
            left.addWidget(name_lbl)

            if student:
                detail_text = f"{'Checked out to' if is_out else label + ' —'} {student}"
            else:
                detail_text = label
            detail_lbl = QLabel(detail_text)
            detail_lbl.setStyleSheet(
                "color: #5a7aaa; background: transparent; border: none;"
            )
            left.addWidget(detail_lbl)
            item_layout.addLayout(left, 1)

            # Right: badge + time
            right = QVBoxLayout()
            right.setSpacing(4)
            right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            _BADGE = {
                "check_out":       ("Out", "#262000", "#c8b830", "#403800"),
                "check_in":        ("In",  "#0a1f0a", "#5caa5c", "#1a401a"),
                "needs_repair":    ("NR",  "#200a0a", "#cc4444", "#3a1212"),
                "out_for_repair":  ("Rep", "#200a0a", "#cc4444", "#3a1212"),
                "repair_returned": ("Ret", "#0a1f0a", "#5caa5c", "#1a401a"),
                "summer_hold":     ("SH",  "#1a2a4a", "#7eb8f7", "#1a3666"),
            }
            b_text, b_bg, b_fg, b_border = _BADGE.get(
                action, ("In", "#0a1f0a", "#5caa5c", "#1a401a")
            )
            badge = QLabel(b_text)
            badge.setStyleSheet(
                f"font-weight: bold; padding: 2px 6px; border-radius: 4px; "
                f"background: {b_bg}; color: {b_fg}; border: 1px solid {b_border};"
            )
            badge.setAlignment(Qt.AlignCenter)
            right.addWidget(badge)

            time_lbl = QLabel(ts)
            time_lbl.setStyleSheet(
                "color: #3a5a8a; background: transparent; border: none;"
            )
            time_lbl.setAlignment(Qt.AlignRight)
            right.addWidget(time_lbl)
            item_layout.addLayout(right)

            self._activity_layout.addWidget(item_frame)

    def _confirm_instrument(self, instrument, action):
        """Show instrument details after scan and ask user to confirm before proceeding."""
        name = instrument["name"]
        serial = instrument["serial_number"] or "no serial"
        status = instrument["status"]
        student = instrument["student_name"] or "—"
        msg = (
            f"<b>{name}</b> ({serial})<br><br>"
            f"Status: <b>{status}</b><br>"
            f"Checked out to: <b>{student}</b><br><br>"
            f"Continue with <b>{action}</b>?"
        )
        box = QMessageBox(self)
        box.setWindowTitle("Instrument Found")
        box.setTextFormat(Qt.RichText)
        box.setText(msg)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Yes)
        return box.exec() == QMessageBox.Yes

    def _get_qr_code(self, title):
        if self._mode_toggle.selected() == 1:
            dlg = ScannerInputDialog(title, self)
        else:
            dlg = CameraDialog(self, title)
        if dlg.exec() != QDialog.Accepted:
            return None
        return dlg.scanned_value

    # ── Checkout ──────────────────────────────────────────────────────────────

    def _checkout(self):
        qr = self._get_qr_code("Scan QR — Check Out")
        if not qr:
            return
        instrument = db.get_instrument_by_qr(qr)
        if not instrument:
            QMessageBox.warning(self, "Not Found",
                                f"No instrument found with QR code:\n{qr}")
            return

        if not self._confirm_instrument(instrument, "Check Out"):
            return

        is_additional = False
        if instrument["status"] == "Checked Out":
            active = db.get_instrument_active_checkouts(instrument["id"])
            current_names = ", ".join(c["student_name"] for c in active) or "Unknown"
            reply = QMessageBox.question(
                self, "Already Checked Out",
                f"{instrument['name']} is currently checked out to {current_names}.\n\n"
                "Add another student to this checkout?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            is_additional = True

        if not db.get_all_students():
            QMessageBox.warning(self, "No Students",
                                "No students in the system. Add students first.")
            return

        co_dlg = CheckoutDialog(instrument, self)
        if co_dlg.exec() != QDialog.Accepted or not co_dlg.selected_student_id:
            return

        if is_additional:
            db.checkout_instrument_additional(
                instrument["id"],
                co_dlg.selected_student_id,
                notes=co_dlg.notes,
                condition_photo_path=co_dlg.condition_photo_path,
                contract_photo_path=co_dlg.contract_photo_path,
            )
        else:
            db.checkout_instrument(
                instrument["id"],
                co_dlg.selected_student_id,
                notes=co_dlg.notes,
                condition_photo_path=co_dlg.condition_photo_path,
                contract_photo_path=co_dlg.contract_photo_path,
            )

        if co_dlg.contract_photo_path:
            db.add_contract(
                co_dlg.selected_student_id,
                instrument["id"],
                co_dlg.contract_photo_path,
                notes=co_dlg.notes or "Created automatically from checkout.",
            )

        student = db.get_student_by_id(co_dlg.selected_student_id)
        QMessageBox.information(
            self, "Checked Out",
            f"{instrument['name']} checked out to {student['name']}.",
        )
        self._refresh_activity()

    # ── Checkin ───────────────────────────────────────────────────────────────

    def _checkin(self):
        qr = self._get_qr_code("Scan QR — Check In")
        if not qr:
            return
        instrument = db.get_instrument_by_qr(qr)
        if not instrument:
            QMessageBox.warning(self, "Not Found",
                                f"No instrument found with QR code:\n{qr}")
            return

        instr_label = f"{instrument['name']} ({instrument['serial_number'] or 'no serial'})"

        if not self._confirm_instrument(instrument, "Check In"):
            return

        if instrument["status"] != "Checked Out":
            status = instrument["status"]
            if status == "Available":
                QMessageBox.information(self, "Already Available",
                                        f"{instr_label} is already marked as Available.")
            else:
                QMessageBox.warning(self, "Cannot Check In",
                                    f"{instr_label} is currently marked as: {status}\n\n"
                                    "Use Change Status on the Instruments page to update it.")
            return

        active_checkouts = db.get_instrument_active_checkouts(instrument["id"])
        ci_dlg = CheckinDialog(instrument, self, active_checkouts=active_checkouts)
        if ci_dlg.exec() != QDialog.Accepted:
            return

        db.checkin_instrument(
            instrument["id"],
            notes=ci_dlg.notes,
            condition_photo_path=ci_dlg.condition_photo_path,
            student_db_id=ci_dlg.student_db_id,
        )
        if ci_dlg.student_db_id and len(active_checkouts) > 1:
            QMessageBox.information(self, "Checked In",
                                    f"{instr_label} — student removed, still checked out to remaining student(s).")
        else:
            QMessageBox.information(self, "Checked In", f"{instr_label} is now Available.")
        self._refresh_activity()
