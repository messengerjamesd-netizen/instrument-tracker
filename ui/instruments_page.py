import csv
import os

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QDialogButtonBox, QComboBox, QFormLayout,
    QPlainTextEdit, QFileDialog, QMenu, QScrollArea, QCheckBox, QFrame,
)

import database as db
import config as cfg
from ui.checkout_dialog import CheckoutDialog
from ui.actions_tab import CheckinDialog
from ui.instrument_detail_dialog import InstrumentDetailDialog


STATUSES = ["Available", "Checked Out", "Needs Repair", "Out for Repair", "Summer Hold"]
REPAIR_STATUSES = {"Needs Repair", "Out for Repair"}


# ── Spreadsheet helpers ───────────────────────────────────────────────────────

import re as _re

def _norm(s):
    return _re.sub(r"[^a-z0-9]", "", s.lower())

def _find_col(row, *aliases):
    """Return the value for the first key in row that fuzzy-matches any alias."""
    norm_row = {_norm(k): v for k, v in row.items()}
    for alias in aliases:
        val = norm_row.get(_norm(alias))
        if val is not None:
            return (val or "").strip()
    return ""


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
        self.serial_edit.setPlaceholderText("Used for QR code scanning")

        layout.addRow("Instrument Name *", self.name_edit)
        layout.addRow("Model", self.model_edit)
        layout.addRow("Serial Number", self.serial_edit)

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
        return (
            self.name_edit.text().strip(),
            self.model_edit.text().strip(),
            self.serial_edit.text().strip(),
        )


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

        layout.addRow("Name:", self.name_edit)
        layout.addRow("Model:", self.model_edit)
        layout.addRow("Serial Number:", self.serial_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_values(self):
        return (
            self.name_edit.text().strip(),
            self.model_edit.text().strip(),
            self.serial_edit.text().strip(),
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


# ── Bulk change dialog ────────────────────────────────────────────────────────

BULK_STATUSES = ["Available", "Checked Out", "Summer Hold", "Needs Repair", "Out for Repair"]

class BulkChangeStatusDialog(QDialog):
    def __init__(self, instruments, parent=None, preselected_ids=None):
        super().__init__(parent)
        self.setWindowTitle("Change Status for Multiple Instruments")
        self.setMinimumSize(520, 480)
        self._checkboxes = []
        _pre = set(preselected_ids) if preselected_ids else set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Status selector
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Change selected instruments to:"))
        self.status_combo = QComboBox()
        for s in BULK_STATUSES:
            self.status_combo.addItem(s)
        self.status_combo.currentTextChanged.connect(self._on_status_changed)
        top_row.addWidget(self.status_combo)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Repair notes (shown only for repair statuses)
        self.repair_label = QLabel("Notes (applied to all selected):")
        self.repair_notes = QPlainTextEdit()
        self.repair_notes.setPlaceholderText("Describe what needs to be repaired…")
        self.repair_notes.setFixedHeight(60)
        layout.addWidget(self.repair_label)
        layout.addWidget(self.repair_notes)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # Filter + select helpers
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Show:"))
        self._filter_combo = QComboBox()
        self._filter_combo.addItem("All Statuses", "")
        for s in STATUSES:
            self._filter_combo.addItem(s, s)
        self._filter_combo.currentIndexChanged.connect(self._apply_filter)
        sel_row.addWidget(self._filter_combo)
        sel_row.addSpacing(12)
        all_btn = QPushButton("Select All")
        all_btn.setMinimumHeight(28)
        all_btn.clicked.connect(self._select_all_visible)
        none_btn = QPushButton("Deselect All")
        none_btn.setMinimumHeight(28)
        none_btn.clicked.connect(self._deselect_all_visible)
        sel_row.addWidget(all_btn)
        sel_row.addWidget(none_btn)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        # Scrollable instrument list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        list_widget = QWidget()
        self._list_layout = QVBoxLayout(list_widget)
        self._list_layout.setSpacing(4)
        self._list_layout.setContentsMargins(4, 4, 4, 4)

        for instr in instruments:
            label = instr["name"]
            if instr["model"]:
                label += f"  —  {instr['model']}"
            if instr["serial_number"]:
                label += f"  (S/N: {instr['serial_number']})"
            label += f"  [{instr['status']}]"
            cb = QCheckBox(label)
            cb.setChecked(instr["id"] in _pre)
            self._list_layout.addWidget(cb)
            self._checkboxes.append((cb, instr))

        self._list_layout.addStretch()
        scroll.setWidget(list_widget)
        layout.addWidget(scroll, 1)

        btns = QDialogButtonBox()
        apply_btn = btns.addButton("Apply Changes", QDialogButtonBox.AcceptRole)
        apply_btn.setObjectName("primary")
        btns.addButton("Cancel", QDialogButtonBox.RejectRole)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._on_status_changed(self.status_combo.currentText())

    def _on_status_changed(self, status):
        visible = status in REPAIR_STATUSES
        self.repair_label.setVisible(visible)
        self.repair_notes.setVisible(visible)

    def _apply_filter(self):
        filter_status = self._filter_combo.currentData()
        for cb, instr in self._checkboxes:
            visible = not filter_status or instr["status"] == filter_status
            cb.setVisible(visible)
            if not visible:
                cb.setChecked(False)

    def _select_all_visible(self):
        for cb, _ in self._checkboxes:
            if cb.isVisible():
                cb.setChecked(True)

    def _deselect_all_visible(self):
        for cb, _ in self._checkboxes:
            if cb.isVisible():
                cb.setChecked(False)

    def _on_accept(self):
        if not any(cb.isChecked() for cb, _ in self._checkboxes):
            QMessageBox.warning(self, "Nothing Selected", "Select at least one instrument.")
            return
        if self.status_combo.currentText() in REPAIR_STATUSES:
            if not self.repair_notes.toPlainText().strip():
                QMessageBox.warning(self, "Notes Required",
                                    "Please describe what needs to be repaired.")
                return
        self.accept()

    def get_selected(self):
        return [instr for cb, instr in self._checkboxes if cb.isChecked()]

    def get_status(self):
        return self.status_combo.currentText()

    def get_repair_notes(self):
        return self.repair_notes.toPlainText().strip()


# ── Repair return dialog ──────────────────────────────────────────────────────

class RepairReturnDialog(QDialog):
    """Confirm return from repair with optional invoice attachment and notes."""

    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.invoice_path = ""
        self.notes = ""

        name = instrument["name"]
        serial = instrument["serial_number"] or "no serial"
        self.setWindowTitle(f"Return from Repair — {name}")
        self.setMinimumWidth(480)
        self._build_ui(name, serial)

    def _build_ui(self, name, serial):
        from ui.camera_dialog import PhotoCaptureDialog
        self._PhotoCaptureDialog = PhotoCaptureDialog

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        hdr = QLabel(f"<b>{name}</b>  <span style='color:#5a7aaa'>({serial})</span>")
        layout.addWidget(hdr)

        layout.addWidget(self._sep())

        layout.addWidget(QLabel("Repair invoice / work slip (optional):"))

        inv_row = QHBoxLayout()
        self.inv_thumb = self._make_thumb()
        inv_btns = QVBoxLayout()
        inv_btns.setSpacing(4)
        cam_btn = QPushButton("📷  Photograph Invoice")
        cam_btn.setMinimumHeight(34)
        cam_btn.clicked.connect(self._take_photo)
        upload_btn = QPushButton("📁  Upload Invoice File")
        upload_btn.setMinimumHeight(34)
        upload_btn.clicked.connect(self._upload_file)
        inv_btns.addWidget(cam_btn)
        inv_btns.addWidget(upload_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        inv_row.addWidget(self.inv_thumb)
        inv_row.addLayout(inv_btns)
        inv_row.addWidget(clear_btn)
        layout.addLayout(inv_row)

        layout.addWidget(self._sep())

        layout.addWidget(QLabel("Repair notes:"))
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("What was repaired, cost, shop name, etc…")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        layout.addWidget(self._sep())

        btns = QDialogButtonBox()
        confirm_btn = btns.addButton("Mark Returned", QDialogButtonBox.AcceptRole)
        confirm_btn.setObjectName("primary")
        btns.addButton("Cancel", QDialogButtonBox.RejectRole)
        btns.accepted.connect(self._confirm)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _sep(self):
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

    def _take_photo(self):
        dlg = self._PhotoCaptureDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.captured_path:
            self.invoice_path = dlg.captured_path
            self._set_thumb(self.inv_thumb, dlg.captured_path)

    def _upload_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Invoice File", "",
            "Images & PDFs (*.png *.jpg *.jpeg *.bmp *.tiff *.pdf);;All Files (*)"
        )
        if not path:
            return
        self.invoice_path = path
        if path.lower().endswith(".pdf"):
            self.inv_thumb.setPixmap(QPixmap())
            self.inv_thumb.setText("PDF")
        else:
            self._set_thumb(self.inv_thumb, path)

    def _clear(self):
        self.invoice_path = ""
        self.inv_thumb.setPixmap(QPixmap())
        self.inv_thumb.setText("—")

    def _set_thumb(self, label, path):
        pix = QPixmap(path).scaled(
            label.width(), label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(pix)
        label.setText("")

    def _confirm(self):
        self.notes = self.notes_edit.toPlainText().strip()
        self.accept()


# ── Main page ─────────────────────────────────────────────────────────────────

class InstrumentsPage(QWidget):
    navigate_to_student = Signal(int)
    status_changed = Signal()

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

        self.invoice_filter_cb = QCheckBox("Has Repair Invoice")
        self.invoice_filter_cb.stateChanged.connect(lambda _: self._apply_filter())
        toolbar.addSpacing(8)
        toolbar.addWidget(self.invoice_filter_cb)

        toolbar.addSpacing(12)
        import_btn = QPushButton("Import Spreadsheet")
        import_btn.setMinimumHeight(32)
        import_btn.setToolTip(
            "Expected columns: Name, Model, Serial Number\n"
            "Supports .csv, .tsv, .xlsx, .xls, .ods"
        )
        import_btn.clicked.connect(self._import_spreadsheet)
        toolbar.addWidget(import_btn)

        bulk_btn = QPushButton("Bulk Change Status")
        bulk_btn.setMinimumHeight(32)
        bulk_btn.clicked.connect(self._bulk_change_status)
        toolbar.addWidget(bulk_btn)

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
            "Status", "Checked Out To", "Last Checked Out", "Last Checked In",
        ])
        self.table.setColumnHidden(0, True)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionsClickable(True)
        hdr.sectionClicked.connect(self._on_header_clicked)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._view_details)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_right_click)
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        self.table.cellEntered.connect(self._on_cell_hovered)
        self.table.viewport().installEventFilter(self)
        self._hovered_link_cell = None
        layout.addWidget(self.table)

        # Hint + row count
        hint = QLabel("Tip: Right-click a row to change its status. Double-click to view full history and contracts. Ctrl+click or Shift+click to select multiple for bulk actions.")
        hint.setStyleSheet("color: #5a7aaa; padding: 2px 0;")
        layout.addWidget(hint)

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
            all_names_raw = instr["all_student_names"] or instr["student_name"] or ""
            if all_names_raw:
                name_list = [n.strip() for n in all_names_raw.split(",") if n.strip()]
                if len(name_list) > 1:
                    display_students = f"{name_list[0]} + {len(name_list) - 1} more"
                else:
                    display_students = name_list[0] if name_list else "N/A"
            else:
                display_students = "N/A"
            vals = [
                str(instr["id"]),
                instr["name"] or "",
                instr["model"] or "",
                instr["serial_number"] or "",
                instr["status"] or "",
                display_students,
                instr["last_checked_out"] or "N/A",
                instr["last_checked_in"] or "N/A",
            ]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setData(Qt.UserRole, instr["id"])
                self.table.setItem(r, c, item)

            student_id = instr["current_student_id"]
            student_item = self.table.item(r, 5)
            if student_id and student_item:
                student_item.setForeground(QColor("#7eb8f7"))
                if all_names_raw and "," in all_names_raw:
                    student_item.setToolTip(all_names_raw.replace(",", "\n"))
                else:
                    student_item.setToolTip("Click to view this student")
                student_item.setData(Qt.UserRole + 1, student_id)

            status_item = self.table.item(r, 4)
            if instr["status"] == "Available":
                status_item.setForeground(Qt.green)
            elif instr["status"] == "Checked Out":
                status_item.setForeground(Qt.yellow)
            elif instr["status"] == "Summer Hold":
                status_item.setForeground(QColor("#7eb8f7"))
            else:
                status_item.setForeground(Qt.red)

        self.table.setSortingEnabled(True)

        total = len(self._data)
        shown = len(rows)
        if total == 0:
            self.row_count_label.setText(
                "No instruments yet — click Add Instrument or Import Spreadsheet to get started."
            )
        elif shown == 0:
            self.row_count_label.setText("No instruments match your filter.")
        elif shown == total:
            self.row_count_label.setText(
                f"Showing {shown} instrument{'s' if shown != 1 else ''}"
            )
        else:
            self.row_count_label.setText(f"Showing {shown} of {total} instruments")

    def _apply_filter(self):
        status = self.status_filter.currentData()
        text = self.search_box.text().lower()
        invoice_only = self.invoice_filter_cb.isChecked()
        filtered = self._data
        if status:
            filtered = [i for i in filtered if (i["status"] or "") == status]
        if text:
            filtered = [
                i for i in filtered
                if any(
                    text in str(v or "").lower()
                    for v in [i["name"], i["model"], i["serial_number"],
                               i["qr_code_text"], i["all_student_names"]]
                )
            ]
        if invoice_only:
            ids = db.get_instrument_ids_with_repair_invoices()
            filtered = [i for i in filtered if i["id"] in ids]
        self._populate(filtered)

    def _selected_instrument_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _selected_instrument_ids(self):
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        ids = []
        for row in sorted(rows):
            item = self.table.item(row, 0)
            if item:
                ids.append(item.data(Qt.UserRole))
        return ids

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

    def _do_checkout(self, instr, add_student=False):
        """Handle changing an instrument to Checked Out. Returns True if successful.

        add_student=True skips the 'already checked out' confirmation and goes straight
        to the student picker (used when the user explicitly chose 'Add Another Student').
        """
        if instr["status"] == "Summer Hold" and instr["current_student_id"]:
            active = db.get_instrument_active_checkouts(instr["id"])
            names = ", ".join(c["student_name"] for c in active) if active else "the assigned student"
            reply = QMessageBox.question(
                self, "Resume Checkout",
                f"Check out back to {names}?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                db.resume_checkout(instr["id"])
                return True
            return False

        if instr["status"] == "Checked Out":
            if not add_student:
                active = db.get_instrument_active_checkouts(instr["id"])
                current_names = ", ".join(c["student_name"] for c in active) or "Unknown"
                reply = QMessageBox.question(
                    self, "Already Checked Out",
                    f"{instr['name']} is already checked out to {current_names}.\n\n"
                    "Add another student to this checkout?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return False
            if not db.get_all_students():
                QMessageBox.warning(self, "No Students",
                                    "No students in the system. Add students first.")
                return False
            co_dlg = CheckoutDialog(instr, self)
            if co_dlg.exec() != QDialog.Accepted or not co_dlg.selected_student_id:
                return False
            db.checkout_instrument_additional(instr["id"], co_dlg.selected_student_id,
                                              notes=co_dlg.notes,
                                              condition_photo_path=co_dlg.condition_photo_path,
                                              contract_photo_path=co_dlg.contract_photo_path)
            if co_dlg.contract_photo_path:
                db.add_contract(co_dlg.selected_student_id, instr["id"],
                                co_dlg.contract_photo_path,
                                notes=co_dlg.notes or "Created automatically from checkout.")
            return True

        if not db.get_all_students():
            QMessageBox.warning(self, "No Students",
                                "No students in the system. Add students first.")
            return False
        co_dlg = CheckoutDialog(instr, self)
        if co_dlg.exec() != QDialog.Accepted or not co_dlg.selected_student_id:
            return False
        db.checkout_instrument(instr["id"], co_dlg.selected_student_id,
                               notes=co_dlg.notes,
                               condition_photo_path=co_dlg.condition_photo_path,
                               contract_photo_path=co_dlg.contract_photo_path)
        if co_dlg.contract_photo_path:
            db.add_contract(co_dlg.selected_student_id, instr["id"],
                            co_dlg.contract_photo_path,
                            notes=co_dlg.notes or "Created automatically from checkout.")
        return True

    def _do_summer_hold(self, instr):
        """Handle changing an instrument to Summer Hold. Returns True if successful."""
        if instr["current_student_id"]:
            db.update_instrument_status(instr["id"], "Summer Hold")
            db.log_status_change(instr["id"], "summer_hold")
            return True
        reply = QMessageBox.question(
            self, "Student Required",
            "Summer Hold requires a student to be assigned.\n\n"
            "Assign a student now and then mark as Summer Hold?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return False
        if not db.get_all_students():
            QMessageBox.warning(self, "No Students",
                                "No students in the system. Add students first.")
            return False
        co_dlg = CheckoutDialog(instr, self)
        if co_dlg.exec() != QDialog.Accepted or not co_dlg.selected_student_id:
            return False
        db.checkout_instrument(instr["id"], co_dlg.selected_student_id,
                               notes=co_dlg.notes,
                               condition_photo_path=co_dlg.condition_photo_path,
                               contract_photo_path=co_dlg.contract_photo_path)
        db.update_instrument_status(instr["id"], "Summer Hold")
        db.log_status_change(instr["id"], "summer_hold")
        if co_dlg.contract_photo_path:
            db.add_contract(co_dlg.selected_student_id, instr["id"],
                            co_dlg.contract_photo_path,
                            notes=co_dlg.notes or "Created automatically from checkout.")
        return True

    def _on_right_click(self, pos):
        item = self.table.itemAt(pos)
        if not item or item.column() != 4:
            return
        clicked_iid = self.table.item(item.row(), 0).data(Qt.UserRole)

        # If the clicked row is part of a multi-selection, handle all together
        selected_iids = self._selected_instrument_ids()
        if len(selected_iids) > 1 and clicked_iid in selected_iids:
            self._on_right_click_multi(selected_iids, pos)
            return

        # Single-instrument path (original behaviour)
        iid = clicked_iid
        instr = db.get_instrument_by_id(iid)
        if not instr:
            return
        menu = QMenu(self)
        for status in STATUSES:
            action = menu.addAction(status)
            if status == instr["status"]:
                action.setEnabled(False)
        # If already checked out, offer adding another student
        add_student_action = None
        if instr["status"] == "Checked Out":
            menu.addSeparator()
            add_student_action = menu.addAction("Add Another Student…")
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if not chosen:
            return
        if add_student_action and chosen == add_student_action:
            if not self._do_checkout(instr, add_student=True):
                return
            self.refresh()
            self.status_changed.emit()
            return
        new_status = chosen.text()
        if new_status == "Checked Out":
            if not self._do_checkout(instr):
                return
        elif new_status == "Available":
            if instr["status"] in REPAIR_STATUSES:
                ret_dlg = RepairReturnDialog(instr, self)
                if ret_dlg.exec() != QDialog.Accepted:
                    return
                db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
            else:
                active = db.get_instrument_active_checkouts(iid)
                ci_dlg = CheckinDialog(instr, self, active_checkouts=active)
                if ci_dlg.exec() != QDialog.Accepted:
                    return
                db.checkin_instrument(iid, notes=ci_dlg.notes,
                                      condition_photo_path=ci_dlg.condition_photo_path,
                                      student_db_id=ci_dlg.student_db_id)
        elif new_status == "Summer Hold":
            if instr["status"] in REPAIR_STATUSES:
                ret_dlg = RepairReturnDialog(instr, self)
                if ret_dlg.exec() != QDialog.Accepted:
                    return
                db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
                instr = db.get_instrument_by_id(iid)
            if not self._do_summer_hold(instr):
                return
        elif new_status in REPAIR_STATUSES:
            dlg = ChangeStatusDialog(instr, self)
            dlg.status_combo.setCurrentText(new_status)
            if dlg.exec() != QDialog.Accepted:
                return
            db.update_instrument_status(iid, new_status)
            db.log_repair_note(iid, new_status, dlg.get_repair_notes())
        else:
            db.update_instrument_status(iid, new_status)
        self.refresh()
        self.status_changed.emit()

    def _on_right_click_multi(self, iids, pos):
        """Right-click handler when multiple rows are selected."""
        menu = QMenu(self)
        for status in STATUSES:
            menu.addAction(status)
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if not chosen:
            return
        new_status = chosen.text()

        instruments = [db.get_instrument_by_id(i) for i in iids]
        instruments = [i for i in instruments if i]

        # Process every instrument sequentially with its own dialog
        applied, cancelled = 0, 0
        for instr in instruments:
            iid = instr["id"]
            if new_status == "Checked Out":
                if instr["status"] in REPAIR_STATUSES:
                    ret_dlg = RepairReturnDialog(instr, self)
                    if ret_dlg.exec() != QDialog.Accepted:
                        cancelled += 1
                        continue
                    db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
                    instr = db.get_instrument_by_id(iid)
                if not self._do_checkout(instr):
                    cancelled += 1
                    continue
            elif new_status == "Available":
                if instr["status"] in REPAIR_STATUSES:
                    ret_dlg = RepairReturnDialog(instr, self)
                    if ret_dlg.exec() != QDialog.Accepted:
                        cancelled += 1
                        continue
                    db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
                else:
                    active = db.get_instrument_active_checkouts(iid)
                    ci_dlg = CheckinDialog(instr, self, active_checkouts=active)
                    if ci_dlg.exec() != QDialog.Accepted:
                        cancelled += 1
                        continue
                    db.checkin_instrument(iid, notes=ci_dlg.notes,
                                          condition_photo_path=ci_dlg.condition_photo_path,
                                          student_db_id=ci_dlg.student_db_id)
            elif new_status == "Summer Hold":
                if instr["status"] in REPAIR_STATUSES:
                    ret_dlg = RepairReturnDialog(instr, self)
                    if ret_dlg.exec() != QDialog.Accepted:
                        cancelled += 1
                        continue
                    db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
                    instr = db.get_instrument_by_id(iid)
                if not self._do_summer_hold(instr):
                    cancelled += 1
                    continue
            elif new_status in REPAIR_STATUSES:
                dlg = ChangeStatusDialog(instr, self)
                dlg.status_combo.setCurrentText(new_status)
                if dlg.exec() != QDialog.Accepted:
                    cancelled += 1
                    continue
                db.update_instrument_status(iid, new_status)
                db.log_repair_note(iid, new_status, dlg.get_repair_notes())
            else:
                db.update_instrument_status(iid, new_status)
            applied += 1

        self.refresh()
        self.status_changed.emit()
        msg = f"Updated {applied} instrument{'s' if applied != 1 else ''}."
        if cancelled:
            msg += f"\n{cancelled} skipped or cancelled."
        QMessageBox.information(self, "Done", msg)

    def _bulk_change_status(self):
        instruments = db.get_all_instruments()
        if not instruments:
            QMessageBox.information(self, "No Instruments",
                                    "No instruments in the system yet.")
            return
        preselected = self._selected_instrument_ids()
        dlg = BulkChangeStatusDialog(instruments, self,
                                     preselected_ids=preselected if preselected else None)
        if dlg.exec() != QDialog.Accepted:
            return
        new_status = dlg.get_status()
        repair_notes = dlg.get_repair_notes()
        selected = dlg.get_selected()

        if new_status == "Checked Out":
            applied, cancelled = 0, 0
            for instr in selected:
                fresh = db.get_instrument_by_id(instr["id"])
                if not fresh:
                    continue
                iid = fresh["id"]
                if fresh["status"] in REPAIR_STATUSES:
                    ret_dlg = RepairReturnDialog(fresh, self)
                    if ret_dlg.exec() != QDialog.Accepted:
                        cancelled += 1
                        continue
                    db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
                    fresh = db.get_instrument_by_id(iid)
                if not self._do_checkout(fresh):
                    cancelled += 1
                    continue
                applied += 1
            self.refresh()
            self.status_changed.emit()
            msg = f"Checked out {applied} instrument{'s' if applied != 1 else ''}."
            if cancelled:
                msg += f"\n{cancelled} skipped or cancelled."
            QMessageBox.information(self, "Done", msg)
            return

        if new_status == "Summer Hold":
            applied, skipped = 0, 0
            for instr in selected:
                if instr["current_student_id"]:
                    db.update_instrument_status(instr["id"], "Summer Hold")
                    db.log_status_change(instr["id"], "summer_hold")
                    applied += 1
                else:
                    skipped += 1
            self.refresh()
            self.status_changed.emit()
            msg = f"Set {applied} instrument{'s' if applied != 1 else ''} to Summer Hold."
            if skipped:
                msg += (f"\n{skipped} skipped (no student assigned)."
                        "\nUse Change Status on each to assign a student first.")
            QMessageBox.information(self, "Done", msg)
            return

        if new_status == "Available":
            applied, cancelled = 0, 0
            for instr in selected:
                iid = instr["id"]
                if instr["status"] in REPAIR_STATUSES:
                    ret_dlg = RepairReturnDialog(instr, self)
                    if ret_dlg.exec() != QDialog.Accepted:
                        cancelled += 1
                        continue
                    db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
                else:
                    active = db.get_instrument_active_checkouts(iid)
                    ci_dlg = CheckinDialog(instr, self, active_checkouts=active)
                    if ci_dlg.exec() != QDialog.Accepted:
                        cancelled += 1
                        continue
                    db.checkin_instrument(iid, notes=ci_dlg.notes,
                                          condition_photo_path=ci_dlg.condition_photo_path,
                                          student_db_id=ci_dlg.student_db_id)
                applied += 1
            self.refresh()
            self.status_changed.emit()
            msg = f"Checked in {applied} instrument{'s' if applied != 1 else ''}."
            if cancelled:
                msg += f"\n{cancelled} skipped or cancelled."
            QMessageBox.information(self, "Done", msg)
            return

        for instr in selected:
            db.update_instrument_status(instr["id"], new_status)
            if new_status in REPAIR_STATUSES:
                db.log_repair_note(instr["id"], new_status, repair_notes)
        self.refresh()
        self.status_changed.emit()
        QMessageBox.information(self, "Done",
                                f"Updated {len(selected)} instrument{'s' if len(selected) != 1 else ''}.")

    def _add_instrument(self):
        dlg = AddInstrumentDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        name, model, serial = dlg.get_values()
        try:
            db.add_instrument(name, model, serial)
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
                name = _find_col(row,
                    "Name", "Instrument", "Instrument Name", "Item",
                    "Description", "Type", "Instrument Type")
                model = _find_col(row,
                    "Model", "Make", "Make/Model", "Manufacturer", "Brand")
                serial = _find_col(row,
                    "Serial Number", "Serial", "Serial #", "Serial No",
                    "Serial No.", "SN", "S/N", "Serial_Number", "SerialNumber")
                if not name:
                    skipped += 1
                    continue
                try:
                    conn.execute(
                        "INSERT INTO instruments (name, model, serial_number, qr_code_text) "
                        "VALUES (?, ?, ?, ?)",
                        (name, model, serial, serial),
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
        name, model, serial = dlg.get_values()
        if not name:
            QMessageBox.warning(self, "Required", "Name cannot be empty.")
            return
        db.update_instrument(iid, name, model, serial)
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
            if instr["status"] in REPAIR_STATUSES:
                ret_dlg = RepairReturnDialog(instr, self)
                if ret_dlg.exec() != QDialog.Accepted:
                    return
                db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
                instr = db.get_instrument_by_id(iid)
                if not instr:
                    return
            if not self._do_checkout(instr):
                return

        elif new_status == "Available":
            if instr["status"] in REPAIR_STATUSES:
                ret_dlg = RepairReturnDialog(instr, self)
                if ret_dlg.exec() != QDialog.Accepted:
                    return
                db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
            else:
                active = db.get_instrument_active_checkouts(iid)
                ci_dlg = CheckinDialog(instr, self, active_checkouts=active)
                if ci_dlg.exec() != QDialog.Accepted:
                    return
                db.checkin_instrument(
                    iid,
                    notes=ci_dlg.notes,
                    condition_photo_path=ci_dlg.condition_photo_path,
                    student_db_id=ci_dlg.student_db_id,
                )

        elif new_status == "Summer Hold":
            if instr["status"] in REPAIR_STATUSES:
                ret_dlg = RepairReturnDialog(instr, self)
                if ret_dlg.exec() != QDialog.Accepted:
                    return
                db.log_repair_return(iid, ret_dlg.notes, ret_dlg.invoice_path)
                instr = db.get_instrument_by_id(iid)
                if not instr:
                    return
            if not self._do_summer_hold(instr):
                return

        else:
            db.update_instrument_status(iid, new_status)
            if new_status in REPAIR_STATUSES:
                db.log_repair_note(iid, new_status, dlg.get_repair_notes())

        self.refresh()
        self.status_changed.emit()

    def _delete_instrument(self):
        iids = self._selected_instrument_ids()
        if not iids:
            QMessageBox.information(self, "No Selection", "Select one or more instruments first.")
            return
        if len(iids) == 1:
            instr = db.get_instrument_by_id(iids[0])
            if not instr:
                return
            msg = (f"Delete {instr['name']} ({instr['serial_number'] or 'no serial'})?\n\n"
                   "This will also delete all checkout history for this instrument.")
        else:
            instrs = [db.get_instrument_by_id(i) for i in iids]
            names = "\n".join(
                f"  • {i['name']} ({i['serial_number'] or 'no serial'})"
                for i in instrs if i
            )
            msg = (f"Delete {len(iids)} instruments?\n\n{names}\n\n"
                   "This will also delete all checkout history for these instruments.")
        reply = QMessageBox.warning(self, "Confirm Delete", msg,
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for iid in iids:
                db.delete_instrument(iid)
            self.refresh()

    def _on_cell_hovered(self, row, col):
        self._clear_link_hover()
        item = self.table.item(row, col)
        if col == 5 and item and item.data(Qt.UserRole + 1):
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            self._hovered_link_cell = (row, col)

    def _clear_link_hover(self):
        if self._hovered_link_cell:
            r, c = self._hovered_link_cell
            item = self.table.item(r, c)
            if item:
                font = item.font()
                font.setBold(False)
                item.setFont(font)
            self._hovered_link_cell = None

    def eventFilter(self, obj, event):
        if obj is self.table.viewport() and event.type() == QEvent.Leave:
            self._clear_link_hover()
        return super().eventFilter(obj, event)

    def _on_cell_clicked(self, row, col):
        if col != 5:
            return
        item = self.table.item(row, 5)
        if not item:
            return
        student_id = item.data(Qt.UserRole + 1)
        if student_id:
            self.navigate_to_student.emit(student_id)

    def show_instrument(self, instrument_id):
        self.status_filter.setCurrentIndex(0)
        self.search_box.clear()
        self.refresh()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == instrument_id:
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                break

    def _view_details(self):
        iid = self._selected_instrument_id()
        if iid is None:
            QMessageBox.information(self, "No Selection", "Select an instrument first.")
            return
        dlg = InstrumentDetailDialog(iid, self)
        dlg.exec()
