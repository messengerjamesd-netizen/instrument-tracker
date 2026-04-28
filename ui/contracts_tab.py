import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QDialog, QSizePolicy,
)
import database as db
from ui.camera_dialog import PhotoCaptureDialog


class ContractsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(12)

        title = QLabel("Manage Contracts")
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(self._build_add_group())

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Student", "Instrument", "Date", "Notes", "Active"]
        )
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Active
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Bottom bar
        bottom = QWidget()
        bottom.setObjectName("bottom_bar")
        bar = QHBoxLayout(bottom)
        bar.setContentsMargins(8, 6, 8, 6)
        bar.setSpacing(8)

        def bar_btn(text, slot, danger=False):
            btn = QPushButton(text)
            btn.setMinimumHeight(34)
            btn.setMinimumWidth(60)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if danger:
                btn.setObjectName("danger")
            btn.clicked.connect(slot)
            bar.addWidget(btn)
            return btn

        bar_btn("Refresh", self.refresh)
        bar_btn("View Scan", self._view_scan)
        bar_btn("Toggle Active", self._toggle_active)
        bar_btn("Delete", self._delete_contract, danger=True)

        layout.addWidget(bottom)

    # ── Add form ──────────────────────────────────────────────────────────────

    def _build_add_group(self):
        group = QGroupBox("Add New Contract")
        v = QVBoxLayout(group)
        v.setSpacing(8)

        def form_label(text, align_top=False):
            lbl = QLabel(text)
            lbl.setMinimumWidth(70)
            if align_top:
                lbl.setAlignment(Qt.AlignTop)
            return lbl

        # Student row
        s_row = QHBoxLayout()
        self.student_combo = QComboBox()
        self.student_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        s_row.addWidget(form_label("Student:"))
        s_row.addWidget(self.student_combo)
        v.addLayout(s_row)

        # Instrument row
        i_row = QHBoxLayout()
        self.instrument_combo = QComboBox()
        self.instrument_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        i_row.addWidget(form_label("Instrument\n(Optional):"))
        i_row.addWidget(self.instrument_combo)
        v.addLayout(i_row)

        # Scan file row
        f_row = QHBoxLayout()
        self.scan_path_edit = QLineEdit()
        self.scan_path_edit.setPlaceholderText("Path to scan/photo file…")
        self.scan_path_edit.setReadOnly(True)
        select_btn = QPushButton("Select File")
        select_btn.setMinimumWidth(70)
        select_btn.clicked.connect(self._select_scan_file)
        photo_btn = QPushButton("Take Photo")
        photo_btn.setMinimumWidth(70)
        photo_btn.clicked.connect(self._take_photo)
        clear_btn = QPushButton("Clear")
        clear_btn.setMinimumWidth(44)
        clear_btn.clicked.connect(lambda: self.scan_path_edit.clear())
        f_row.addWidget(form_label("Scan File:"))
        f_row.addWidget(self.scan_path_edit)
        f_row.addWidget(select_btn)
        f_row.addWidget(photo_btn)
        f_row.addWidget(clear_btn)
        v.addLayout(f_row)

        # Notes row
        n_row = QHBoxLayout()
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes…")
        self.notes_edit.setMinimumHeight(50)
        self.notes_edit.setMaximumHeight(120)
        n_row.addWidget(form_label("Notes:", align_top=True))
        n_row.addWidget(self.notes_edit)
        v.addLayout(n_row)

        add_btn = QPushButton("Add Contract")
        add_btn.setObjectName("primary")
        add_btn.setMinimumHeight(36)
        add_btn.clicked.connect(self._add_contract)
        v.addWidget(add_btn)

        self.add_status = QLabel("")
        self.add_status.setObjectName("status")
        v.addWidget(self.add_status)

        self._populate_combos()
        return group

    def _populate_combos(self):
        self.student_combo.clear()
        self.student_combo.addItem("-- Select Student --", None)
        for s in db.get_all_students():
            self.student_combo.addItem(f"{s['name']} ({s['student_id']})", s["id"])

        self.instrument_combo.clear()
        self.instrument_combo.addItem("-- Select Instrument (Optional) --", None)
        for i in db.get_all_instruments():
            label = f"{i['name']}"
            if i["serial_number"]:
                label += f" ({i['serial_number']})"
            self.instrument_combo.addItem(label, i["id"])

    def _select_scan_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Scan File", "",
            "Image/PDF Files (*.jpg *.jpeg *.png *.pdf);;All Files (*)"
        )
        if path:
            self.scan_path_edit.setText(path)

    def _take_photo(self):
        dlg = PhotoCaptureDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.captured_path:
            self.scan_path_edit.setText(dlg.captured_path)
            self.add_status.setText(f"Photo saved: {os.path.basename(dlg.captured_path)}")

    def _add_contract(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            self.add_status.setText("Please select a student.")
            return

        instrument_id = self.instrument_combo.currentData()
        scan_path = self.scan_path_edit.text().strip()
        notes = self.notes_edit.toPlainText().strip()

        try:
            db.add_contract(student_id, instrument_id, scan_path, notes)
            self.add_status.setText("Contract added.")
            self.scan_path_edit.clear()
            self.notes_edit.clear()
            self.student_combo.setCurrentIndex(0)
            self.instrument_combo.setCurrentIndex(0)
            self.refresh()
        except Exception as e:
            self.add_status.setText(f"Error: {e}")

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self):
        self._populate_combos()
        self._data = db.get_all_contracts()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._data))
        for r, c in enumerate(self._data):
            instr_label = ""
            if c["instrument_name"]:
                instr_label = c["instrument_name"]
                if c["instrument_serial"]:
                    instr_label += f" ({c['instrument_serial']})"

            notes_preview = (c["notes"] or "No notes.")[:60]
            active_label = "Yes" if c["active"] else "No"

            vals = [
                str(c["id"]),
                c["student_name"],
                instr_label or "—",
                c["date"],
                notes_preview,
                active_label,
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setData(Qt.UserRole, dict(c))
                self.table.setItem(r, col, item)

            if not c["active"]:
                for col in range(self.table.columnCount()):
                    it = self.table.item(r, col)
                    if it:
                        it.setForeground(Qt.darkGray)

        self.table.setSortingEnabled(True)

    def _selected_contract(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    # ── Actions ───────────────────────────────────────────────────────────────

    def _view_scan(self):
        contract = self._selected_contract()
        if not contract:
            QMessageBox.information(self, "No Selection", "Select a contract first.")
            return
        path = contract.get("scan_file_path", "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "No File", "No scan file attached to this contract.")
            return
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])

    def _toggle_active(self):
        contract = self._selected_contract()
        if not contract:
            QMessageBox.information(self, "No Selection", "Select a contract first.")
            return
        db.toggle_contract_active(contract["id"])
        self.refresh()

    def _delete_contract(self):
        contract = self._selected_contract()
        if not contract:
            QMessageBox.information(self, "No Selection", "Select a contract first.")
            return
        reply = QMessageBox.warning(
            self, "Confirm Delete",
            f"Delete contract #{contract['id']} for {contract['student_name']}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db.delete_contract(contract["id"])
            self.refresh()
