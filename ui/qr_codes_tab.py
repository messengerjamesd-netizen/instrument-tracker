import io

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QMessageBox, QCheckBox, QScrollArea,
    QFrame, QComboBox,
)
from PySide6.QtCore import Qt

import database as db

# Avery 22816: 2"x2" square, 3 cols x 4 rows = 12 per sheet on US Letter
# Margins verified from compatible 12-up 2"x2" template spec
_AVERY_22816 = {
    "cols": 3,
    "rows": 4,
    "label_w": 2.0,       # inches
    "label_h": 2.0,
    "left_margin": 0.625,
    "top_margin": 0.600,
    "col_gap": 0.625,     # horizontal gap between labels
    "row_gap": 0.600,     # vertical gap between labels
}


class QRCodesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkboxes = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Print QR Codes")
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(self._build_options_group())
        layout.addWidget(self._build_list_group(), 1)
        layout.addWidget(self._build_export_group())

    def _build_options_group(self):
        group = QGroupBox("Options")
        h = QHBoxLayout(group)

        h.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Standard grid",
            "Avery 22816  (2”×2” stickers, 12/sheet)",
        ])
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        h.addWidget(self.format_combo)

        h.addSpacing(24)
        h.addWidget(QLabel("QR Content:"))
        self.qr_content_combo = QComboBox()
        self.qr_content_combo.addItems([
            "QR Code Text field (falls back to Serial Number)",
            "Serial Number only",
        ])
        h.addWidget(self.qr_content_combo)

        h.addSpacing(24)
        self.cols_label = QLabel("Columns per page:")
        h.addWidget(self.cols_label)
        self.columns_combo = QComboBox()
        self.columns_combo.addItems(["2", "3", "4"])
        self.columns_combo.setCurrentIndex(1)
        h.addWidget(self.columns_combo)

        h.addStretch()
        return group

    def _on_format_changed(self, index):
        avery = index == 1
        self.cols_label.setVisible(not avery)
        self.columns_combo.setVisible(not avery)

    def _build_list_group(self):
        group = QGroupBox("Select Instruments")
        v = QVBoxLayout(group)

        btn_row = QHBoxLayout()
        all_btn = QPushButton("Select All")
        all_btn.clicked.connect(self._select_all)
        none_btn = QPushButton("Deselect All")
        none_btn.clicked.connect(self._deselect_all)
        btn_row.addWidget(all_btn)
        btn_row.addWidget(none_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        v.addWidget(scroll)
        return group

    def _build_export_group(self):
        group = QGroupBox("Export")
        h = QHBoxLayout(group)

        pdf_btn = QPushButton("Save as PDF")
        pdf_btn.setObjectName("primary")
        pdf_btn.setMinimumHeight(38)
        pdf_btn.clicked.connect(self._export_pdf)
        h.addWidget(pdf_btn)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        h.addWidget(self.status_label)
        h.addStretch()
        return group

    def refresh(self):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._checkboxes.clear()

        instruments = db.get_all_instruments()
        for instr in instruments:
            parts = [instr["name"]]
            if instr["model"]:
                parts.append(instr["model"])
            if instr["serial_number"]:
                parts.append(f"S/N: {instr['serial_number']}")
            cb = QCheckBox("  —  ".join(parts))
            cb.setChecked(True)
            self._list_layout.addWidget(cb)
            self._checkboxes.append((cb, instr))

        self._list_layout.addStretch()

    def _select_all(self):
        for cb, _ in self._checkboxes:
            cb.setChecked(True)

    def _deselect_all(self):
        for cb, _ in self._checkboxes:
            cb.setChecked(False)

    def _qr_text_for(self, instr):
        if self.qr_content_combo.currentIndex() == 0:
            return instr["qr_code_text"] or instr["serial_number"] or str(instr["id"])
        return instr["serial_number"] or instr["qr_code_text"] or str(instr["id"])

    def _export_pdf(self):
        selected = [instr for cb, instr in self._checkboxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select at least one instrument.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save QR Codes PDF", "instrument_qr_codes.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return

        try:
            if self.format_combo.currentIndex() == 1:
                self._generate_avery_22816(path, selected)
            else:
                self._generate_grid_pdf(path, selected)
            self.status_label.setText(f"Saved {len(selected)} QR codes.")
            QMessageBox.information(self, "Done", f"PDF saved:\n{path}")
        except ImportError as e:
            QMessageBox.critical(
                self, "Missing Library",
                f"Required library not installed:\n{e}\n\nRun: pip install qrcode[pil] reportlab",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{e}")

    # ── Standard grid ─────────────────────────────────────────────────────────

    def _generate_grid_pdf(self, path, instruments):
        import qrcode
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.utils import ImageReader

        cols = int(self.columns_combo.currentText())
        page_w, page_h = letter
        margin = 0.4 * inch
        gap = 0.15 * inch

        cell_w = (page_w - 2 * margin - gap * (cols - 1)) / cols
        qr_size = cell_w - 0.2 * inch
        label_h = 0.6 * inch
        cell_h = qr_size + label_h + 0.1 * inch

        c = rl_canvas.Canvas(path, pagesize=letter)
        x_starts = [margin + i * (cell_w + gap) for i in range(cols)]
        y = page_h - margin
        col_idx = 0

        for instr in instruments:
            qr_text = self._qr_text_for(instr)
            if not qr_text:
                continue
            if col_idx == 0:
                if y - cell_h < margin:
                    c.showPage()
                    y = page_h - margin
                y -= cell_h
            x = x_starts[col_idx]
            c.setStrokeColor(colors.lightgrey)
            c.setLineWidth(0.5)
            c.rect(x, y, cell_w, cell_h)
            self._draw_qr_cell(c, instr, qr_text, x, y, cell_w, qr_size, label_h, inch)
            col_idx = (col_idx + 1) % cols

        c.save()

    # ── Avery 22816 ───────────────────────────────────────────────────────────

    def _generate_avery_22816(self, path, instruments):
        import qrcode
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.utils import ImageReader

        s = _AVERY_22816
        page_w, page_h = letter

        label_w = s["label_w"] * inch
        label_h = s["label_h"] * inch
        left_m  = s["left_margin"] * inch
        top_m   = s["top_margin"] * inch
        col_gap = s["col_gap"] * inch
        row_gap = s["row_gap"] * inch
        cols    = s["cols"]

        # Pre-compute x positions (left edge of each column)
        x_starts = [left_m + i * (label_w + col_gap) for i in range(cols)]

        # Pre-compute y positions (bottom edge of each row, top-to-bottom order)
        y_starts = [page_h - top_m - (r + 1) * label_h - r * row_gap
                    for r in range(s["rows"])]

        # QR image occupies most of the 2"x2" cell; leave ~0.45" at bottom for text
        text_h  = 0.45 * inch
        qr_size = label_w - 0.15 * inch   # slight inset so QR isn't edge-to-edge

        c = rl_canvas.Canvas(path, pagesize=letter)
        pos = 0   # flat index into the grid positions

        for instr in instruments:
            qr_text = self._qr_text_for(instr)
            if not qr_text:
                continue

            if pos > 0 and pos % (cols * s["rows"]) == 0:
                c.showPage()

            slot  = pos % (cols * s["rows"])
            row   = slot // cols
            col   = slot % cols

            x = x_starts[col]
            y = y_starts[row]

            # Dashed cut guide
            c.setStrokeColor(colors.Color(0.75, 0.75, 0.75))
            c.setLineWidth(0.3)
            c.setDash(2, 3)
            c.rect(x, y, label_w, label_h)
            c.setDash()   # reset

            self._draw_qr_cell(c, instr, qr_text, x, y, label_w, qr_size, text_h, inch)
            pos += 1

        c.save()

    # ── Shared cell drawing ────────────────────────────────────────────────────

    def _draw_qr_cell(self, c, instr, qr_text, x, y, cell_w, qr_size, label_h, inch):
        import qrcode
        from reportlab.lib import colors
        from reportlab.lib.utils import ImageReader

        qr = qrcode.QRCode(border=1)
        qr.add_data(qr_text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        qr_x = x + (cell_w - qr_size) / 2
        qr_y = y + label_h + 0.04 * inch
        c.drawImage(ImageReader(buf), qr_x, qr_y, qr_size, qr_size)

        c.setFillColor(colors.black)
        tx = x + 0.07 * inch

        name   = instr["name"] or ""
        model  = instr["model"] or ""
        serial = instr["serial_number"] or ""
        line1  = name + (f"  —  {model}" if model else "")

        c.setFont("Helvetica-Bold", 7)
        c.drawString(tx, y + 0.28 * inch, line1[:60])
        if serial:
            c.setFont("Helvetica", 6.5)
            c.drawString(tx, y + 0.13 * inch, f"S/N: {serial}")
