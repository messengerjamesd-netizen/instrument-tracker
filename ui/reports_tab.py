from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QMessageBox, QDialog, QSizePolicy,
)
from PySide6.QtGui import QTextDocument, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

import database as db


# ── HTML report builders (shared with reports_dialog) ─────────────────────────

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

    if key == "summer_hold":
        rows = db.get_summer_hold_instruments()
        data = [
            [r["name"], r["model"] or "—", r["serial_number"] or "—",
             r["student_name"] or "—"]
            for r in rows
        ]
        return _wrap("Summer Hold — Instruments at Home",
                     _table(["Instrument", "Model", "Serial #", "Student"],
                            data, "No instruments currently marked Summer Hold."))

    return ""


def _print_html(html, parent):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    dlg = QPrintDialog(printer, parent)
    if dlg.exec() != QDialog.Accepted:
        return
    doc = QTextDocument()
    doc.setHtml(html)
    doc.print_(printer)


# ── Reports page ──────────────────────────────────────────────────────────────

class ReportsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Reports")
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(self._build_export_group())
        layout.addWidget(self._build_print_group())
        layout.addWidget(self._build_qr_group())
        layout.addStretch()

    # ── Export Data ───────────────────────────────────────────────────────────

    def _build_export_group(self):
        group = QGroupBox("Export Data")
        h = QHBoxLayout(group)
        h.setSpacing(10)

        instr_btn = QPushButton("🎺  Export Instruments")
        instr_btn.setMinimumHeight(52)
        instr_btn.setMinimumWidth(160)
        instr_btn.clicked.connect(self._export_instruments)
        h.addWidget(instr_btn)

        stu_btn = QPushButton("🎓  Export Students")
        stu_btn.setMinimumHeight(52)
        stu_btn.setMinimumWidth(160)
        stu_btn.clicked.connect(self._export_students)
        h.addWidget(stu_btn)

        h.addStretch()
        return group

    def _export_instruments(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Instruments CSV", "instruments.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            count = db.export_instruments_to_csv(path)
            QMessageBox.information(self, "Export Complete", f"Exported {count} instruments.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _export_students(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Students CSV", "students.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            count = db.export_students_to_csv(path)
            QMessageBox.information(self, "Export Complete", f"Exported {count} students.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    # ── Print Reports ─────────────────────────────────────────────────────────

    def _build_print_group(self):
        group = QGroupBox("Print Reports")
        h = QHBoxLayout(group)
        h.setSpacing(10)

        reports = [
            ("📋", "Current Checkouts", "current_checkouts"),
            ("📦", "Full Inventory", "full_inventory"),
            ("🔧", "Needs Repair", "needs_repair"),
            ("✅", "Available", "available"),
            ("🏠", "Summer Hold", "summer_hold"),
        ]
        for icon, label, key in reports:
            btn = QPushButton(f"{icon}  {label}")
            btn.setMinimumHeight(52)
            btn.setMinimumWidth(140)
            btn.clicked.connect(lambda _, k=key: self._print_report(k))
            h.addWidget(btn)

        h.addStretch()
        return group

    def _print_report(self, key):
        html = _build_html(key)
        if html:
            _print_html(html, self)

    # ── QR Labels ─────────────────────────────────────────────────────────────

    def _build_qr_group(self):
        group = QGroupBox("QR Codes")
        h = QHBoxLayout(group)
        h.setSpacing(10)

        qr_btn = QPushButton("▦  Print QR Labels")
        qr_btn.setMinimumHeight(52)
        qr_btn.setMinimumWidth(160)
        qr_btn.clicked.connect(self._open_qr_labels)
        h.addWidget(qr_btn)

        h.addStretch()
        return group

    def _open_qr_labels(self):
        from ui.qr_codes_tab import QRCodesTab

        dlg = QDialog(self)
        dlg.setWindowTitle("Print QR Labels")
        dlg.setMinimumSize(560, 540)

        v = QVBoxLayout(dlg)
        v.setContentsMargins(0, 0, 0, 8)

        tab = QRCodesTab()
        tab.refresh()
        v.addWidget(tab)

        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(34)
        close_btn.clicked.connect(dlg.reject)
        v.addWidget(close_btn, alignment=Qt.AlignRight)

        dlg.exec()
