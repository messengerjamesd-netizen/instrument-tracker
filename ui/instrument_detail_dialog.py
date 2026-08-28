import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSizePolicy, QComboBox, QPlainTextEdit,
    QFileDialog, QFrame, QLineEdit, QDialogButtonBox,
)
import database as db


def _open_file(path):
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])


class PhotoPreviewDialog(QDialog):
    """Shows a full-size photo."""

    def __init__(self, path, title="Photo", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)
        self.resize(700, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.img_label.setObjectName("camera_preview")
        layout.addWidget(self.img_label)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open in Default Viewer")
        open_btn.clicked.connect(lambda: _open_file(path))
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(open_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._path = path
        self._load_image()

    def _load_image(self):
        pix = QPixmap(self._path)
        if pix.isNull():
            self.img_label.setText("Could not load image.")
            return
        self._pix_orig = pix
        self._update_scaled()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_pix_orig"):
            self._update_scaled()

    def _update_scaled(self):
        pix = self._pix_orig.scaled(
            self.img_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.img_label.setPixmap(pix)


class _AddContractToInstrumentDialog(QDialog):
    def __init__(self, instrument_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Contract")
        self.setFixedWidth(440)
        self._instrument_id = instrument_id
        self.student_id = None
        self.scan_path = ""
        self.notes = ""
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        instr = db.get_instrument_by_id(self._instrument_id)
        current_student_id = instr["current_student_id"] if instr else None

        self._student_combo = QComboBox()
        self._student_combo.addItem("-- Select Student --", None)
        for s in db.get_all_students():
            self._student_combo.addItem(f"{s['name']} ({s['student_id']})", s["id"])
            if s["id"] == current_student_id:
                self._student_combo.setCurrentIndex(self._student_combo.count() - 1)
        layout.addRow("Student *", self._student_combo)

        scan_w = QWidget()
        scan_row = QHBoxLayout(scan_w)
        scan_row.setContentsMargins(0, 0, 0, 0)
        scan_row.setSpacing(4)
        self._scan_edit = QLineEdit()
        self._scan_edit.setPlaceholderText("Optional scan/photo…")
        self._scan_edit.setReadOnly(True)
        file_btn = QPushButton("Browse File")
        file_btn.clicked.connect(self._select_file)
        photo_btn = QPushButton("Take Photo")
        photo_btn.clicked.connect(self._take_photo)
        clr_btn = QPushButton("Clear")
        clr_btn.clicked.connect(lambda: self._scan_edit.clear())
        scan_row.addWidget(self._scan_edit)
        scan_row.addWidget(file_btn)
        scan_row.addWidget(photo_btn)
        scan_row.addWidget(clr_btn)
        layout.addRow("Scan File", scan_w)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setPlaceholderText("Notes…")
        self._notes_edit.setFixedHeight(70)
        layout.addRow("Notes", self._notes_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Scan File", "",
            "Image/PDF Files (*.jpg *.jpeg *.png *.pdf);;All Files (*)"
        )
        if path:
            self._scan_edit.setText(path)

    def _take_photo(self):
        from ui.camera_dialog import PhotoCaptureDialog
        dlg = PhotoCaptureDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.captured_path:
            self._scan_edit.setText(dlg.captured_path)

    def _on_accept(self):
        if not self._student_combo.currentData():
            QMessageBox.warning(self, "Required", "Please select a student.")
            return
        self.student_id = self._student_combo.currentData()
        self.scan_path = self._scan_edit.text().strip()
        self.notes = self._notes_edit.toPlainText().strip()
        self.accept()


class InstrumentDetailDialog(QDialog):
    def __init__(self, instrument_id, parent=None):
        super().__init__(parent)
        self.instrument_id = instrument_id
        instr = db.get_instrument_by_id(instrument_id)
        name = instr["name"] if instr else "Instrument"
        serial = instr["serial_number"] if instr else ""
        self.setWindowTitle(f"{name} — Details")
        self.setMinimumSize(760, 520)
        self.resize(880, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel(f"<b>{name}</b>  <span style='color:#5a7aaa'>({serial})</span>")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(self._build_history_tab(), "History")
        tabs.addTab(self._build_contracts_tab(), "Contracts")
        layout.addWidget(tabs)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)
        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(close_btn)
        layout.addLayout(h)

    # ── History tab ───────────────────────────────────────────────────────────

    def _build_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        top_bar = QHBoxLayout()
        add_note_btn = QPushButton("+ Add Repair Note")
        add_note_btn.setObjectName("primary")
        add_note_btn.clicked.connect(self._add_repair_note)
        top_bar.addWidget(add_note_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["Action", "Student", "Timestamp", "Notes", "Photos"]
        )
        hdr = self.history_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(True)
        self.history_table.setColumnWidth(0, 130)
        self.history_table.setColumnWidth(1, 120)
        self.history_table.setColumnWidth(2, 140)
        self.history_table.setColumnWidth(3, 120)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setSortingEnabled(True)
        hdr.setSortIndicator(2, Qt.DescendingOrder)
        self.history_table.selectionModel().selectionChanged.connect(
            self._on_history_selection
        )
        layout.addWidget(self.history_table)

        # Photo buttons row
        btn_row = QHBoxLayout()
        self.view_cond_btn = QPushButton("View Condition Photo")
        self.view_cond_btn.setEnabled(False)
        self.view_cond_btn.clicked.connect(self._view_condition_photo)
        self.view_cont_btn = QPushButton("View Contract Photo")
        self.view_cont_btn.setEnabled(False)
        self.view_cont_btn.clicked.connect(self._view_contract_photo)
        self.view_inv_btn = QPushButton("View Repair Invoice")
        self.view_inv_btn.setEnabled(False)
        self.view_inv_btn.clicked.connect(self._view_repair_invoice)
        btn_row.addWidget(self.view_cond_btn)
        btn_row.addWidget(self.view_cont_btn)
        btn_row.addWidget(self.view_inv_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._load_history()
        return widget

    def _load_history(self):
        records = db.get_instrument_history(self.instrument_id)
        self.history_table.setSortingEnabled(False)
        self.history_table.setRowCount(len(records))
        action_map = {
            "check_out":       "Check Out",
            "check_in":        "Check In",
            "needs_repair":    "Needs Repair",
            "out_for_repair":  "Out for Repair",
            "repair_note":     "Repair Note",
            "repair_returned": "Returned from Repair",
            "summer_hold":     "Summer Hold",
        }
        for row, r in enumerate(records):
            action_label = action_map.get(r["action"], r["action"])

            cond = r["condition_photo_path"] or ""
            cont = r["contract_photo_path"] or ""
            inv  = r["repair_invoice_path"] or ""
            photo_flags = []
            if cond and os.path.exists(cond):
                photo_flags.append("Condition")
            if cont and os.path.exists(cont):
                photo_flags.append("Contract")
            if inv and os.path.exists(inv):
                photo_flags.append("Invoice")
            photo_label = ", ".join(photo_flags) if photo_flags else "—"

            vals = [
                action_label,
                r["student_name"] or "—",
                r["timestamp"],
                r["notes"] or "",
                photo_label,
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setData(Qt.UserRole, dict(r))
                self.history_table.setItem(row, col, item)
        self.history_table.setSortingEnabled(True)

    def _on_history_selection(self):
        row = self.history_table.currentRow()
        if row < 0:
            self.view_cond_btn.setEnabled(False)
            self.view_cont_btn.setEnabled(False)
            self.view_inv_btn.setEnabled(False)
            return
        data = self.history_table.item(row, 0).data(Qt.UserRole)
        cond = data.get("condition_photo_path") or ""
        cont = data.get("contract_photo_path") or ""
        inv  = data.get("repair_invoice_path") or ""
        self.view_cond_btn.setEnabled(bool(cond and os.path.exists(cond)))
        self.view_cont_btn.setEnabled(bool(cont and os.path.exists(cont)))
        self.view_inv_btn.setEnabled(bool(inv and os.path.exists(inv)))

    def _view_condition_photo(self):
        row = self.history_table.currentRow()
        if row < 0:
            return
        data = self.history_table.item(row, 0).data(Qt.UserRole)
        path = data.get("condition_photo_path") or ""
        if path and os.path.exists(path):
            dlg = PhotoPreviewDialog(path, "Condition Photo", self)
            dlg.exec()

    def _view_contract_photo(self):
        row = self.history_table.currentRow()
        if row < 0:
            return
        data = self.history_table.item(row, 0).data(Qt.UserRole)
        path = data.get("contract_photo_path") or ""
        if path and os.path.exists(path):
            dlg = PhotoPreviewDialog(path, "Contract Photo", self)
            dlg.exec()

    def _add_repair_note(self):
        from ui.instruments_page import RepairReturnDialog
        instr = db.get_instrument_by_id(self.instrument_id)
        if not instr:
            return
        dlg = RepairReturnDialog(instr, self, mode="note")
        if dlg.exec() != QDialog.Accepted:
            return
        db.add_repair_note(self.instrument_id, dlg.notes, dlg.invoice_path)
        self._load_history()

    def _view_repair_invoice(self):
        row = self.history_table.currentRow()
        if row < 0:
            return
        data = self.history_table.item(row, 0).data(Qt.UserRole)
        path = data.get("repair_invoice_path") or ""
        if path and os.path.exists(path):
            if path.lower().endswith(".pdf"):
                _open_file(path)
            else:
                dlg = PhotoPreviewDialog(path, "Repair Invoice", self)
                dlg.exec()

    # ── Contracts tab ─────────────────────────────────────────────────────────

    def _build_contracts_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        self.contracts_table = QTableWidget()
        self.contracts_table.setColumnCount(5)
        self.contracts_table.setHorizontalHeaderLabels(
            ["ID", "Student", "Date", "Notes", "Active"]
        )
        hdr = self.contracts_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.contracts_table.setAlternatingRowColors(True)
        self.contracts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.contracts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.contracts_table.verticalHeader().setVisible(False)
        self.contracts_table.setSortingEnabled(True)
        self.contracts_table.selectionModel().selectionChanged.connect(
            self._on_contracts_selection
        )
        layout.addWidget(self.contracts_table)

        self._contracts_sel_buttons = []

        def mk(text, slot, danger=False, primary=False):
            btn = QPushButton(text)
            btn.setMinimumHeight(32)
            if danger:
                btn.setObjectName("danger")
            if primary:
                btn.setObjectName("primary")
            btn.clicked.connect(slot)
            return btn

        add_btn = mk("+ Add Contract", self._add_contract_to_instrument, primary=True)

        self._c_delete_btn = mk("Delete", self._delete_contract_from_instrument, danger=True)
        self._c_delete_btn.setEnabled(False)
        self._contracts_sel_buttons.append(self._c_delete_btn)

        self._c_view_btn = mk("View Scan", self._view_scan)
        self._c_view_btn.setEnabled(False)
        self._contracts_sel_buttons.append(self._c_view_btn)

        self._c_toggle_btn = mk("Toggle Active", self._toggle_contract_active)
        self._c_toggle_btn.setEnabled(False)
        self._contracts_sel_buttons.append(self._c_toggle_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Plain)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.addWidget(add_btn)
        bar.addStretch()
        bar.addWidget(sep)
        bar.addWidget(self._c_delete_btn)
        bar.addWidget(self._c_view_btn)
        bar.addWidget(self._c_toggle_btn)
        layout.addLayout(bar)

        self._load_contracts()
        return widget

    def _load_contracts(self):
        records = db.get_contracts_for_instrument(self.instrument_id)
        self.contracts_table.setSortingEnabled(False)
        self.contracts_table.setRowCount(len(records))
        for row, r in enumerate(records):
            vals = [
                str(r["id"]),
                r["student_name"],
                r["date"],
                r["notes"] or "No notes.",
                "Yes" if r["active"] else "No",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setData(Qt.UserRole, dict(r))
                self.contracts_table.setItem(row, col, item)
        self.contracts_table.setSortingEnabled(True)

    def _on_contracts_selection(self):
        has_sel = self.contracts_table.selectionModel().hasSelection()
        for btn in self._contracts_sel_buttons:
            btn.setEnabled(has_sel)

    def _selected_contract(self):
        row = self.contracts_table.currentRow()
        if row < 0:
            return None
        item = self.contracts_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _view_scan(self):
        contract = self._selected_contract()
        if not contract:
            return
        path = contract.get("scan_file_path", "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "No File", "No scan file attached to this contract.")
            return
        _open_file(path)

    def _add_contract_to_instrument(self):
        if not db.get_all_students():
            QMessageBox.information(self, "No Students",
                                    "No students in the system yet.")
            return
        dlg = _AddContractToInstrumentDialog(self.instrument_id, self)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            db.add_contract(dlg.student_id, self.instrument_id, dlg.scan_path, dlg.notes)
            self._load_contracts()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _delete_contract_from_instrument(self):
        contract = self._selected_contract()
        if not contract:
            return
        reply = QMessageBox.warning(
            self, "Confirm Delete",
            f"Delete contract #{contract['id']} for {contract['student_name']}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db.delete_contract(contract["id"])
            self._load_contracts()

    def _toggle_contract_active(self):
        contract = self._selected_contract()
        if not contract:
            return
        db.toggle_contract_active(contract["id"])
        self._load_contracts()
