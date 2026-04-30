import io
import os
import tempfile

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QMessageBox, QCheckBox, QScrollArea,
    QFrame, QComboBox, QColorDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

import database as db

# Avery 22816: 2"x2" square, 3 cols x 4 rows = 12 per sheet on US Letter
_AVERY_22816 = {
    "cols": 3,
    "rows": 4,
    "label_w": 2.0,
    "label_h": 2.0,
    "left_margin": 0.625,
    "top_margin": 0.600,
    "col_gap": 0.625,
    "row_gap": 0.600,
}

_SIZE_INCHES = [0.75, 1.0, 1.25, 1.5, 2.0, 2.5]
_SIZE_LABELS = ['¾"', '1"', '1¼"', '1½"', '2"', '2½"']
_QR_STYLES   = ["Square", "Rounded", "Circles", "Gapped"]

_PREVIEW_PX = 180   # preview image area size in pixels


class QRCodesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkboxes = []
        self._qr_color = "#000000"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Print Codes")
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(self._build_options_group())

        # Middle row: instrument list (flex) + preview panel (fixed)
        mid = QHBoxLayout()
        mid.setSpacing(12)
        mid.addWidget(self._build_list_group(), 1)
        mid.addWidget(self._build_preview_panel())
        layout.addLayout(mid, 1)

        layout.addWidget(self._build_export_group())

    # ── Options ───────────────────────────────────────────────────────────────

    def _build_options_group(self):
        group = QGroupBox("Options")
        h = QHBoxLayout(group)

        h.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Standard grid",
            "Avery 22816  (2″×2″ stickers, 12/sheet)",
        ])
        h.addWidget(self.format_combo)

        h.addSpacing(20)
        self.type_label = QLabel("Code type:")
        h.addWidget(self.type_label)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["QR Code", "Barcode (Code 128)"])
        h.addWidget(self.type_combo)

        h.addSpacing(20)
        self.style_label = QLabel("QR style:")
        h.addWidget(self.style_label)
        self.style_combo = QComboBox()
        self.style_combo.addItems(_QR_STYLES)
        h.addWidget(self.style_combo)

        h.addSpacing(12)
        self.color_label = QLabel("Color:")
        h.addWidget(self.color_label)
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(32, 24)
        self.color_btn.setToolTip("Choose QR code color")
        self.color_btn.clicked.connect(self._pick_color)
        self._apply_color_btn_style()
        h.addWidget(self.color_btn)

        h.addSpacing(20)
        self.size_label = QLabel("Size:")
        h.addWidget(self.size_label)
        self.size_combo = QComboBox()
        self.size_combo.addItems(_SIZE_LABELS)
        self.size_combo.setCurrentIndex(2)  # default 1.25"
        h.addWidget(self.size_combo)

        h.addStretch()

        self.format_combo.currentIndexChanged.connect(self._on_options_changed)
        self.type_combo.currentIndexChanged.connect(self._on_options_changed)
        self.style_combo.currentIndexChanged.connect(self._on_options_changed)
        self.size_combo.currentIndexChanged.connect(self._on_options_changed)
        self.color_btn.clicked.connect(self._pick_color)

        self._update_option_visibility()
        return group

    def _on_options_changed(self):
        self._update_option_visibility()
        self._update_preview()

    def _update_option_visibility(self):
        avery = self.format_combo.currentIndex() == 1
        is_qr = avery or self.type_combo.currentIndex() == 0
        self.type_label.setVisible(not avery)
        self.type_combo.setVisible(not avery)
        self.size_label.setVisible(not avery)
        self.size_combo.setVisible(not avery)
        self.style_label.setVisible(not avery and is_qr)
        self.style_combo.setVisible(not avery and is_qr)
        self.color_label.setVisible(True)
        self.color_btn.setVisible(True)
        self.size_label.setText("QR code size:" if is_qr else "Bar height:")

    def _pick_color(self):
        is_qr = self.type_combo.currentIndex() == 0
        title = "Choose QR Code Color" if is_qr else "Choose Barcode Color"
        color = QColorDialog.getColor(QColor(self._qr_color), self, title)
        if color.isValid():
            self._qr_color = color.name()
            self._apply_color_btn_style()
            self._update_preview()

    def _apply_color_btn_style(self):
        self.color_btn.setStyleSheet(
            f"background-color: {self._qr_color}; border: 1px solid #888; border-radius: 3px;"
        )

    # ── Instrument list ───────────────────────────────────────────────────────

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

    # ── Preview panel ─────────────────────────────────────────────────────────

    def _build_preview_panel(self):
        panel = QGroupBox("Preview")
        v = QVBoxLayout(panel)
        panel.setFixedWidth(220)

        self._preview_img = QLabel()
        self._preview_img.setFixedSize(_PREVIEW_PX, _PREVIEW_PX)
        self._preview_img.setAlignment(Qt.AlignCenter)
        self._preview_img.setStyleSheet(
            "background: white; border: 1px solid #c0c8d8; border-radius: 4px;"
        )
        self._preview_img.setText("Select an\ninstrument")
        v.addWidget(self._preview_img, alignment=Qt.AlignHCenter)

        self._preview_info = QLabel("")
        self._preview_info.setAlignment(Qt.AlignCenter)
        self._preview_info.setStyleSheet("color: #5a7aaa; font-size: 11px;")
        self._preview_info.setWordWrap(True)
        v.addWidget(self._preview_info)

        v.addStretch()
        return panel

    def _update_preview(self):
        serial = self._preview_serial()
        if not serial:
            self._preview_img.setPixmap(QPixmap())
            self._preview_img.setText("No serial\nnumber found")
            self._preview_info.setText("")
            return

        try:
            is_barcode = self.type_combo.currentIndex() == 1
            if is_barcode:
                pixmap = self._render_barcode_preview(serial, self._qr_color)
                info = f"Code 128\nS/N: {serial}"
            else:
                style_idx = self.style_combo.currentIndex()
                pixmap = self._render_qr_preview(serial, style_idx, self._qr_color)
                avery = self.format_combo.currentIndex() == 1
                size_str = '2"' if avery else _SIZE_LABELS[self.size_combo.currentIndex()]
                info = f"{_QR_STYLES[style_idx]} · {size_str}\nS/N: {serial}"

            self._preview_img.setText("")
            self._preview_img.setPixmap(
                pixmap.scaled(_PREVIEW_PX, _PREVIEW_PX,
                              Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self._preview_info.setText(info)
        except Exception as e:
            self._preview_img.setPixmap(QPixmap())
            self._preview_img.setText("Preview\nunavailable")
            self._preview_info.setText(str(e)[:60])

    def _preview_serial(self):
        for cb, instr in self._checkboxes:
            if instr["serial_number"]:
                return instr["serial_number"]
        return ""

    def _render_qr_preview(self, serial, style_idx, color="#000000"):
        import qrcode
        qr = qrcode.QRCode(border=2)
        qr.add_data(serial)
        qr.make(fit=True)

        if style_idx == 0:
            img = qr.make_image(fill_color=color, back_color="white")
        else:
            from qrcode.image.styledimage import StyledPilImage
            from qrcode.image.styles.moduledrawers import (
                RoundedModuleDrawer, CircleModuleDrawer, GappedSquareModuleDrawer,
            )
            drawer = [None,
                      RoundedModuleDrawer(),
                      CircleModuleDrawer(),
                      GappedSquareModuleDrawer()][style_idx]
            img = qr.make_image(image_factory=StyledPilImage, module_drawer=drawer,
                                fill_color=color, back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        px = QPixmap()
        px.loadFromData(buf.read())
        return px

    def _render_barcode_preview(self, serial, color="#000000"):
        from reportlab.graphics.barcode import code128
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics import renderPM
        from reportlab.lib.colors import HexColor

        bar_h = 60
        bc = code128.Code128(serial, barWidth=1.8, barHeight=bar_h,
                             humanReadable=True, barColor=HexColor(color))
        d = Drawing(bc.width, bar_h + 22)
        d.add(bc)
        png_bytes = renderPM.drawToString(d, fmt="PNG", dpi=150)
        px = QPixmap()
        px.loadFromData(png_bytes)
        return px

    # ── Export group ──────────────────────────────────────────────────────────

    def _build_export_group(self):
        group = QGroupBox("Export")
        h = QHBoxLayout(group)

        print_btn = QPushButton("🖨  Print")
        print_btn.setObjectName("primary")
        print_btn.setMinimumHeight(38)
        print_btn.clicked.connect(self._print_codes)
        h.addWidget(print_btn)

        pdf_btn = QPushButton("Save as PDF")
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

        for instr in db.get_all_instruments():
            parts = [instr["name"]]
            if instr["model"]:
                parts.append(instr["model"])
            has_serial = bool(instr["serial_number"])
            if has_serial:
                parts.append(f"S/N: {instr['serial_number']}")
            label = "  —  ".join(parts)
            if not has_serial:
                label += "  (no serial — skipped)"
            cb = QCheckBox(label)
            cb.setChecked(has_serial)
            cb.setEnabled(has_serial)
            self._list_layout.addWidget(cb)
            self._checkboxes.append((cb, instr))

        self._list_layout.addStretch()
        self._update_preview()

    def _select_all(self):
        for cb, instr in self._checkboxes:
            if instr["serial_number"]:
                cb.setChecked(True)

    def _deselect_all(self):
        for cb, _ in self._checkboxes:
            cb.setChecked(False)

    def _serial_for(self, instr):
        return instr["serial_number"] or ""

    # ── Generate / export ─────────────────────────────────────────────────────

    def _generate(self, path):
        selected = [instr for cb, instr in self._checkboxes
                    if cb.isChecked() and instr["serial_number"]]
        if not selected:
            QMessageBox.warning(self, "No Selection",
                                "No instruments with serial numbers are selected.")
            return False
        if self.format_combo.currentIndex() == 1:
            self._generate_avery_22816(path, selected)
        else:
            self._generate_grid_pdf(path, selected)
        return True

    def _print_codes(self):
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.close()
            if self._generate(tmp.name):
                os.startfile(tmp.name, "print")
        except ImportError as e:
            QMessageBox.critical(self, "Missing Library",
                                 f"Required library not installed:\n{e}\n\n"
                                 "Run: pip install qrcode[pil] reportlab")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate print file:\n{e}")

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", "instrument_codes.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            if self._generate(path):
                self.status_label.setText("Saved.")
                QMessageBox.information(self, "Done", f"PDF saved:\n{path}")
        except ImportError as e:
            QMessageBox.critical(self, "Missing Library",
                                 f"Required library not installed:\n{e}\n\n"
                                 "Run: pip install qrcode[pil] reportlab")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{e}")

    # ── Standard grid ─────────────────────────────────────────────────────────

    def _generate_grid_pdf(self, path, instruments):
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as rl_canvas

        is_barcode = self.type_combo.currentIndex() == 1
        size_in    = _SIZE_INCHES[self.size_combo.currentIndex()]
        page_w, page_h = letter
        margin  = 0.4 * inch
        gap     = 0.15 * inch
        label_h = 0.55 * inch

        if is_barcode:
            bar_h  = size_in * inch
            cell_w = (page_w - 2 * margin - gap) / 2
            cell_h = bar_h + label_h + 0.15 * inch
            cols   = 2
        else:
            qr_size = size_in * inch
            cell_w  = qr_size + 0.2 * inch
            cell_h  = qr_size + label_h + 0.1 * inch
            cols    = max(1, int((page_w - 2 * margin + gap) / (cell_w + gap)))

        x_starts = [margin + i * (cell_w + gap) for i in range(cols)]
        c = rl_canvas.Canvas(path, pagesize=letter)
        y = page_h - margin
        col_idx = 0

        for instr in instruments:
            serial = self._serial_for(instr)
            if not serial:
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
            if is_barcode:
                self._draw_barcode_cell(c, instr, serial, x, y, cell_w,
                                        bar_h, label_h, inch, self._qr_color)
            else:
                self._draw_qr_cell(c, instr, serial, x, y, cell_w,
                                   size_in * inch, label_h, inch,
                                   self.style_combo.currentIndex(),
                                   self._qr_color)
            col_idx = (col_idx + 1) % cols

        c.save()

    # ── Avery 22816 ───────────────────────────────────────────────────────────

    def _generate_avery_22816(self, path, instruments):
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as rl_canvas

        s = _AVERY_22816
        page_w, page_h = letter
        label_w = s["label_w"] * inch
        label_h = s["label_h"] * inch
        left_m  = s["left_margin"] * inch
        top_m   = s["top_margin"] * inch
        col_gap = s["col_gap"] * inch
        row_gap = s["row_gap"] * inch
        cols    = s["cols"]

        x_starts = [left_m + i * (label_w + col_gap) for i in range(cols)]
        y_starts = [page_h - top_m - (r + 1) * label_h - r * row_gap
                    for r in range(s["rows"])]

        text_h  = 0.45 * inch
        qr_size = label_w - 0.15 * inch

        c = rl_canvas.Canvas(path, pagesize=letter)
        pos = 0

        for instr in instruments:
            serial = self._serial_for(instr)
            if not serial:
                continue
            if pos > 0 and pos % (cols * s["rows"]) == 0:
                c.showPage()
            slot = pos % (cols * s["rows"])
            x = x_starts[slot % cols]
            y = y_starts[slot // cols]

            c.setStrokeColor(colors.Color(0.75, 0.75, 0.75))
            c.setLineWidth(0.3)
            c.setDash(2, 3)
            c.rect(x, y, label_w, label_h)
            c.setDash()

            self._draw_qr_cell(c, instr, serial, x, y, label_w,
                               qr_size, text_h, inch, style_idx=0,
                               color=self._qr_color)
            pos += 1

        c.save()

    # ── Cell drawing ──────────────────────────────────────────────────────────

    def _draw_qr_cell(self, c, instr, serial, x, y, cell_w,
                      qr_size, label_h, inch, style_idx=0, color="#000000"):
        import qrcode
        from reportlab.lib.utils import ImageReader

        qr = qrcode.QRCode(border=1)
        qr.add_data(serial)
        qr.make(fit=True)

        if style_idx == 0:
            img = qr.make_image(fill_color=color, back_color="white")
        else:
            from qrcode.image.styledimage import StyledPilImage
            from qrcode.image.styles.moduledrawers import (
                RoundedModuleDrawer, CircleModuleDrawer, GappedSquareModuleDrawer,
            )
            drawer = [None,
                      RoundedModuleDrawer(),
                      CircleModuleDrawer(),
                      GappedSquareModuleDrawer()][style_idx]
            img = qr.make_image(image_factory=StyledPilImage, module_drawer=drawer,
                                fill_color=color, back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        qr_x = x + (cell_w - qr_size) / 2
        qr_y = y + label_h + 0.04 * inch
        c.drawImage(ImageReader(buf), qr_x, qr_y, qr_size, qr_size)
        self._draw_label_text(c, instr, serial, x, y, inch)

    def _draw_barcode_cell(self, c, instr, serial, x, y, cell_w,
                           bar_h, label_h, inch, color="#000000"):
        from reportlab.graphics.barcode import code128
        from reportlab.lib.colors import HexColor

        target_w    = cell_w - 0.2 * inch
        est_modules = max(1, 11 * len(serial) + 35)
        bar_w       = max(0.008 * inch, target_w / est_modules)

        bc = code128.Code128(serial, barWidth=bar_w, barHeight=bar_h,
                             humanReadable=False, barColor=HexColor(color))
        bc_x = x + (cell_w - bc.width) / 2
        bc_y = y + label_h + 0.04 * inch
        bc.drawOn(c, bc_x, bc_y)
        self._draw_label_text(c, instr, serial, x, y, inch)

    def _draw_label_text(self, c, instr, serial, x, y, inch):
        from reportlab.lib import colors
        c.setFillColor(colors.black)
        tx    = x + 0.07 * inch
        name  = instr["name"] or ""
        model = instr["model"] or ""
        line1 = name + (f"  —  {model}" if model else "")
        c.setFont("Helvetica-Bold", 7)
        c.drawString(tx, y + 0.28 * inch, line1[:60])
        c.setFont("Helvetica", 6.5)
        c.drawString(tx, y + 0.13 * inch, f"S/N: {serial}")
