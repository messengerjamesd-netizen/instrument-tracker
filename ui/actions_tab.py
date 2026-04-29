from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QMessageBox, QSizePolicy, QFrame, QDialogButtonBox,
    QPlainTextEdit, QLineEdit, QButtonGroup, QScrollArea,
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
}


def _relative_time(timestamp_str):
    try:
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


class _CardButton(QFrame):
    """Clickable card widget used for the main action buttons."""
    clicked = Signal()

    def __init__(self, icon, title, desc, primary=False, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        bg     = "#102a5a" if primary else "#0f2040"
        border = "#2d6bc4" if primary else "#1a3666"
        title_color = "#7eb8f7" if primary else "#ffffff"
        self.setStyleSheet(f"""
            _CardButton {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            _CardButton:hover {{
                background: {"#1a3a70" if primary else "#162840"};
                border-color: {"#4a8ae4" if primary else "#2d6bc4"};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 26px; background: transparent; border: none;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {title_color}; background: transparent; border: none;")
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size: 12px; color: #5a7aaa; background: transparent; border: none;")
        desc_lbl.setWordWrap(True)

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)

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

    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.condition_photo_path = ""
        self.notes = ""

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

        try:
            student_name = self.instrument["student_name"]
        except (IndexError, KeyError):
            student_name = None
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
        self.accept()


class ActionsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._activity_items = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scroll area so content works at any window size
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        # Centering: stretch | fixed-width inner | stretch
        page = QVBoxLayout(container)
        page.setContentsMargins(40, 40, 40, 40)
        page.setSpacing(0)
        page.addStretch()

        inner = QWidget()
        inner.setMaximumWidth(560)
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(16)

        # Title
        title = QLabel("Instrument Actions")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e8f0ff;")
        inner_layout.addWidget(title)

        # Scan mode toggle
        mode_label = QLabel("How are you scanning?")
        mode_label.setStyleSheet("font-size: 13px; color: #8aaad0;")
        inner_layout.addWidget(mode_label)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(0)

        self._btn_camera  = QPushButton("📷  Camera")
        self._btn_scanner = QPushButton("⌨️  Type Manually / External Scanner")

        for btn in (self._btn_camera, self._btn_scanner):
            btn.setCheckable(True)
            btn.setMinimumHeight(44)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 14px; font-weight: bold;
                    background: #0f2040; color: #8aaad0;
                    border: 1px solid #1a3666;
                }
                QPushButton:checked {
                    background: #1a4a8a; color: #ffffff;
                    border: 1px solid #2d6bc4;
                }
                QPushButton:first-child { border-radius: 6px 0 0 6px; }
                QPushButton:last-child  { border-radius: 0 6px 6px 0; }
            """)
            toggle_row.addWidget(btn)

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._btn_camera, 0)
        self._mode_group.addButton(self._btn_scanner, 1)
        self._btn_camera.setChecked(True)
        inner_layout.addLayout(toggle_row)

        # Card buttons (Check Out / Check In)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        co_card = _CardButton("📤", "Check Out", "Assign an instrument to a student.", primary=True)
        co_card.clicked.connect(self._checkout)
        ci_card = _CardButton("📥", "Check In", "Return an instrument to inventory.")
        ci_card.clicked.connect(self._checkin)

        cards_row.addWidget(co_card)
        cards_row.addWidget(ci_card)
        inner_layout.addLayout(cards_row)

        # Recent activity section header
        divider_row = QHBoxLayout()
        divider_row.setSpacing(10)
        act_label = QLabel("RECENT ACTIVITY")
        act_label.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #8aaad0; letter-spacing: 1px;"
        )
        divider_row.addWidget(act_label)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #1a3666;")
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        divider_row.addWidget(line)
        inner_layout.addLayout(divider_row)

        # Activity list placeholder — populated by _refresh_activity
        self._activity_layout = QVBoxLayout()
        self._activity_layout.setSpacing(6)
        inner_layout.addLayout(self._activity_layout)

        # Center the inner widget horizontally
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch()
        h.addWidget(inner)
        h.addStretch()
        page.addLayout(h)
        page.addStretch()

        self._refresh_activity()

    def _refresh_activity(self):
        # Clear old items
        while self._activity_layout.count():
            item = self._activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = db.get_recent_activity(5)
        if not rows:
            empty = QLabel("No activity yet.")
            empty.setStyleSheet("font-size: 13px; color: #3a5a8a; padding: 10px 0;")
            self._activity_layout.addWidget(empty)
            return

        for row in rows:
            action  = row["action"]
            instr   = row["instrument_name"] or "Unknown Instrument"
            serial  = row["serial_number"] or ""
            student = row["student_name"] or ""
            ts      = _relative_time(row["timestamp"])
            label   = ACTION_LABELS.get(action, action)
            is_out  = action in ("check_out",)

            item_frame = QFrame()
            item_frame.setStyleSheet(
                "QFrame { background: #0d1e3a; border: 1px solid #1a3666; border-radius: 6px; }"
            )
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(14, 10, 14, 10)
            item_layout.setSpacing(10)

            # Left: instrument name + detail
            left = QVBoxLayout()
            left.setSpacing(2)
            name_lbl = QLabel(f"{instr}{(' (S/N: ' + serial + ')') if serial else ''}")
            name_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #c8d8f0; background: transparent; border: none;"
            )
            left.addWidget(name_lbl)

            if student:
                detail_text = f"{'Checked out to' if is_out else label + ' —'} {student}"
            else:
                detail_text = label
            detail_lbl = QLabel(detail_text)
            detail_lbl.setStyleSheet(
                "font-size: 12px; color: #5a7aaa; background: transparent; border: none;"
            )
            left.addWidget(detail_lbl)
            item_layout.addLayout(left, 1)

            # Right: badge + time
            right = QVBoxLayout()
            right.setSpacing(4)
            right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            badge_text  = "Out" if is_out else "In"
            badge_style = (
                "font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 4px; "
                + ("background: #1a3a1a; color: #6abf6a; border: 1px solid #2a5a2a;"
                   if is_out else
                   "background: #1a2a4a; color: #7eb8f7; border: 1px solid #1a3666;")
            )
            badge = QLabel(badge_text)
            badge.setStyleSheet(badge_style)
            badge.setAlignment(Qt.AlignCenter)
            right.addWidget(badge)

            time_lbl = QLabel(ts)
            time_lbl.setStyleSheet(
                "font-size: 11px; color: #3a5a8a; background: transparent; border: none;"
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
        if self._mode_group.checkedId() == 1:
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

        if instrument["status"] == "Checked Out":
            student_name = instrument["student_name"] or "Unknown"
            reply = QMessageBox.question(
                self, "Already Checked Out",
                f"{instrument['name']} is currently checked out to {student_name}.\n\n"
                "Check it out to a different student anyway?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        if not db.get_all_students():
            QMessageBox.warning(self, "No Students",
                                "No students in the system. Add students first.")
            return

        co_dlg = CheckoutDialog(instrument, self)
        if co_dlg.exec() != QDialog.Accepted or not co_dlg.selected_student_id:
            return

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

        ci_dlg = CheckinDialog(instrument, self)
        if ci_dlg.exec() != QDialog.Accepted:
            return

        db.checkin_instrument(
            instrument["id"],
            notes=ci_dlg.notes,
            condition_photo_path=ci_dlg.condition_photo_path,
        )
        QMessageBox.information(self, "Checked In", f"{instr_label} is now Available.")
        self._refresh_activity()
