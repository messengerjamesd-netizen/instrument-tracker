import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSizePolicy, QFrame, QDialogButtonBox, QPlainTextEdit,
    QFileDialog, QCompleter,
)
import database as db
from ui.camera_dialog import PhotoCaptureDialog


class CheckoutDialog(QDialog):
    """
    All-in-one checkout: pick student, optionally photograph instrument
    condition and/or the paper contract before confirming.
    """

    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.selected_student_id = None
        self.condition_photo_path = ""
        self.contract_photo_path = ""
        self.notes = ""

        name = instrument["name"]
        serial = instrument["serial_number"] or "no serial"
        self.setWindowTitle(f"Check Out — {name}")
        self.setMinimumWidth(480)

        self._build_ui(name, serial)

    def _build_ui(self, name, serial):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Instrument header
        hdr = QLabel(f"<b>{name}</b>  <span style='color:#5a7aaa'>({serial})</span>")
        hdr.setStyleSheet("font-size: 15px;")
        layout.addWidget(hdr)

        layout.addWidget(self._separator())

        # Student selector
        s_row = QHBoxLayout()
        s_lbl = QLabel("Assign to student:")
        s_lbl.setMinimumWidth(130)
        self.student_combo = QComboBox()
        self.student_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.student_combo.setEditable(True)
        self.student_combo.setInsertPolicy(QComboBox.NoInsert)
        self.student_combo.lineEdit().setPlaceholderText("Type to search students…")
        students = db.get_all_students()
        for s in students:
            self.student_combo.addItem(f"{s['name']} ({s['student_id']})", s["id"])
        completer = QCompleter([f"{s['name']} ({s['student_id']})" for s in students])
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.student_combo.setCompleter(completer)
        s_row.addWidget(s_lbl)
        s_row.addWidget(self.student_combo)
        layout.addLayout(s_row)

        layout.addWidget(self._separator())

        # Photos
        layout.addWidget(QLabel("Optional photos:"))

        # Condition photo row
        cond_row = QHBoxLayout()
        self.cond_thumb = self._make_thumb()
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

        # Contract row — camera + upload stacked, shared thumb + clear
        cont_row = QHBoxLayout()
        self.cont_thumb = self._make_thumb()
        cont_btns = QVBoxLayout()
        cont_btns.setSpacing(4)
        cont_cam_btn = QPushButton("📄  Photograph Paper Contract")
        cont_cam_btn.setMinimumHeight(34)
        cont_cam_btn.clicked.connect(self._take_contract_photo)
        cont_upload_btn = QPushButton("📁  Upload Contract File")
        cont_upload_btn.setMinimumHeight(34)
        cont_upload_btn.clicked.connect(self._upload_contract_file)
        cont_btns.addWidget(cont_cam_btn)
        cont_btns.addWidget(cont_upload_btn)
        cont_clear = QPushButton("Clear")
        cont_clear.clicked.connect(self._clear_contract_photo)
        cont_row.addWidget(self.cont_thumb)
        cont_row.addLayout(cont_btns)
        cont_row.addWidget(cont_clear)
        layout.addLayout(cont_row)

        layout.addWidget(self._separator())

        # Condition notes
        layout.addWidget(QLabel("Condition notes:"))
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes about instrument condition…")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        layout.addWidget(self._separator())

        # Confirm / Cancel
        btns = QDialogButtonBox()
        self.confirm_btn = btns.addButton("Complete Checkout", QDialogButtonBox.AcceptRole)
        self.confirm_btn.setObjectName("primary")
        btns.addButton("Cancel", QDialogButtonBox.RejectRole)
        btns.accepted.connect(self._confirm)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def _make_thumb(self):
        lbl = QLabel()
        lbl.setFixedSize(80, 60)
        lbl.setStyleSheet(
            "background:#0f2040; border:1px solid #1a3666; border-radius:4px;"
        )
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setText("—")
        return lbl

    def _take_condition_photo(self):
        dlg = PhotoCaptureDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.captured_path:
            self.condition_photo_path = dlg.captured_path
            self._set_thumb(self.cond_thumb, dlg.captured_path)

    def _clear_condition_photo(self):
        self.condition_photo_path = ""
        self.cond_thumb.setPixmap(QPixmap())
        self.cond_thumb.setText("—")

    def _take_contract_photo(self):
        dlg = PhotoCaptureDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.captured_path:
            self.contract_photo_path = dlg.captured_path
            self._set_thumb(self.cont_thumb, dlg.captured_path)

    def _upload_contract_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Contract File", "",
            "Images & PDFs (*.png *.jpg *.jpeg *.bmp *.tiff *.pdf);;All Files (*)"
        )
        if not path:
            return
        self.contract_photo_path = path
        if path.lower().endswith(".pdf"):
            self.cont_thumb.setPixmap(QPixmap())
            self.cont_thumb.setText("PDF")
        else:
            self._set_thumb(self.cont_thumb, path)

    def _clear_contract_photo(self):
        self.contract_photo_path = ""
        self.cont_thumb.setPixmap(QPixmap())
        self.cont_thumb.setText("—")

    def _set_thumb(self, label, path):
        pix = QPixmap(path).scaled(
            label.width(), label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(pix)
        label.setText("")

    def _confirm(self):
        self.selected_student_id = self.student_combo.currentData()
        self.notes = self.notes_edit.toPlainText().strip()
        self.accept()
