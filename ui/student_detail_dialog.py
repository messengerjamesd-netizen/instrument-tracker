from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
)
import database as db

_ACTION_LABELS = {
    "check_out":     "Checked Out",
    "check_in":      "Checked In",
    "needs_repair":  "Needs Repair",
    "out_for_repair":"Out for Repair",
}


class StudentDetailDialog(QDialog):
    def __init__(self, student_db_id, parent=None):
        super().__init__(parent)
        self.setMinimumSize(680, 480)
        self.setWindowTitle("Student History")
        student = db.get_student_by_id(student_db_id)
        self._build_ui(student, student_db_id)

    def _build_ui(self, student, student_db_id):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        name = student["name"] if student else "Unknown"
        sid  = student["student_id"] if student else ""
        grade = student["grade"] or "" if student else ""

        hdr = QLabel(f"<b>{name}</b>")
        layout.addWidget(hdr)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel(f"Student ID: <b>{sid}</b>"))
        if grade:
            info_row.addWidget(QLabel(f"Grade: <b>{grade}</b>"))
        info_row.addStretch()
        layout.addLayout(info_row)

        # Current instrument
        instruments = db.get_all_instruments()
        current = next(
            (i for i in instruments
             if i["current_student_id"] == student_db_id),
            None,
        )
        if current:
            cur_label = QLabel(
                f"Currently has: <b>{current['name']}"
                f"{' — ' + current['model'] if current['model'] else ''}</b>"
                f"  <span style='color:#5a7aaa'>S/N: {current['serial_number'] or '—'}</span>"
            )
        else:
            cur_label = QLabel("No instrument currently checked out.")
        layout.addWidget(cur_label)

        layout.addWidget(self._separator())
        layout.addWidget(QLabel("<b>Instrument History</b>"))

        # History table
        history = db.get_student_history(student_db_id)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Instrument", "Model", "Serial Number", "Action", "Date / Notes"]
        )
        hdr_view = self.table.horizontalHeader()
        hdr_view.setSectionResizeMode(QHeaderView.Stretch)
        hdr_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)

        self.table.setRowCount(len(history))
        for r, row in enumerate(history):
            action = _ACTION_LABELS.get(row["action"], row["action"])
            date_notes = row["timestamp"] or ""
            if row["notes"]:
                date_notes += f"  —  {row['notes']}"
            vals = [
                row["instrument_name"] or "—",
                row["model"] or "—",
                row["serial_number"] or "—",
                action,
                date_notes,
            ]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(r, c, item)

        layout.addWidget(self.table)

        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(34)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line
