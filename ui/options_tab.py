import shutil
import zipfile
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QDialog, QColorDialog, QMessageBox, QFileDialog,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

import config as cfg
import database as db
from ui.themes import THEME_LABELS, apply_theme
from ui.pin_dialog import SetPINDialog, VerifyPINDialog


class OptionsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = cfg.load_config()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Options")
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(self._build_appearance_group())
        layout.addWidget(self._build_security_group())
        layout.addWidget(self._build_backup_group())
        layout.addStretch()

    # ── Appearance ────────────────────────────────────────────────────────────

    def _build_appearance_group(self):
        group = QGroupBox("Appearance")
        v = QVBoxLayout(group)
        v.setSpacing(12)

        # Font size
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font size:"))
        self._font_btns = {}
        for key, label in [("small", "Small"), ("medium", "Default"), ("large", "Large")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            btn.setMinimumHeight(34)
            is_active = self._config["font_size"] == key
            btn.setChecked(is_active)
            btn.setObjectName("primary" if is_active else "")
            btn.clicked.connect(lambda _, k=key: self._set_font_size(k))
            font_row.addWidget(btn)
            self._font_btns[key] = btn
        font_row.addStretch()
        v.addLayout(font_row)

        # Theme
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        for key, label in THEME_LABELS.items():
            self.theme_combo.addItem(label, key)
        current_idx = self.theme_combo.findData(self._config["theme"])
        if current_idx >= 0:
            self.theme_combo.setCurrentIndex(current_idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        v.addLayout(theme_row)

        # Custom color pickers (only visible when Custom is selected)
        self._custom_row = QHBoxLayout()
        self._custom_row.addWidget(QLabel("Background color:"))
        self._secondary_btn = QPushButton()
        self._secondary_btn.setFixedSize(60, 28)
        self._secondary_btn.clicked.connect(self._pick_secondary)
        self._custom_row.addWidget(self._secondary_btn)
        self._custom_row.addSpacing(16)
        self._custom_row.addWidget(QLabel("Accent color:"))
        self._primary_btn = QPushButton()
        self._primary_btn.setFixedSize(60, 28)
        self._primary_btn.clicked.connect(self._pick_primary)
        self._custom_row.addWidget(self._primary_btn)
        self._custom_row.addStretch()

        self._custom_widget = QWidget()
        self._custom_widget.setLayout(self._custom_row)
        v.addWidget(self._custom_widget)

        self._update_color_buttons()
        self._custom_widget.setVisible(self._config["theme"] == "custom")

        return group

    def _update_color_buttons(self):
        p = self._config["custom_primary"]
        s = self._config["custom_secondary"]
        self._primary_btn.setStyleSheet(
            f"background-color: {p}; border: 1px solid #888; border-radius: 3px;"
        )
        self._secondary_btn.setStyleSheet(
            f"background-color: {s}; border: 1px solid #888; border-radius: 3px;"
        )

    def _set_font_size(self, size: str):
        for k, btn in self._font_btns.items():
            active = k == size
            btn.setChecked(active)
            btn.setObjectName("primary" if active else "")
            btn.setStyle(btn.style())  # force style refresh
        self._config["font_size"] = size
        try:
            cfg.save_config(self._config)
        except Exception:
            pass
        self._apply()

    def _on_theme_changed(self, _index):
        theme = self.theme_combo.currentData()
        self._config["theme"] = theme
        self._custom_widget.setVisible(theme == "custom")
        try:
            cfg.save_config(self._config)
        except Exception:
            pass
        self._apply()

    def _pick_primary(self):
        color = QColorDialog.getColor(
            QColor(self._config["custom_primary"]), self, "Pick Primary Color"
        )
        if color.isValid():
            self._config["custom_primary"] = color.name()
            self._update_color_buttons()
            try:
                cfg.save_config(self._config)
            except Exception:
                pass
            self._apply()

    def _pick_secondary(self):
        color = QColorDialog.getColor(
            QColor(self._config["custom_secondary"]), self, "Pick Background Color"
        )
        if color.isValid():
            self._config["custom_secondary"] = color.name()
            self._update_color_buttons()
            try:
                cfg.save_config(self._config)
            except Exception:
                pass
            self._apply()

    def _apply(self):
        apply_theme(
            QApplication.instance(),
            self._config["theme"],
            self._config["font_size"],
            self._config["custom_primary"],
            self._config["custom_secondary"],
        )

    # ── Security ──────────────────────────────────────────────────────────────

    def _build_security_group(self):
        group = QGroupBox("Security")
        v = QVBoxLayout(group)
        v.setSpacing(10)

        pin_row = QHBoxLayout()
        self._pin_status = QLabel(self._pin_status_text())
        pin_row.addWidget(self._pin_status)
        pin_row.addStretch()

        self._toggle_pin_btn = QPushButton(
            "Disable PIN Lock" if self._config["pin_enabled"] else "Enable PIN Lock"
        )
        self._toggle_pin_btn.setMinimumHeight(34)
        self._toggle_pin_btn.clicked.connect(self._toggle_pin)
        pin_row.addWidget(self._toggle_pin_btn)

        self._change_pin_btn = QPushButton("Change PIN")
        self._change_pin_btn.setMinimumHeight(34)
        self._change_pin_btn.setVisible(self._config["pin_enabled"])
        self._change_pin_btn.clicked.connect(self._change_pin)
        pin_row.addWidget(self._change_pin_btn)

        v.addLayout(pin_row)
        v.addWidget(QLabel(
            "When enabled, a PIN will be required each time the app is opened."
        ))
        return group

    def _pin_status_text(self):
        if self._config["pin_enabled"]:
            return "PIN lock is <b>enabled</b>."
        return "PIN lock is <b>disabled</b>."

    def _toggle_pin(self):
        if self._config["pin_enabled"]:
            # Must verify current PIN to disable
            dlg = VerifyPINDialog(self._config["pin_hash"], self)
            if dlg.exec() != QDialog.Accepted:
                return
            self._config["pin_enabled"] = False
            self._config["pin_hash"] = ""
        else:
            # Set new PIN
            dlg = SetPINDialog(parent=self)
            if dlg.exec() != QDialog.Accepted:
                return
            self._config["pin_enabled"] = True
            self._config["pin_hash"] = dlg.get_new_hash()

        try:
            cfg.save_config(self._config)
        except Exception:
            pass
        self._pin_status.setText(self._pin_status_text())
        self._toggle_pin_btn.setText(
            "Disable PIN Lock" if self._config["pin_enabled"] else "Enable PIN Lock"
        )
        self._change_pin_btn.setVisible(self._config["pin_enabled"])

        state = "enabled" if self._config["pin_enabled"] else "disabled"
        QMessageBox.information(self, "PIN Lock", f"PIN lock has been {state}.")

    def _change_pin(self):
        dlg = SetPINDialog(current_hash=self._config["pin_hash"], parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        self._config["pin_hash"] = dlg.get_new_hash()
        try:
            cfg.save_config(self._config)
        except Exception:
            pass
        QMessageBox.information(self, "PIN Changed", "Your PIN has been updated.")

    # ── Backup & Restore ──────────────────────────────────────────────────────

    def _build_backup_group(self):
        group = QGroupBox("Backup & Restore")
        v = QVBoxLayout(group)
        v.setSpacing(10)

        btn_row = QHBoxLayout()

        backup_btn = QPushButton("💾  Backup Data")
        backup_btn.setMinimumHeight(36)
        backup_btn.clicked.connect(self._backup)
        btn_row.addWidget(backup_btn)

        restore_btn = QPushButton("📂  Restore from Backup")
        restore_btn.setMinimumHeight(36)
        restore_btn.clicked.connect(self._restore)
        btn_row.addWidget(restore_btn)

        btn_row.addStretch()
        v.addLayout(btn_row)

        v.addWidget(QLabel(
            "Backup saves your database to a zip file you choose. "
            "Restore replaces the current database — restart the app afterward."
        ))
        return group

    def _backup(self):
        src = db.get_db_path()
        default_name = f"InstrumentTracker_Backup_{date.today().strftime('%Y%m%d')}.zip"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Backup", default_name, "Zip Files (*.zip)"
        )
        if not path:
            return
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(src, "band_tracker.db")
            QMessageBox.information(self, "Backup Complete", f"Backup saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", str(e))

    def _restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", "", "Zip Files (*.zip)"
        )
        if not path:
            return
        try:
            with zipfile.ZipFile(path, "r") as zf:
                if "band_tracker.db" not in zf.namelist():
                    QMessageBox.warning(
                        self, "Invalid Backup",
                        "This zip file doesn't contain a valid database backup."
                    )
                    return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read zip file:\n{e}")
            return

        reply = QMessageBox.warning(
            self, "Confirm Restore",
            "This will replace your current database with the backup.\n\n"
            "All current data will be overwritten. This cannot be undone.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            dest = db.get_db_path()
            with zipfile.ZipFile(path, "r") as zf:
                with zf.open("band_tracker.db") as src_file, open(dest, "wb") as dst_file:
                    shutil.copyfileobj(src_file, dst_file)
            QMessageBox.information(
                self, "Restore Complete",
                "Database restored successfully.\n\n"
                "Please restart the application to see the restored data."
            )
        except Exception as e:
            QMessageBox.critical(self, "Restore Failed", str(e))
