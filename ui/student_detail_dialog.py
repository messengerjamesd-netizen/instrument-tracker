from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QWidget,
)
import database as db

_ACTION_LABELS = {
    "check_out":      "Checked Out",
    "check_in":       "Checked In",
    "needs_repair":   "Needs Repair",
    "out_for_repair": "Out for Repair",
    "repair_returned":"Returned from Repair",
    "summer_hold":    "Summer Hold",
    "available":      "Marked Available",
}


class StudentDetailDialog(QDialog):
    instruments_changed = Signal()

    def __init__(self, student_db_id, parent=None):
        super().__init__(parent)
        self._student_db_id = student_db_id
        self.setMinimumSize(680, 480)
        self.setWindowTitle("Student History")
        student = db.get_student_by_id(student_db_id)
        self._build_ui(student)

    def _build_ui(self, student):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        name  = student["name"]       if student else "Unknown"
        sid   = student["student_id"] if student else ""
        grade = (student["grade"] or "") if student else ""

        layout.addWidget(QLabel(f"<b>{name}</b>"))

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel(f"Student ID: <b>{sid}</b>"))
        if grade:
            info_row.addWidget(QLabel(f"Grade: <b>{grade}</b>"))
        info_row.addStretch()
        layout.addLayout(info_row)

        # Current instruments — refreshable container
        self._cur_container = QWidget()
        self._cur_vbox = QVBoxLayout(self._cur_container)
        self._cur_vbox.setContentsMargins(0, 0, 0, 0)
        self._cur_vbox.setSpacing(6)
        layout.addWidget(self._cur_container)

        # Action feedback label (hidden until an action fires)
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #4caf50; font-style: italic;")
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        layout.addWidget(self._separator())
        layout.addWidget(QLabel("<b>Instrument History</b>"))

        # History table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Instrument", "Model", "Serial Number", "Action", "Date / Notes"]
        )
        hdr_view = self.table.horizontalHeader()
        hdr_view.setSectionResizeMode(QHeaderView.Interactive)
        hdr_view.setStretchLastSection(True)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 100)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Empty-state label shown when history table is empty
        self._empty_label = QLabel("No instrument history yet.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #5a7aaa; font-style: italic; padding: 12px;")
        self._empty_label.setVisible(False)
        layout.addWidget(self._empty_label)

        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(34)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

        self._populate_current()
        self._populate_history()

    # ── Current instruments ───────────────────────────────────────────────────

    def _populate_current(self):
        while self._cur_vbox.count():
            item = self._cur_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        current_instruments = db.get_checked_out_for_student(self._student_db_id)
        if current_instruments:
            for instr in current_instruments:
                row_w = QWidget()
                row = QHBoxLayout(row_w)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(8)

                status = instr["status"] or ""
                status_display = f"  <span style='color:#5a7aaa'>[{status}]</span>" if status else ""
                label = QLabel(
                    f"Currently has: <b>{instr['name']}"
                    f"{' — ' + instr['model'] if instr['model'] else ''}</b>"
                    f"  <span style='color:#5a7aaa'>S/N: {instr['serial_number'] or '—'}</span>"
                    f"{status_display}"
                )
                row.addWidget(label)
                row.addStretch()

                ci_btn = QPushButton("Check In")
                ci_btn.setMinimumHeight(28)
                ci_btn.clicked.connect(lambda _, i=dict(instr): self._do_check_in(i))
                row.addWidget(ci_btn)

                if status == "Summer Hold":
                    resume_btn = QPushButton("Resume Checkout")
                    resume_btn.setMinimumHeight(28)
                    resume_btn.clicked.connect(lambda _, i=dict(instr): self._do_resume(i))
                    row.addWidget(resume_btn)
                else:
                    sh_btn = QPushButton("Summer Hold")
                    sh_btn.setMinimumHeight(28)
                    sh_btn.clicked.connect(lambda _, i=dict(instr): self._do_summer_hold(i))
                    row.addWidget(sh_btn)

                self._cur_vbox.addWidget(row_w)
        else:
            self._cur_vbox.addWidget(QLabel("No instrument currently checked out."))

    # ── History table ─────────────────────────────────────────────────────────

    def _populate_history(self):
        history = db.get_student_history(self._student_db_id)
        self.table.setSortingEnabled(False)
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
        self.table.setSortingEnabled(True)

        has_rows = len(history) > 0
        self.table.setVisible(has_rows)
        self._empty_label.setVisible(not has_rows)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _show_status(self, msg):
        self._status_label.setText(msg)
        self._status_label.setVisible(True)
        # Pass `self` as context — timer won't fire if the dialog is destroyed first
        QTimer.singleShot(3000, self, lambda: self._status_label.setVisible(False))

    def _do_check_in(self, instr):
        from ui.actions_tab import CheckinDialog
        active = db.get_instrument_active_checkouts(instr["id"])
        dlg = CheckinDialog(instr, self, active_checkouts=active)
        if dlg.exec() != QDialog.Accepted:
            return
        db.checkin_instrument(instr["id"], notes=dlg.notes,
                              condition_photo_path=dlg.condition_photo_path,
                              student_db_id=dlg.student_db_id)
        self.instruments_changed.emit()
        self._populate_current()
        self._populate_history()
        self._show_status(f"✓ {instr['name']} checked in.")

    def _do_resume(self, instr):
        reply = QMessageBox.question(
            self, "Resume Checkout",
            f"Resume checkout of <b>{instr['name']}</b> back to Checked Out?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        db.resume_checkout(instr["id"])
        self.instruments_changed.emit()
        self._populate_current()
        self._populate_history()
        self._show_status(f"✓ {instr['name']} resumed as Checked Out.")

    def _do_summer_hold(self, instr):
        active = db.get_instrument_active_checkouts(instr["id"])
        if len(active) > 1:
            from ui.instruments_page import SummerHoldMultiStudentDialog
            dlg = SummerHoldMultiStudentDialog(instr, active, self)
            if dlg.exec() != QDialog.Accepted:
                return
            if dlg.mode == "one" and dlg.summer_student_id is not None:
                other_ids = [c["student_id"] for c in active
                             if c["student_id"] != dlg.summer_student_id]
                if dlg.other_action == "checkin":
                    for oid in other_ids:
                        db.checkin_instrument(instr["id"], student_db_id=oid)
        else:
            reply = QMessageBox.question(
                self, "Summer Hold",
                f"Put <b>{instr['name']}</b> on Summer Hold?<br><br>"
                "The instrument stays assigned to the student but is marked as Summer Hold.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        db.update_instrument_status(instr["id"], "Summer Hold")
        db.log_status_change(instr["id"], "summer_hold")
        self.instruments_changed.emit()
        self._populate_current()
        self._populate_history()
        self._show_status(f"✓ {instr['name']} placed on Summer Hold.")

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line
