from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy, QMessageBox,
)
from PySide6.QtGui import QTextDocument, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
import database as db


REPORTS = [
    ("current_checkouts", "Current Checkouts",
     "All instruments currently checked out, with student name and checkout date."),
    ("full_inventory",    "Full Inventory",
     "Every instrument in the system with its status, model, and serial number."),
    ("student_roster",    "Student Roster",
     "All students, their grade, and their currently assigned instrument."),
    ("needs_repair",      "Needs Repair",
     "Instruments currently flagged as Needs Repair or Out for Repair."),
    ("available",         "Available Instruments",
     "All instruments currently available to check out."),
]


class _ReportCard(QFrame):
    clicked = Signal()

    def __init__(self, title, desc, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size: 11px;")
        desc_lbl.setWordWrap(True)

        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _table(headers, rows, empty_msg="No records found."):
    if not rows:
        return f"<p style='color:#888;font-style:italic;margin-top:14px;'>{empty_msg}</p>"
    th = "".join(
        f"<th style='background:#1a3666;color:white;padding:7px 10px;"
        f"text-align:left;border:1px solid #bbc;'>{h}</th>"
        for h in headers
    )
    body = ""
    for i, row in enumerate(rows):
        bg = "#f2f5fa" if i % 2 == 0 else "#ffffff"
        tds = "".join(
            f"<td style='padding:5px 10px;border:1px solid #dde;background:{bg};'>{v}</td>"
            for v in row
        )
        body += f"<tr>{tds}</tr>"
    return (
        f"<table style='border-collapse:collapse;width:100%;margin-top:14px;'>"
        f"<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"
    )


def _wrap(title, table_html):
    date_str = datetime.now().strftime("%B %d, %Y  %I:%M %p")
    return (
        "<html><body style='font-family:Arial,sans-serif;font-size:10pt;margin:20px;'>"
        f"<h2 style='color:#1a3666;margin-bottom:2px;'>{title}</h2>"
        f"<p style='color:#666;margin-top:2px;font-size:9pt;'>Generated: {date_str}</p>"
        "<hr style='border:1px solid #ccd;'/>"
        f"{table_html}"
        "</body></html>"
    )


def _build_html(key):
    if key == "current_checkouts":
        rows = db.get_current_checkouts()
        data = [
            [r["name"], r["model"] or "—", r["serial_number"] or "—",
             r["student_name"] or "—", r["last_checked_out"] or "—"]
            for r in rows
        ]
        return _wrap("Current Checkouts",
                     _table(["Instrument", "Model", "Serial #", "Student", "Checked Out"],
                            data, "No instruments currently checked out."))

    if key == "full_inventory":
        rows = db.get_all_instruments()
        data = [
            [r["name"], r["model"] or "—", r["serial_number"] or "—",
             r["status"], r["student_name"] or "—"]
            for r in rows
        ]
        return _wrap("Full Inventory",
                     _table(["Instrument", "Model", "Serial #", "Status", "Current Student"],
                            data, "No instruments in the system."))

    if key == "student_roster":
        rows = db.get_student_roster()
        data = [
            [r["name"], r["student_id"], r["grade"] or "—",
             r["instrument_name"] or "None", r["serial_number"] or "—"]
            for r in rows
        ]
        return _wrap("Student Roster",
                     _table(["Student", "Student ID", "Grade", "Instrument", "Serial #"],
                            data, "No students in the system."))

    if key == "needs_repair":
        rows = db.get_needs_repair()
        data = [
            [r["name"], r["model"] or "—", r["serial_number"] or "—", r["status"]]
            for r in rows
        ]
        return _wrap("Instruments Needing Repair",
                     _table(["Instrument", "Model", "Serial #", "Status"],
                            data, "No instruments currently flagged for repair."))

    if key == "available":
        rows = db.get_available_instruments()
        data = [
            [r["name"], r["model"] or "—", r["serial_number"] or "—",
             r["last_checked_in"] or "—"]
            for r in rows
        ]
        return _wrap("Available Instruments",
                     _table(["Instrument", "Model", "Serial #", "Last Checked In"],
                            data, "No instruments currently available."))

    return ""


# ── Dialog ────────────────────────────────────────────────────────────────────

class ReportsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Print Reports")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(8)

        lbl = QLabel("Choose a report to print:")
        lbl.setObjectName("section_title")
        layout.addWidget(lbl)

        for key, title, desc in REPORTS:
            card = _ReportCard(title, desc, self)
            card.clicked.connect(lambda k=key: self._print_report(k))
            layout.addWidget(card)

        layout.addSpacing(6)
        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(34)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _print_report(self, key):
        html = _build_html(key)
        if not html:
            return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)

        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.Accepted:
            return

        doc = QTextDocument()
        doc.setHtml(html)
        doc.print_(printer)
