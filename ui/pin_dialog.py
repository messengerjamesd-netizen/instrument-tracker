from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QFrame,
)
from config import verify_pin, hash_pin, verify_recovery_code


class PINLockDialog(QDialog):
    """Shown on startup when PIN is enabled. Cannot be dismissed without correct PIN."""

    def __init__(self, stored_hash: str, recovery_hash: str = "", parent=None):
        super().__init__(parent)
        self._stored_hash = stored_hash
        self._recovery_hash = recovery_hash
        self.setWindowTitle("Instrument Tracker — Locked")
        self.setMinimumWidth(320)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)  # no close button
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("🔒  Enter PIN to unlock")
        title.setStyleSheet("font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Enter PIN…")
        self.pin_input.setMinimumHeight(38)
        self.pin_input.setAlignment(Qt.AlignCenter)
        self.pin_input.returnPressed.connect(self._try_unlock)
        layout.addWidget(self.pin_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e05555;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)

        unlock_btn = QPushButton("Unlock")
        unlock_btn.setObjectName("primary")
        unlock_btn.setMinimumHeight(38)
        unlock_btn.clicked.connect(self._try_unlock)
        layout.addWidget(unlock_btn)

        forgot_btn = QPushButton("Forgot PIN?")
        forgot_btn.setFlat(True)
        forgot_btn.setStyleSheet("color: #5a7aaa; font-size: 10px; border: none;")
        forgot_btn.clicked.connect(self._try_recovery)
        layout.addWidget(forgot_btn, alignment=Qt.AlignCenter)

    def _try_unlock(self):
        pin = self.pin_input.text()
        if verify_pin(pin, self._stored_hash):
            self.accept()
        else:
            self.error_label.setText("Incorrect PIN. Please try again.")
            self.pin_input.clear()
            self.pin_input.setFocus()

    def _try_recovery(self):
        if not self._recovery_hash:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "No Recovery Code",
                "No recovery code has been set up for this PIN.\n\n"
                "Ask your administrator to reset the PIN in Options → Security."
            )
            return
        dlg = ForgotPINDialog(self._recovery_hash, self)
        if dlg.exec() == QDialog.Accepted:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Access Restored",
                "Access restored using recovery code.\n\n"
                "Please set a new PIN in Options → Security."
            )
            self.accept()

    def closeEvent(self, event):
        event.ignore()  # prevent closing without correct PIN


class SetPINDialog(QDialog):
    """Set a new PIN. If changing an existing PIN, current_hash must be provided."""

    def __init__(self, current_hash: str = "", parent=None):
        super().__init__(parent)
        self._current_hash = current_hash
        self.setWindowTitle("Set PIN")
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        if self._current_hash:
            layout.addWidget(QLabel("Current PIN:"))
            self.current_input = QLineEdit()
            self.current_input.setEchoMode(QLineEdit.Password)
            self.current_input.setMinimumHeight(34)
            layout.addWidget(self.current_input)
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            layout.addWidget(line)
        else:
            self.current_input = None

        layout.addWidget(QLabel("New PIN (minimum 4 digits):"))
        self.new_input = QLineEdit()
        self.new_input.setEchoMode(QLineEdit.Password)
        self.new_input.setMinimumHeight(34)
        layout.addWidget(self.new_input)

        layout.addWidget(QLabel("Confirm new PIN:"))
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setMinimumHeight(34)
        self.confirm_input.returnPressed.connect(self._on_accept)
        layout.addWidget(self.confirm_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e05555;")
        layout.addWidget(self.error_label)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        if self.current_input:
            if not verify_pin(self.current_input.text(), self._current_hash):
                self.error_label.setText("Current PIN is incorrect.")
                self.current_input.clear()
                return

        new_pin = self.new_input.text()
        if len(new_pin) < 4:
            self.error_label.setText("PIN must be at least 4 digits.")
            return
        if new_pin != self.confirm_input.text():
            self.error_label.setText("PINs do not match.")
            self.confirm_input.clear()
            return

        self._new_hash = hash_pin(new_pin)
        self.accept()

    def get_new_hash(self) -> str:
        return getattr(self, "_new_hash", "")


class VerifyPINDialog(QDialog):
    """Verify the current PIN — used when disabling PIN lock."""

    def __init__(self, stored_hash: str, parent=None):
        super().__init__(parent)
        self._stored_hash = stored_hash
        self.setWindowTitle("Verify PIN")
        self.setMinimumWidth(300)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("Enter your current PIN to disable PIN lock:"))

        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setMinimumHeight(34)
        self.pin_input.returnPressed.connect(self._on_accept)
        layout.addWidget(self.pin_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e05555;")
        layout.addWidget(self.error_label)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        if verify_pin(self.pin_input.text(), self._stored_hash):
            self.accept()
        else:
            self.error_label.setText("Incorrect PIN.")
            self.pin_input.clear()


class RecoveryCodeDialog(QDialog):
    """Shown once after a PIN is set. Displays the recovery code to write down."""

    def __init__(self, code: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Your Recovery Code")
        self.setMinimumWidth(400)
        # No close button — must acknowledge
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        self._build_ui(code)

    def _build_ui(self, code: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("<b>Save this recovery code now.</b>"))
        layout.addWidget(QLabel(
            "If you ever forget your PIN, this code will unlock the app.\n"
            "Write it down and keep it somewhere safe — it cannot be shown again."
        ))

        formatted = f"{code[:4]}-{code[4:8]}-{code[8:]}"
        code_label = QLabel(formatted)
        code_label.setAlignment(Qt.AlignCenter)
        code_label.setStyleSheet(
            "font-size: 22px; font-weight: bold; font-family: monospace; "
            "color: #e8f0ff; letter-spacing: 4px; padding: 14px;"
        )
        layout.addWidget(code_label)

        warn = QLabel("This code will not be shown again.")
        warn.setStyleSheet("color: #e08040; font-style: italic;")
        warn.setAlignment(Qt.AlignCenter)
        layout.addWidget(warn)

        btns = QDialogButtonBox()
        ok_btn = btns.addButton("I've Written It Down", QDialogButtonBox.AcceptRole)
        ok_btn.setObjectName("primary")
        ok_btn.setMinimumHeight(36)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)


class ForgotPINDialog(QDialog):
    """Enter the paper recovery code to bypass PIN lock."""

    def __init__(self, stored_recovery_hash: str, parent=None):
        super().__init__(parent)
        self._stored_recovery_hash = stored_recovery_hash
        self.setWindowTitle("Enter Recovery Code")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel(
            "Enter the recovery code that was shown when your PIN was set.\n"
            "Dashes and spaces are ignored."
        ))

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g. A1B2-C3D4-E5F6")
        self.code_input.setMinimumHeight(38)
        self.code_input.setAlignment(Qt.AlignCenter)
        self.code_input.returnPressed.connect(self._on_accept)
        layout.addWidget(self.code_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e05555;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        code = self.code_input.text().replace("-", "").replace(" ", "").upper()
        if verify_recovery_code(code, self._stored_recovery_hash):
            self.accept()
        else:
            self.error_label.setText("Incorrect recovery code. Please try again.")
            self.code_input.clear()
