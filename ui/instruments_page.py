import csv
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QDialogButtonBox, QComboBox, QFormLayout,
    QPlainTextEdit, QFileDialog,
)

import database as db
import config as cfg
from ui.checkout_dialog import CheckoutDialog
from ui.actions_tab import CheckinDialog
from ui.instrument_detail_dialog import InstrumentDetailDialog


STATUSES = ["Available", "Checked Out", "Needs Repair", "Out for Repair"]
REPAIR_STATUSES = {"Needs Repair", "Out for Repair"}


# ── Spreadsheet reader ────────────────────────────────────────────────────────

def _read_spreadsheet(path):
    """Return list of dicts from CSV/TSV/XLSX/XLS/ODS. First row = headers."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".tsv":
        with open(path, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f, delimiter="\t"))
    if ext in (".xlsx", ".ods"):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            return []
        headers = [str(h or "").strip() for h in rows[0]]
        return [
            dict(zip(headers, [str(v or "").strip() for v in row]))
            for row in rows[1:]
        ]
    if ext == ".xls":
        import xlrd
        wb = xlrd.open_workbook(path)
        ws = wb.sheet_by_index(0)
        headers = [str(ws.cell_value(0, c)).strip() for c in range(ws.ncols)]
        return [
            {headers[c]: str(ws.cell_value(r, c)).strip() for c in range(ws.ncols)}
            for r in range(1, ws.nrows)
        ]
    # default: CSV
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ── Dialogs ───────────────────────────────────────────────────────────────────

class AddInstrumentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Instrument")
        self.setFixedWidth(420)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Flute, Trumpet  (required)")
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("e.g., Yamaha YFL-221")
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText("Serial Number (used as QR text if QR blank)")
        self.qr_edit = QLineEdit()
        self.qr_edit.setPlaceholderText("Leave blank to use serial number")

        layout.addRow("Instrument Name *", self.name_edit)
        layout.addRow("Model", self.model_edit)
        layout.addRow("Serial Number", self.serial_edit)
        layout.addRow("QR Code Text", self.qr_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

        self.name_edit.setFocus()

    def _on_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Required", "Instrument name is required.")
            return
        self.accept()

    def get_values(self):
        name = self.name_edit.text().strip()
        model = self.model_edit.text().strip()
        serial = self.serial_edit.text().strip()
        qr = self.qr_edit.text().strip() or serial
        return name, model, serial, qr


class EditInstrumentDialog(QDialog):
    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Instrument")
        self.setFixedWidth(420)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.name_edit = QLineEdit(instrument["name"])
        self.model_edit = QLineEdit(instrument["model"] or "")
        self.serial_edit = QLineEdit(instrument["serial_number"] or "")
        self.qr_edit = QLineEdit(instrument["qr_code_text"] or "")

        layout.addRow("Name:", self.name_edit)
        layout.addRow("Model:", self.model_edit)
        layout.addRow("Serial Number:", self.serial_edit)
        layout.addRow("QR Code Text:", self.qr_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_values(self):
        return (
            self.name_edit.text().strip(),
            self.model_edit.text().strip(),
            self.serial_edit.text().strip(),
            self.qr_edit.text().strip(),
        )


class ChangeStatusDialog(QDialog):
    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Instrument Status")
        self.setMinimumWidth(360)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        instr_label = f"{instrument['name']} ({instrument['serial_number'] or 'no serial'})"
        layout.addRow(QLabel(f"<b>{instr_label}</b>"))

        self.status_combo = QComboBox()
        for s in STATUSES:
            self.status_combo.addItem(s)
        current = instrument["status"] or "Available"
        idx = self.status_combo.findText(current)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self.status_combo.currentTextChanged.connect(self._on_status_changed)
        layout.addRow("Status:", self.status_combo)

        self.repair_label = QLabel("What needs repair:")
        self.repair_notes = QPlainTextEdit()
        self.repair_notes.setPlaceholderText("Describe what needs to be repaired…")
        self.repair_notes.setFixedHeight(80)
        layout.addRow(self.repair_label, self.repair_notes)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

        self._on_status_changed(self.status_combo.currentText())

    def _on_status_changed(self, status):
        visible = status in REPAIR_STATUSES
        self.repair_label.setVisible(visible)
        self.repair_notes.setVisible(visible)

    def _on_accept(self):
        if self.status_combo.currentText() in REPAIR_STATUSES:
            if not self.repair_notes.toPlainText().strip():
                QMessageBox.warning(self, "Notes Required",
                                    "Please describe what needs to be repaired.")
                return
        self.accept()

    def get_status(self):
        return self.status_combo.currentText()

    def get_repair_notes(self):
        return self.repair_notes.toPlainText().strip()


# ── Main page ─────────────────────────────────────────────────────────────────

class InstrumentsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(10)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("All Statuses", "")
        for s in STATUSES:
            self.status_filter.addItem(s, s)
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.status_filter)

        toolbar.addSpacing(8)
        toolbar.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setObjectName("search")
        self.search_box.setPlaceholderText("Filter by name, model, serial, student…")
        self.search_box.setMinimumWidth(80)
        self.search_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_box.textChanged.connect(lambda _: self._apply_filter())
        toolbar.addWidget(self.search_box)

        toolbar.addSpacing(12)
        import_btn = QPushButton("Import CSV / Excel")
        import_btn.setMinimumHeight(32)
        import_btn.clicked.connect(self._import_spreadsheet)
        toolbar.addWidget(import_btn)

        add_btn = QPushButton("+ Add Instrument")
        add_btn.setObjectName("primary")
        add_btn.setMinimumHeight(32)
        add_btn.clicked.connect(self._add_instrument)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Model", "Serial Number",
            "Status", "Current Student", "Last Checked Out", "Last Checked In",
        ])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionsClickable(True)
        hdr.sectionClicked.connect(self._on_header_clicked)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._view_details)
        layout.addWidget(self.table)

        # Row count
        self.row_count_label = QLabel("")
        self.row_count_label.setObjectName("status")
        layout.addWidget(self.row_count_label)

        # Bottom action bar
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
        bar_btn("Edit Details", self._edit_instrument)
        bar_btn("Change Status", self._change_status)
        bar_btn("Delete", self._delete_instrument, danger=True)
        bar_btn("History / Contracts", self._view_details)

        layout.addWidget(bottom)

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if self.table.hasFocus():
            if event.key() == Qt.Key_Delete:
                self._delete_instrument()
                return
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_F2):
                self._edit_instrument()
                return
        super().keyPressEvent(event)

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self):
        self._data = db.get_all_instruments()
        self._apply_filter()
        self._restore_sort()

    def _populate(self, rows):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, instr in enumerate(rows):
            vals = [
                str(instr["id"]),
                instr["name"] or "",
                instr["model"] or "",
                instr["serial_number"] or "",
                instr["status"] or "",
                instr["student_name"] or "N/A",
                instr["last_checked_out"] or "N/A",
                instr["last_checked_in"] or "N/A",
            ]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setData(Qt.UserRole, instr["id"])
                self.table.setItem(r, c, item)

            status_item = self.table.item(r, 4)
            if instr["status"] == "Available":
                status_item.setForeground(Qt.green)
            elif instr["status"] == "Checked Out":
                status_item.setForeground(Qt.yellow)
            else:
                status_item.setForeground(Qt.red)

        self.table.setSortingEnabled(True)

        total = len(self._data)
        shown = len(rows)
        if shown == total:
            self.row_count_label.setText(
                f"Showing {shown} instrument{'s' if shown != 1 else ''}"
            )
        else:
            self.row_count_label.setText(f"Showing {shown} of {total} instruments")

    def _apply_filter(self):
        status = self.status_filter.currentData()
        text = self.search_box.text().lower()
        filtered = self._data
        if status:
            filtered = [i for i in filtered if (i["status"] or "") == status]
        if text:
            filtered = [
                i for i in filtered
                if any(
                    text in str(v or "").lower()
                    for v in [i["name"], i["model"], i["serial_number"],
                               i["qr_code_text"], i["student_name"]]
                )
            ]
        self._populate(filtered)

    def _selected_instrument_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    # ── Sort memory ───────────────────────────────────────────────────────────

    def _on_header_clicked(self, col):
        order = self.table.horizontalHeader().sortIndicatorOrder()
        c = cfg.load_config()
        c["instruments_sort_col"] = col
        c["instruments_sort_asc"] = (order == Qt.AscendingOrder)
        cfg.save_config(c)

    def _restore_sort(self):
        c = cfg.load_config()
        col = c.get("instruments_sort_col", 1)
        asc = c.get("instruments_sort_asc", True)
        order = Qt.AscendingOrder if asc else Qt.DescendingOrder
        self.table.horizontalHeader().setSortIndicator(col, order)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_instrument(self):
        dlg = AddInstrumentDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        name, model, serial, qr = dlg.get_values()
        try:
            db.add_instrument(name, model, serial, qr)
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _import_spreadsheet(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "",
            "Spreadsheets & CSV (*.csv *.tsv *.xlsx *.xls *.ods);;All Files (*)"
        )
        if not path:
            return
        try:
            rows = _read_spreadsheet(path)
        except ImportError as e:
            QMessageBox.critical(
                self, "Missing Library",
                f"Required library not installed:\n{e}\n\n"
                "Run: pip install openpyxl xlrd"
            )
            return
        except Exception as e:
            QMessageBox.critical(self, "Read Error", str(e))
            return

        added, skipped = 0, 0
        with db.get_connection() as conn:
            for row in rows:
                name = row.get("Name", "").strip()
                model = row.get("Model", "").strip()
                serial = row.get("Serial Number", "").strip()
                qr = row.get("QR Code Text", "").strip()
                if not name:
                    skipped += 1
                    continue
                try:
                    conn.execute(
                        "INSERT INTO instruments (name, model, serial_number, qr_code_text) "
                        "VALUES (?, ?, ?, ?)",
                        (name, model, serial, qr),
                    )
                    added += 1
                except Exception:
                    skipped += 1

        self.refresh()
        QMessageBox.information(
            self, "Import Complete",
            f"Added: {added}  Skipped/Errors: {skipped}"
        )

    def _edit_instrument(self):
        iid = self._selected_instrument_id()
        if iid is None:
            QMessageBox.information(self, "No Selection", "Select an instrument first.")
            return
        instr = db.get_instrument_by_id(iid)
        if not instr:
            return
        dlg = EditInstrumentDialog(instr, self)
        if dlg.exec() != QDialog.Accepted:
            return
        name, model, serial, qr = dlg.get_values()
        if not name:
            QMessageBox.warning(self, "Required", "Name cannot be empty.")
            return
        db.update_instrument(iid, name, model, serial, qr)
        self.refresh()

    def _change_status(self):
        iid = self._selected_instrument_id()
        if iid is None:
            QMessageBox.information(self, "No Selection", "Select an instrument first.")
            return
        instr = db.get_instrument_by_id(iid)
        if not instr:
            return

        dlg = ChangeStatusDialog(instr, self)
        if dlg.exec() != QDialog.Accepted:
            return
        new_status = dlg.get_status()

        if new_status == "Checked Out":
            if not db.get_all_students():
                QMessageBox.warning(self, "No Students",
                                    "No students in the system. Add students first.")
                return
            co_dlg = CheckoutDialog(instr, self)
            if co_dlg.exec() != QDialog.Accepted or not co_dlg.selected_student_id:
                return
            db.checkout_instrument(
                iid,
                co_dlg.selected_student_id,
                notes=co_dlg.notes,
                condition_photo_path=co_dlg.condition_photo_path,
                contract_photo_path=co_dlg.contract_photo_path,
            )
            if co_dlg.contract_photo_path:
                db.add_contract(
                    co_dlg.selected_student_id, iid,
                    co_dlg.contract_photo_path,
                    notes=co_dlg.notes or "Created automatically from checkout.",
                )

        elif new_status == "Available":
            ci_dlg = CheckinDialog(instr, self)
            if ci_dlg.exec() != QDialog.Accepted:
                return
            db.checkin_instrument(
                iid,
                notes=ci_dlg.notes,
                condition_photo_path=ci_dlg.condition_photo_path,
            )

        else:
            db.update_instrument_status(iid, new_status)
            if new_status in REPAIR_STATUSES:
                db.log_repair_note(iid, new_status, dlg.get_repair_notes())

        self.refresh()

    def _delete_instrument(self):
        iid = self._selected_instrument_id()
        if iid is None:
            QMessageBox.information(self, "No Selection", "Select an instrument first.")
            return
        instr = db.get_instrument_by_id(iid)
        if not instr:
            return
        reply = QMessageBox.warning(
            self, "Confirm Delete",
            f"Delete {instr['name']} ({instr['serial_number'] or 'no serial'})?\n\n"
            "This will also delete all checkout history for this instrument.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db.delete_instrument(iid)
            self.refresh()

    def _view_details(self):
        iid = self._selected_instrument_id()
        if iid is None:
            QMessageBox.information(self, "No Selection", "Select an instrument first.")
            return
        dlg = InstrumentDetailDialog(iid, self)
        dlg.exec()
