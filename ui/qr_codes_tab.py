import io
import json
import os
import tempfile

from PySide6.QtCore import Qt, Signal, QRect, QTimer
from PySide6.QtGui import QPixmap, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QMessageBox, QCheckBox, QScrollArea,
    QFrame, QComboBox, QColorDialog, QDialog, QDialogButtonBox,
    QLineEdit, QListWidget, QListWidgetItem,
)

import database as db

# ── Built-in label format database ───────────────────────────────────────────
# All measurements in inches for US Letter (8.5" × 11") paper.
# Layout math: left_margin + cols*label_w + (cols-1)*col_gap + right_margin = 8.5
#              top_margin  + rows*label_h + (rows-1)*row_gap + bot_margin   = 11.0

_BUILTIN_FORMATS = [
    # ── Square / inventory stickers ───────────────────────────────────────────
    {"name": "Avery 22816",
     "description": "Square stickers  •  2\" × 2\"  •  12/sheet  •  great for QR codes on cases",
     "cols": 3,  "rows": 4,  "label_w": 2.0,     "label_h": 2.0,
     "left_margin": 0.625,   "top_margin": 0.600,  "col_gap": 0.625,  "row_gap": 0.600},

    {"name": "1.5\" × 1.5\" Square",
     "description": "Small square  •  1½\" × 1½\"  •  30/sheet  •  common on Amazon for QR code inventory labels",
     "cols": 5,  "rows": 6,  "label_w": 1.5,     "label_h": 1.5,
     "left_margin": 0.5,     "top_margin": 1.0,    "col_gap": 0.0,    "row_gap": 0.0},

    {"name": "1\" × 1\" Square",
     "description": "Mini square  •  1\" × 1\"  •  80/sheet  •  barcodes and small QR codes; sold by many brands at Walmart/Amazon",
     "cols": 8,  "rows": 10, "label_w": 1.0,     "label_h": 1.0,
     "left_margin": 0.25,    "top_margin": 0.5,    "col_gap": 0.0,    "row_gap": 0.0},

    # ── Address / mailing labels ──────────────────────────────────────────────
    # Avery 5160 / 5260 / 5960 / 8160 / 8460 all share this layout.
    # Also sold as: Maco ML-1000, SJPACK, Printworks, Amazon Basics, Staples, Office Depot,
    # Great Value (Walmart), Uline S-19402 — virtually every generic address label.
    {"name": "Avery 5160",
     "description": "Address  •  2⅝\" × 1\"  •  30/sheet  •  most widely used label size; compatible with 5260, 8160, Maco ML-1000, SJPACK, Amazon Basics, Great Value",
     "cols": 3,  "rows": 10, "label_w": 2.625,   "label_h": 1.0,
     "left_margin": 0.1875,  "top_margin": 0.5,   "col_gap": 0.125,  "row_gap": 0.0},

    {"name": "Avery 5260",
     "description": "Address EasyPeel  •  2⅝\" × 1\"  •  30/sheet  •  same layout as 5160",
     "cols": 3,  "rows": 10, "label_w": 2.625,   "label_h": 1.0,
     "left_margin": 0.1875,  "top_margin": 0.5,   "col_gap": 0.125,  "row_gap": 0.0},

    {"name": "Avery 8160",
     "description": "Address inkjet  •  2⅝\" × 1\"  •  30/sheet  •  same layout as 5160",
     "cols": 3,  "rows": 10, "label_w": 2.625,   "label_h": 1.0,
     "left_margin": 0.1875,  "top_margin": 0.5,   "col_gap": 0.125,  "row_gap": 0.0},

    {"name": "Avery 5161",
     "description": "Address  •  4\" × 1\"  •  20/sheet",
     "cols": 2,  "rows": 10, "label_w": 4.0,     "label_h": 1.0,
     "left_margin": 0.15625, "top_margin": 0.5,   "col_gap": 0.1875, "row_gap": 0.0},

    {"name": "Avery 8161",
     "description": "Address inkjet  •  4\" × 1\"  •  20/sheet  •  same layout as 5161",
     "cols": 2,  "rows": 10, "label_w": 4.0,     "label_h": 1.0,
     "left_margin": 0.15625, "top_margin": 0.5,   "col_gap": 0.1875, "row_gap": 0.0},

    {"name": "Avery 5162",
     "description": "Address  •  4\" × 1⅓\"  •  14/sheet",
     "cols": 2,  "rows": 7,  "label_w": 4.0,     "label_h": 1.333,
     "left_margin": 0.15625, "top_margin": 0.833, "col_gap": 0.1875, "row_gap": 0.0},

    {"name": "Avery 8162",
     "description": "Address inkjet  •  4\" × 1⅓\"  •  14/sheet  •  same layout as 5162",
     "cols": 2,  "rows": 7,  "label_w": 4.0,     "label_h": 1.333,
     "left_margin": 0.15625, "top_margin": 0.833, "col_gap": 0.1875, "row_gap": 0.0},

    {"name": "Avery 5195",
     "description": "Small / inventory  •  2½\" × ¾\"  •  39/sheet  •  good for narrow barcodes on small items",
     "cols": 3,  "rows": 13, "label_w": 2.5,     "label_h": 0.75,
     "left_margin": 0.25,    "top_margin": 0.625, "col_gap": 0.25,   "row_gap": 0.0},

    # ── Shipping labels ───────────────────────────────────────────────────────
    # Avery 5163 / 8163 / 5912 / 8912 all share this layout.
    # Also sold as: Maco ML-3000, Amazon Basics Shipping, Staples, Office Depot,
    # Great Value shipping, Uline S-12516, AIEX, Betckey, Yaroze.
    {"name": "Avery 5163",
     "description": "Shipping  •  4\" × 2\"  •  10/sheet  •  compatible with 8163, 5912, Maco ML-3000, Amazon Basics, most generic shipping labels",
     "cols": 2,  "rows": 5,  "label_w": 4.0,     "label_h": 2.0,
     "left_margin": 0.15625, "top_margin": 0.5,   "col_gap": 0.1875, "row_gap": 0.0},

    {"name": "Avery 8163",
     "description": "Shipping inkjet  •  4\" × 2\"  •  10/sheet  •  same layout as 5163",
     "cols": 2,  "rows": 5,  "label_w": 4.0,     "label_h": 2.0,
     "left_margin": 0.15625, "top_margin": 0.5,   "col_gap": 0.1875, "row_gap": 0.0},

    {"name": "Avery 5164",
     "description": "Large shipping  •  4\" × 3⅓\"  •  6/sheet  •  compatible with Uline S-11965, WorldLabel WL-875",
     "cols": 2,  "rows": 3,  "label_w": 4.0,     "label_h": 3.333,
     "left_margin": 0.25,    "top_margin": 0.5,   "col_gap": 0.0,    "row_gap": 0.0},

    {"name": "Half Sheet Shipping Labels",
     "description": "Large shipping / packing slip  •  5½\" × 8½\"  •  2/sheet  •  best seller on Amazon; works in all inkjet & laser printers; sold by MFLABEL, Envelopes.com, and dozens of others",
     "cols": 1,  "rows": 2,  "label_w": 8.5,     "label_h": 5.5,
     "left_margin": 0.0,     "top_margin": 0.0,   "col_gap": 0.0,    "row_gap": 0.0},

    {"name": "Quarter Sheet Labels",
     "description": "Medium shipping / product  •  4¼\" × 5½\"  •  4/sheet  •  common on Amazon and at Walmart",
     "cols": 2,  "rows": 2,  "label_w": 4.25,    "label_h": 5.5,
     "left_margin": 0.0,     "top_margin": 0.0,   "col_gap": 0.0,    "row_gap": 0.0},

    {"name": "Full Sheet Label",
     "description": "Single full-page label  •  8½\" × 11\"  •  1/sheet  •  poster, single large QR code, or packing list",
     "cols": 1,  "rows": 1,  "label_w": 8.5,     "label_h": 11.0,
     "left_margin": 0.0,     "top_margin": 0.0,   "col_gap": 0.0,    "row_gap": 0.0},

    # ── Return address labels ─────────────────────────────────────────────────
    {"name": "Avery 5167",
     "description": "Return address  •  1¾\" × ½\"  •  80/sheet  •  also sold as Avery 8167",
     "cols": 4,  "rows": 20, "label_w": 1.75,    "label_h": 0.5,
     "left_margin": 0.28125, "top_margin": 0.5,   "col_gap": 0.3125, "row_gap": 0.0},

    {"name": "Avery 8167",
     "description": "Return address inkjet  •  1¾\" × ½\"  •  80/sheet  •  same layout as 5167",
     "cols": 4,  "rows": 20, "label_w": 1.75,    "label_h": 0.5,
     "left_margin": 0.28125, "top_margin": 0.5,   "col_gap": 0.3125, "row_gap": 0.0},

    # ── Business cards ────────────────────────────────────────────────────────
    {"name": "Avery 5371",
     "description": "Business cards  •  3½\" × 2\"  •  10/sheet  •  also 5376, 5877, 8371, 8376; sold by Staples, Office Depot, Amazon Basics",
     "cols": 2,  "rows": 5,  "label_w": 3.5,     "label_h": 2.0,
     "left_margin": 0.75,    "top_margin": 0.5,   "col_gap": 0.0,    "row_gap": 0.0},

    {"name": "Avery 5376",
     "description": "Business cards Clean Edge  •  3½\" × 2\"  •  10/sheet  •  same layout as 5371",
     "cols": 2,  "rows": 5,  "label_w": 3.5,     "label_h": 2.0,
     "left_margin": 0.75,    "top_margin": 0.5,   "col_gap": 0.0,    "row_gap": 0.0},

    # ── File folder labels ────────────────────────────────────────────────────
    {"name": "Avery 5366",
     "description": "File folder  •  3⁷⁄₁₆\" × ⅔\"  •  30/sheet",
     "cols": 2,  "rows": 15, "label_w": 3.4375,  "label_h": 0.667,
     "left_margin": 0.5,     "top_margin": 0.5,   "col_gap": 0.625,  "row_gap": 0.0},

    # ── Other brands / generic equivalents ────────────────────────────────────
    {"name": "Maco ML-1000",
     "description": "Address (Maco / Walmart)  •  2⅝\" × 1\"  •  30/sheet  •  same layout as Avery 5160; widely available at Walmart",
     "cols": 3,  "rows": 10, "label_w": 2.625,   "label_h": 1.0,
     "left_margin": 0.1875,  "top_margin": 0.5,   "col_gap": 0.125,  "row_gap": 0.0},

    {"name": "Maco ML-3000",
     "description": "Shipping (Maco / Walmart)  •  4\" × 2\"  •  10/sheet  •  same layout as Avery 5163; widely available at Walmart",
     "cols": 2,  "rows": 5,  "label_w": 4.0,     "label_h": 2.0,
     "left_margin": 0.15625, "top_margin": 0.5,   "col_gap": 0.1875, "row_gap": 0.0},

    {"name": "Uline S-19402",
     "description": "Address (Uline)  •  2⅝\" × 1\"  •  30/sheet  •  same layout as Avery 5160",
     "cols": 3,  "rows": 10, "label_w": 2.625,   "label_h": 1.0,
     "left_margin": 0.1875,  "top_margin": 0.5,   "col_gap": 0.125,  "row_gap": 0.0},

    {"name": "Uline S-12516",
     "description": "Shipping (Uline)  •  4\" × 2\"  •  10/sheet  •  same layout as Avery 5163",
     "cols": 2,  "rows": 5,  "label_w": 4.0,     "label_h": 2.0,
     "left_margin": 0.15625, "top_margin": 0.5,   "col_gap": 0.1875, "row_gap": 0.0},

    {"name": "3\" × 1\" Barcode Labels",
     "description": "Barcode / inventory  •  3\" × 1\"  •  20/sheet  •  good for narrow barcodes; sold by various brands on Amazon",
     "cols": 2,  "rows": 10, "label_w": 3.0,     "label_h": 1.0,
     "left_margin": 1.0,     "top_margin": 0.5,   "col_gap": 0.5,    "row_gap": 0.0},

    {"name": "WorldLabel WL-875",
     "description": "Large label (WorldLabel / OnlineLabels)  •  4\" × 3⅓\"  •  6/sheet  •  same layout as Avery 5164",
     "cols": 2,  "rows": 3,  "label_w": 4.0,     "label_h": 3.333,
     "left_margin": 0.25,    "top_margin": 0.5,   "col_gap": 0.0,    "row_gap": 0.0},
]


def _get_user_formats_path():
    import database as db
    return os.path.join(os.path.dirname(db.get_db_path()), "label_formats.json")


_SIZE_INCHES = [0.75, 1.0, 1.25, 1.5, 2.0, 2.5]
_SIZE_LABELS = ['¾"', '1"', '1¼"', '1½"', '2"', '2½"']
_QR_STYLES   = ["Square", "Rounded", "Circles", "Gapped"]

_PREVIEW_PX = 180   # preview image area width in pixels

# Code128B symbol table (indices 0-102 = data chars, 103=START A,
# 104=START B, 105=START C, 106=STOP)
_CODE128B_SYM = [
    "11011001100","11001101100","11001100110","10010011000","10010001100",
    "10001001100","10011001000","10011000100","10001100100","11001001000",
    "11001000100","11000100100","10110011100","10011011100","10011001110",
    "10111001100","10011101100","10011100110","11001110010","11001011100",
    "11001001110","11011100100","11001110100","11101101110","11101001100",
    "11100101100","11100100110","11101100100","11100110100","11100110010",
    "11011011000","11011000110","11000110110","10100011000","10001011000",
    "10001000110","10110001000","10001101000","10001100010","11010001000",
    "11000101000","11000100010","10110111000","10110001110","10001101110",
    "10111011000","10111000110","10001110110","11101110110","11010001110",
    "11000101110","11011101000","11011100010","11011101110","11101011000",
    "11101000110","11100010110","11101101000","11101100010","11100011010",
    "11101111010","11001000010","11110001010","10100110000","10100001100",
    "10010110000","10010000110","10000101100","10000100110","10110010000",
    "10110000100","10011010000","10011000010","10000110100","10000110010",
    "11000010010","11001010000","11110111010","11000010100","10001111010",
    "10100111100","10010111100","10010011110","10111100100","10011110100",
    "10011110010","11110100100","11110010100","11110010010","11011011110",
    "11011110110","11110110110","10101111000","10100011110","10001011110",
    "10111101000","10111100010","11110101000","11110100010","10111011110",
    "10111101110","11101011110","11110101110",
    "11010000100","11010010000","11010011100","1100011101011",
]


class AddLabelFormatDialog(QDialog):
    """Search the built-in label format database and pick one to add."""

    def __init__(self, already_added: set, parent=None):
        super().__init__(parent)
        self.selected_format = None
        self.setWindowTitle("Add Label Format")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Search by name or number (e.g. \"5160\", \"address\", \"shipping\"):"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Start typing to filter…")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_item_changed)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list, 1)

        self._detail = QLabel("")
        self._detail.setStyleSheet("color: #5a7aaa; font-size: 11px;")
        self._detail.setWordWrap(True)
        layout.addWidget(self._detail)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._ok_btn = btns.button(QDialogButtonBox.Ok)
        self._ok_btn.setEnabled(False)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._already_added = already_added
        self._filter("")
        self._search.setFocus()

    def _filter(self, text):
        self._list.clear()
        q = text.lower()
        for fmt in _BUILTIN_FORMATS:
            if q and q not in fmt["name"].lower() and q not in fmt["description"].lower():
                continue
            item = QListWidgetItem(f"{fmt['name']}  —  {fmt['description']}")
            item.setData(Qt.UserRole, fmt)
            if fmt["name"] in self._already_added:
                item.setForeground(QColor("#666688"))
                item.setText(item.text() + "  ✓ already added")
            self._list.addItem(item)
        self._ok_btn.setEnabled(False)
        self._detail.setText("")

    def _on_item_changed(self, item):
        if item is None:
            self._detail.setText("")
            self._ok_btn.setEnabled(False)
            return
        fmt = item.data(Qt.UserRole)
        already = fmt["name"] in self._already_added
        s = fmt
        self._detail.setText(
            f"Cols: {s['cols']}  •  Rows: {s['rows']}  •  "
            f"Label size: {s['label_w']}\" × {s['label_h']}\"  •  "
            f"Left margin: {s['left_margin']}\"  •  Top margin: {s['top_margin']}\"  •  "
            f"Col gap: {s['col_gap']}\"  •  Row gap: {s['row_gap']}\""
        )
        self._ok_btn.setEnabled(not already)

    def _on_double_click(self, item):
        fmt = item.data(Qt.UserRole)
        if fmt["name"] not in self._already_added:
            self._on_accept()

    def _on_accept(self):
        item = self._list.currentItem()
        if item is None:
            return
        fmt = item.data(Qt.UserRole)
        if fmt["name"] in self._already_added:
            return
        self.selected_format = fmt
        self.accept()


class _PillToggle(QWidget):
    """Compact pill-style toggle (no animation) for the preview panel."""
    toggled = Signal(int)

    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self._labels = labels
        self._selected = 0
        self.setFixedHeight(30)
        self.setCursor(Qt.PointingHandCursor)

    def selected(self):
        return self._selected

    def set_selected(self, idx, emit=True):
        if idx != self._selected:
            self._selected = idx
            self.update()
            if emit:
                self.toggled.emit(idx)

    def mousePressEvent(self, e):
        idx = 0 if e.position().x() < self.width() / 2 else 1
        self.set_selected(idx)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        track = QPainterPath()
        track.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 8, 8)
        p.fillPath(track, QColor("#0f2040"))
        p.setPen(QPen(QColor("#1a3666"), 1))
        p.drawPath(track)

        pw = r.width() / 2 - 4
        px_off = (r.width() / 2) * self._selected + 2
        pill = QPainterPath()
        pill.addRoundedRect(px_off, 3, pw, r.height() - 6, 6, 6)
        p.fillPath(pill, QColor("#1a4a8a"))
        p.setPen(Qt.NoPen)

        half = r.width() // 2
        for i, lbl in enumerate(self._labels):
            p.setPen(QColor("#ffffff" if i == self._selected else "#8aaad0"))
            p.setFont(self.font())
            p.drawText(QRect(i * half, 0, half, r.height()), Qt.AlignCenter, lbl)

        p.end()


class QRCodesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkboxes = []
        self._qr_color = "#000000"
        self._preview_mode = "single"
        # _format_specs[i] corresponds to format_combo index i+1 (index 0 = standard grid)
        self._format_specs = []
        self._format_names_added = set()
        self._load_user_formats()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Print Codes")
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(self._build_options_group())

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
        self.format_combo.addItem("Standard grid")
        for spec in self._format_specs:
            self.format_combo.addItem(self._format_combo_label(spec))
        h.addWidget(self.format_combo)
        add_fmt_btn = QPushButton("+")
        add_fmt_btn.setFixedSize(26, 26)
        add_fmt_btn.setToolTip("Add label format…")
        add_fmt_btn.setStyleSheet("QPushButton { color: #c8d8f0; font-weight: bold; padding: 0px; }")
        add_fmt_btn.clicked.connect(self._add_label_format)
        h.addWidget(add_fmt_btn)
        self._remove_fmt_btn = QPushButton("−")
        self._remove_fmt_btn.setFixedSize(26, 26)
        self._remove_fmt_btn.setToolTip("Remove this format from list")
        self._remove_fmt_btn.setStyleSheet("QPushButton { color: #c8d8f0; font-weight: bold; padding: 0px; }")
        self._remove_fmt_btn.setVisible(False)
        self._remove_fmt_btn.clicked.connect(self._remove_label_format)
        h.addWidget(self._remove_fmt_btn)
        self.format_combo.currentIndexChanged.connect(self._update_remove_btn)

        h.addSpacing(20)
        self.type_label = QLabel("Code type:")
        h.addWidget(self.type_label)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["QR Code", "Barcode"])
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
        is_label_sheet = self._get_label_format_spec() is not None
        is_qr = is_label_sheet or self.type_combo.currentIndex() == 0
        self.type_label.setVisible(not is_label_sheet)
        self.type_combo.setVisible(not is_label_sheet)
        self.size_label.setVisible(not is_label_sheet)
        self.size_combo.setVisible(not is_label_sheet)
        self.style_label.setVisible(is_qr)
        self.style_combo.setVisible(is_qr)
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

        self._preview_toggle = _PillToggle(["Single", "Page"])
        self._preview_toggle.toggled.connect(self._on_toggle)
        v.addWidget(self._preview_toggle)

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

    def _on_toggle(self, idx):
        mode = "page" if idx == 1 else "single"
        if mode == self._preview_mode:
            return
        self._preview_mode = mode
        # Label stays 180×180 for both modes; background colour signals the mode
        if mode == "page":
            self._preview_img.setStyleSheet(
                "background: #b8bece; border: 1px solid #c0c8d8; border-radius: 4px;"
            )
        else:
            self._preview_img.setStyleSheet(
                "background: white; border: 1px solid #c0c8d8; border-radius: 4px;"
            )
        self._update_preview()

    def _update_preview(self):
        if self._preview_mode == "page":
            self._update_page_preview()
            return

        serial = self._preview_serial()
        if not serial:
            self._preview_img.setPixmap(QPixmap())
            self._preview_img.setText("No serial\nnumber found")
            self._preview_info.setText("")
            return

        try:
            spec = self._get_label_format_spec()
            is_label_sheet = spec is not None
            is_barcode = not is_label_sheet and self.type_combo.currentIndex() == 1
            if is_barcode:
                pixmap = self._render_barcode_preview(serial, self._qr_color)
                info = f"Code 128\nS/N: {serial}"
            else:
                style_idx = self.style_combo.currentIndex()
                pixmap = self._render_qr_preview(serial, style_idx, self._qr_color)
                if is_label_sheet:
                    size_str = f'{spec["label_w"]}"×{spec["label_h"]}"'
                else:
                    size_str = _SIZE_LABELS[self.size_combo.currentIndex()]
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

    def _update_page_preview(self):
        selected = [instr for cb, instr in self._checkboxes
                    if cb.isChecked() and instr["serial_number"]]
        if not selected:
            self._preview_img.setPixmap(QPixmap())
            self._preview_img.setText("No instruments\nselected")
            self._preview_info.setText("")
            return
        try:
            pixmap = self._render_page_preview(selected)
            if pixmap:
                self._preview_img.setText("")
                self._preview_img.setPixmap(
                    pixmap.scaled(_PREVIEW_PX, _PREVIEW_PX,
                                  Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                n = len(selected)
                self._preview_info.setText(
                    f"{n} instrument{'s' if n != 1 else ''} · first page"
                )
        except Exception as e:
            self._preview_img.setPixmap(QPixmap())
            self._preview_img.setText("Preview\nunavailable")
            self._preview_info.setText(str(e)[:60])

    def _preview_serial(self):
        for cb, instr in self._checkboxes:
            if instr["serial_number"]:
                return instr["serial_number"]
        return ""

    # ── PIL helpers ───────────────────────────────────────────────────────────

    def _qr_pil(self, serial, style_idx, color, size_px):
        """Return a PIL Image of the QR code resized to size_px × size_px."""
        from PIL import Image
        import qrcode

        border = 1 if size_px < 60 else 2
        qr = qrcode.QRCode(border=border)
        qr.add_data(serial)
        qr.make(fit=True)

        if style_idx == 0:
            img = qr.make_image(fill_color=color, back_color="white")
        else:
            try:
                from qrcode.image.styledpil import StyledPilImage
            except ImportError:
                from qrcode.image.styledimage import StyledPilImage
            try:
                from qrcode.image.styles.moduledrawers.pil import (
                    RoundedModuleDrawer, CircleModuleDrawer, GappedSquareModuleDrawer,
                )
            except ImportError:
                from qrcode.image.styles.moduledrawers import (
                    RoundedModuleDrawer, CircleModuleDrawer, GappedSquareModuleDrawer,
                )
            from qrcode.image.styles.colormasks import SolidFillColorMask
            drawer = [None,
                      RoundedModuleDrawer(),
                      CircleModuleDrawer(),
                      GappedSquareModuleDrawer()][style_idx]
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            img = qr.make_image(image_factory=StyledPilImage, module_drawer=drawer,
                                color_mask=SolidFillColorMask(front_color=(r, g, b)))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        pil_img = Image.open(buf).copy()
        return pil_img.resize((size_px, size_px), Image.LANCZOS)

    def _barcode_pil(self, serial, color="#000000", bar_h_px=60):
        """Return a PIL Image of the Code128B barcode (no text)."""
        from PIL import Image, ImageDraw

        data = [ch for ch in serial if 32 <= ord(ch) <= 126]
        bits = _CODE128B_SYM[104]
        check = 104
        for i, ch in enumerate(data):
            v = ord(ch) - 32
            bits += _CODE128B_SYM[v]
            check += (i + 1) * v
        bits += _CODE128B_SYM[check % 103]
        bits += _CODE128B_SYM[106]

        bar_w, quiet = 2, 8
        fg = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        img_w = len(bits) * bar_w + 2 * quiet
        img = Image.new("RGB", (img_w, bar_h_px), "white")
        draw = ImageDraw.Draw(img)
        x = quiet
        for bit in bits:
            if bit == "1":
                draw.rectangle([x, 0, x + bar_w - 1, bar_h_px - 1], fill=fg)
            x += bar_w
        return img

    def _render_qr_preview(self, serial, style_idx, color="#000000"):
        pil_img = self._qr_pil(serial, style_idx, color, _PREVIEW_PX)
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)
        px = QPixmap()
        px.loadFromData(buf.read())
        return px

    def _render_barcode_preview(self, serial, color="#000000"):
        from PIL import Image, ImageDraw
        bar_img = self._barcode_pil(serial, color, bar_h_px=60)
        w, h = bar_img.size
        final = Image.new("RGB", (w, h + 18), "white")
        final.paste(bar_img, (0, 0))
        draw = ImageDraw.Draw(final)
        fg = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        draw.text((8, h + 3), "".join(ch for ch in serial if 32 <= ord(ch) <= 126), fill=fg)
        buf = io.BytesIO()
        final.save(buf, format="PNG")
        buf.seek(0)
        px = QPixmap()
        px.loadFromData(buf.read())
        return px

    def _render_page_preview(self, selected):
        """
        Render a first-page thumbnail showing the actual print layout.
        The page floats on a grey background so it reads clearly as one page.
        Returns a QPixmap.
        """
        from PIL import Image, ImageDraw

        # Letter at 72 pt/px: 612 × 792
        PAGE_W, PAGE_H = 612, 792
        THUMB_W = _PREVIEW_PX
        THUMB_H = int(PAGE_H / PAGE_W * THUMB_W)   # ≈ 233

        # 3 px inset: grey surround + white page rect
        INSET = 3
        scale = (THUMB_W - 2 * INSET) / PAGE_W

        # Grey canvas — the page will appear as a white card floating on it
        canvas = Image.new("RGB", (THUMB_W, THUMB_H), "#b8bece")
        draw = ImageDraw.Draw(canvas)

        # White page with subtle border
        draw.rectangle(
            [INSET, INSET, THUMB_W - INSET - 1, THUMB_H - INSET - 1],
            fill="white", outline="#8090a8", width=1,
        )

        spec     = self._get_label_format_spec()
        avery    = spec is not None
        is_bcode = not avery and self.type_combo.currentIndex() == 1

        def pt2px(v):
            return max(1, int(v * scale))

        def page_x(x_pt):
            return INSET + 1 + pt2px(x_pt)

        def page_y(y_pt, h_pt):
            # PDF y=0 is bottom; PIL y=0 is top
            return INSET + 1 + pt2px(PAGE_H - y_pt - h_pt)

        def paste_code(instr, x_pt, y_pt, w_pt, h_pt, label_h_pt):
            px = page_x(x_pt)
            py = page_y(y_pt, h_pt)
            pw = pt2px(w_pt)
            ph = pt2px(h_pt)
            draw.rectangle([px, py, px + pw, py + ph], outline="#d0d4dc", width=1)
            try:
                if is_bcode:
                    bh = max(4, pt2px(h_pt - label_h_pt) - 2)
                    bw = max(4, pw - 4)
                    bc = self._barcode_pil(instr["serial_number"], self._qr_color,
                                           bar_h_px=bh)
                    bc = bc.resize((bw, bh), Image.LANCZOS)
                    canvas.paste(bc, (px + (pw - bw) // 2,
                                      py + pt2px(label_h_pt) + 1))
                else:
                    sz = max(4, min(pw - 4, pt2px(h_pt - label_h_pt) - 2))
                    qr = self._qr_pil(instr["serial_number"],
                                      self.style_combo.currentIndex(),
                                      self._qr_color, sz)
                    canvas.paste(qr, (px + (pw - sz) // 2,
                                      py + pt2px(label_h_pt) + 1))
            except Exception:
                pass

        if avery:
            s       = spec
            lw      = s["label_w"] * 72
            lh      = s["label_h"] * 72
            left_m  = s["left_margin"] * 72
            top_m   = s["top_margin"] * 72
            col_gap = s["col_gap"] * 72
            row_gap = s["row_gap"] * 72
            text_h  = min(0.45 * 72, lh * 0.4)
            total   = s["cols"] * s["rows"]
            for i, instr in enumerate(selected[:total]):
                col  = i % s["cols"]
                row  = i // s["cols"]
                x_pt = left_m + col * (lw + col_gap)
                y_pt = PAGE_H - top_m - (row + 1) * lh - row * row_gap
                paste_code(instr, x_pt, y_pt, lw, lh, text_h)
        else:
            margin_pt  = 0.4 * 72
            gap_pt     = 0.15 * 72
            label_h_pt = 0.55 * 72
            size_in    = _SIZE_INCHES[self.size_combo.currentIndex()]

            if is_bcode:
                bar_h_pt  = size_in * 72
                cell_w_pt = (PAGE_W - 2 * margin_pt - gap_pt) / 2
                cell_h_pt = bar_h_pt + label_h_pt + 0.15 * 72
                cols      = 2
            else:
                qr_pt     = size_in * 72
                cell_w_pt = qr_pt + 0.2 * 72
                cell_h_pt = qr_pt + label_h_pt + 0.1 * 72
                cols      = max(1, int((PAGE_W - 2 * margin_pt + gap_pt)
                                        / (cell_w_pt + gap_pt)))

            x_starts = [margin_pt + i * (cell_w_pt + gap_pt) for i in range(cols)]
            y_pt   = PAGE_H - margin_pt
            col_idx = 0

            for instr in selected:
                if col_idx == 0:
                    if y_pt - cell_h_pt < margin_pt:
                        break  # only first page
                    y_pt -= cell_h_pt
                paste_code(instr, x_starts[col_idx], y_pt,
                           cell_w_pt, cell_h_pt, label_h_pt)
                col_idx = (col_idx + 1) % cols

        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        buf.seek(0)
        px = QPixmap()
        px.loadFromData(buf.read())
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
        self.status_label.setVisible(False)
        h.addWidget(self.status_label)

        self._open_file_btn = QPushButton("Open File")
        self._open_file_btn.setVisible(False)
        self._open_file_btn.clicked.connect(self._open_saved_pdf)
        h.addWidget(self._open_file_btn)

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
            cb.stateChanged.connect(self._update_preview)
            self._list_layout.addWidget(cb)
            self._checkboxes.append((cb, instr))

        self._list_layout.addStretch()
        self._update_preview()

    def _select_all(self):
        for cb, instr in self._checkboxes:
            cb.blockSignals(True)
            if instr["serial_number"]:
                cb.setChecked(True)
            cb.blockSignals(False)
        self._update_preview()

    def _deselect_all(self):
        for cb, _ in self._checkboxes:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self._update_preview()

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
        spec = self._get_label_format_spec()
        if spec is not None:
            self._generate_label_sheet(path, selected, spec)
        else:
            self._generate_grid_pdf(path, selected)
        return True

    def _print_codes(self):
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.close()
            if not self._generate(tmp.name):
                return
            try:
                os.startfile(tmp.name, "print")
            except OSError:
                os.startfile(tmp.name)
                QMessageBox.information(
                    self, "Print",
                    "Your PDF viewer has been opened.\nUse File → Print from there to print."
                )
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
                self._saved_pdf_path = path
                self.status_label.setText("PDF saved.")
                self.status_label.setVisible(True)
                self._open_file_btn.setVisible(True)
                QTimer.singleShot(8000, self._clear_save_status)
        except ImportError as e:
            QMessageBox.critical(self, "Missing Library",
                                 f"Required library not installed:\n{e}\n\n"
                                 "Run: pip install qrcode[pil] reportlab")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{e}")

    def _clear_save_status(self):
        self.status_label.setVisible(False)
        self._open_file_btn.setVisible(False)

    def _open_saved_pdf(self):
        if hasattr(self, "_saved_pdf_path") and self._saved_pdf_path:
            os.startfile(self._saved_pdf_path)

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

    # ── Label sheet (any format) ──────────────────────────────────────────────

    def _generate_label_sheet(self, path, instruments, spec):
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as rl_canvas

        s = spec
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

        text_h  = min(0.45 * inch, label_h * 0.4)
        qr_avail = label_h - text_h - 0.08 * inch
        qr_size  = min(label_w - 0.15 * inch, qr_avail)
        qr_size  = max(0.15 * inch, qr_size)

        c = rl_canvas.Canvas(path, pagesize=letter)
        pos = 0
        labels_per_page = cols * s["rows"]

        for instr in instruments:
            serial = self._serial_for(instr)
            if not serial:
                continue
            if pos > 0 and pos % labels_per_page == 0:
                c.showPage()
            slot = pos % labels_per_page
            x = x_starts[slot % cols]
            y = y_starts[slot // cols]

            c.setStrokeColor(colors.Color(0.75, 0.75, 0.75))
            c.setLineWidth(0.3)
            c.setDash(2, 3)
            c.rect(x, y, label_w, label_h)
            c.setDash()

            self._draw_qr_cell(c, instr, serial, x, y, label_w,
                               qr_size, text_h, inch,
                               style_idx=self.style_combo.currentIndex(),
                               color=self._qr_color)
            pos += 1

        c.save()

    # ── Format management ─────────────────────────────────────────────────────

    @staticmethod
    def _format_combo_label(spec):
        total = spec["cols"] * spec["rows"]
        return f"{spec['name']}  ({spec['label_w']}\"×{spec['label_h']}\", {total}/sheet)"

    def _get_label_format_spec(self):
        idx = self.format_combo.currentIndex()
        if idx == 0:
            return None
        return self._format_specs[idx - 1]

    def _load_user_formats(self):
        try:
            path = _get_user_formats_path()
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                user_formats = json.load(f)
            for fmt in user_formats:
                if fmt.get("name") not in self._format_names_added:
                    self._format_specs.append(fmt)
                    self._format_names_added.add(fmt["name"])
        except Exception:
            pass

    def _save_user_formats(self):
        try:
            user_formats = list(self._format_specs)
            with open(_get_user_formats_path(), "w", encoding="utf-8") as f:
                json.dump(user_formats, f, indent=2)
        except Exception:
            pass

    def _add_label_format(self):
        dlg = AddLabelFormatDialog(self._format_names_added, self)
        if dlg.exec() != QDialog.Accepted or dlg.selected_format is None:
            return
        fmt = dlg.selected_format
        self._format_specs.append(fmt)
        self._format_names_added.add(fmt["name"])
        self.format_combo.addItem(self._format_combo_label(fmt))
        self.format_combo.setCurrentIndex(self.format_combo.count() - 1)
        self._save_user_formats()

    def _update_remove_btn(self):
        self._remove_fmt_btn.setVisible(self.format_combo.currentIndex() > 0)

    def _remove_label_format(self):
        idx = self.format_combo.currentIndex()
        if idx <= 0:
            return
        fmt = self._format_specs[idx - 1]
        self._format_specs.pop(idx - 1)
        self._format_names_added.discard(fmt["name"])
        self.format_combo.removeItem(idx)
        self._save_user_formats()

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
            try:
                from qrcode.image.styledpil import StyledPilImage
            except ImportError:
                from qrcode.image.styledimage import StyledPilImage
            try:
                from qrcode.image.styles.moduledrawers.pil import (
                    RoundedModuleDrawer, CircleModuleDrawer, GappedSquareModuleDrawer,
                )
            except ImportError:
                from qrcode.image.styles.moduledrawers import (
                    RoundedModuleDrawer, CircleModuleDrawer, GappedSquareModuleDrawer,
                )
            from qrcode.image.styles.colormasks import SolidFillColorMask
            drawer = [None,
                      RoundedModuleDrawer(),
                      CircleModuleDrawer(),
                      GappedSquareModuleDrawer()][style_idx]
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            img = qr.make_image(image_factory=StyledPilImage, module_drawer=drawer,
                                color_mask=SolidFillColorMask(front_color=(r, g, b)))

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
