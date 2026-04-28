from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QFileDialog, QMessageBox, QSizePolicy,
)
import database as db


class InstrumentsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Manage Instruments")
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(self._build_add_group())
        layout.addWidget(self._build_import_group())
        layout.addWidget(self._build_export_group())
        layout.addStretch()

    # ── Add single ────────────────────────────────────────────────────────────

    def _build_add_group(self):
        group = QGroupBox("Add Single Instrument")
        v = QVBoxLayout(group)
        v.setSpacing(8)

        def row(label, placeholder):
            h = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(60)
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            h.addWidget(lbl)
            h.addWidget(edit)
            v.addLayout(h)
            return edit

        self.name_edit = row("Name:", "e.g., Flute, Trumpet")
        self.model_edit = row("Model:", "e.g., Yamaha YFL-221")
        self.serial_edit = row("Serial/QR:", "Serial Number (used as QR text if QR left blank)")
        self.qr_edit = row("QR Code Text:", "Leave blank to use serial number")

        add_btn = QPushButton("Add New Instrument")
        add_btn.setObjectName("primary")
        add_btn.setMinimumHeight(38)
        add_btn.clicked.connect(self._add_instrument)
        v.addWidget(add_btn)

        self.add_status = QLabel("")
        self.add_status.setObjectName("status")
        v.addWidget(self.add_status)

        return group

    def _add_instrument(self):
        name = self.name_edit.text().strip()
        model = self.model_edit.text().strip()
        serial = self.serial_edit.text().strip()
        qr = self.qr_edit.text().strip() or serial

        if not name:
            self.add_status.setText("Name is required.")
            return
        try:
            db.add_instrument(name, model, serial, qr)
            self.add_status.setText(f"Added: {name} ({model})")
            self.name_edit.clear()
            self.model_edit.clear()
            self.serial_edit.clear()
            self.qr_edit.clear()
            self.name_edit.setFocus()
        except Exception as e:
            self.add_status.setText(f"Error: {e}")

    # ── Import ────────────────────────────────────────────────────────────────

    def _build_import_group(self):
        group = QGroupBox("Import Instruments from CSV")
        v = QVBoxLayout(group)
        v.setSpacing(8)

        v.addWidget(QLabel("Expected columns: Name, Model, Serial Number, QR Code Text"))

        btn = QPushButton("Choose CSV File and Import")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._import_csv)
        v.addWidget(btn)

        self.import_status = QLabel("Status: Ready.")
        self.import_status.setObjectName("status")
        v.addWidget(self.import_status)

        return group

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        try:
            added, skipped = db.import_instruments_from_csv(path)
            self.import_status.setText(
                f"Done. Added: {added}  Skipped/Errors: {skipped}"
            )
        except Exception as e:
            self.import_status.setText(f"Error: {e}")

    # ── Export ────────────────────────────────────────────────────────────────

    def _build_export_group(self):
        group = QGroupBox("Export Instruments")
        v = QVBoxLayout(group)
        v.setSpacing(8)

        btn = QPushButton("Export Instruments to CSV")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._export_csv)
        v.addWidget(btn)

        self.export_status = QLabel("")
        self.export_status.setObjectName("status")
        v.addWidget(self.export_status)

        return group

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "instruments.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            count = db.export_instruments_to_csv(path)
            self.export_status.setText(f"Exported {count} instruments.")
        except Exception as e:
            self.export_status.setText(f"Error: {e}")
