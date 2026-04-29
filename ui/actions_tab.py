from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QMessageBox, QSizePolicy, QFrame, QDialogButtonBox,
    QPlainTextEdit, QLineEdit, QCheckBox,
)
import database as db
from ui.camera_dialog import CameraDialog, PhotoCaptureDialog
from ui.checkout_dialog import CheckoutDialog


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
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        title = QLabel("Instrument Actions")
        title.setObjectName("section_title")
        outer.addWidget(title)

        self.scanner_toggle = QCheckBox("Use external QR scanner or manual entry")
        self.scanner_toggle.setStyleSheet("""
            QCheckBox { font-size: 14px; color: #c8d8f0; spacing: 10px; }
            QCheckBox::indicator { width: 20px; height: 20px; }
        """)
        outer.addWidget(self.scanner_toggle)

        checkout_btn = QPushButton("  Scan QR — Check Out Instrument")
        checkout_btn.setObjectName("primary")
        checkout_btn.setMinimumHeight(52)
        checkout_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        checkout_btn.setStyleSheet(
            "font-size: 15px; font-weight: bold; text-align: left; padding-left: 20px;"
        )
        checkout_btn.clicked.connect(self._checkout)
        outer.addWidget(checkout_btn)

        checkin_btn = QPushButton("  Scan QR — Check In Instrument")
        checkin_btn.setMinimumHeight(52)
        checkin_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        checkin_btn.setStyleSheet(
            "font-size: 15px; font-weight: bold; text-align: left; padding-left: 20px;"
        )
        checkin_btn.clicked.connect(self._checkin)
        outer.addWidget(checkin_btn)

        outer.addStretch()

    def _get_qr_code(self, title):
        """Open either the camera dialog or scanner input depending on the toggle."""
        if self.scanner_toggle.isChecked():
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

        if instrument["status"] != "Checked Out":
            QMessageBox.information(self, "Already Available",
                                    f"{instr_label} is already marked as Available.")
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
