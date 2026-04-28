import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSizePolicy,
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
        header.setStyleSheet("font-size: 16px;")
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

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["Action", "Student", "Timestamp", "Notes", "Photos"]
        )
        hdr = self.history_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
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
        btn_row.addWidget(self.view_cond_btn)
        btn_row.addWidget(self.view_cont_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._load_history()
        return widget

    def _load_history(self):
        records = db.get_instrument_history(self.instrument_id)
        self.history_table.setRowCount(len(records))
        for row, r in enumerate(records):
            action_label = "Check Out" if r["action"] == "check_out" else "Check In"

            cond = r["condition_photo_path"] or ""
            cont = r["contract_photo_path"] or ""
            photo_flags = []
            if cond and os.path.exists(cond):
                photo_flags.append("Condition")
            if cont and os.path.exists(cont):
                photo_flags.append("Contract")
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

    def _on_history_selection(self):
        row = self.history_table.currentRow()
        if row < 0:
            self.view_cond_btn.setEnabled(False)
            self.view_cont_btn.setEnabled(False)
            return
        data = self.history_table.item(row, 0).data(Qt.UserRole)
        cond = data.get("condition_photo_path") or ""
        cont = data.get("contract_photo_path") or ""
        self.view_cond_btn.setEnabled(bool(cond and os.path.exists(cond)))
        self.view_cont_btn.setEnabled(bool(cont and os.path.exists(cont)))

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

    # ── Contracts tab ─────────────────────────────────────────────────────────

    def _build_contracts_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)

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
        layout.addWidget(self.contracts_table)

        view_btn = QPushButton("View Scan File")
        view_btn.clicked.connect(self._view_scan)
        h = QHBoxLayout()
        h.addWidget(view_btn)
        h.addStretch()
        layout.addLayout(h)

        self._load_contracts()
        return widget

    def _load_contracts(self):
        records = db.get_contracts_for_instrument(self.instrument_id)
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

    def _view_scan(self):
        row = self.contracts_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a contract first.")
            return
        data = self.contracts_table.item(row, 0).data(Qt.UserRole)
        path = data.get("scan_file_path", "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "No File", "No scan file attached to this contract.")
            return
        _open_file(path)
