from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QFrame,
)
from config import verify_pin, hash_pin


class PINLockDialog(QDialog):
    """Shown on startup when PIN is enabled. Cannot be dismissed without correct PIN."""

    def __init__(self, stored_hash: str, parent=None):
        super().__init__(parent)
        self._stored_hash = stored_hash
        self.setWindowTitle("Instrument Tracker — Locked")
        self.setMinimumWidth(320)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)  # no close button
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("🔒  Enter PIN to unlock")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
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

    def _try_unlock(self):
        pin = self.pin_input.text()
        if verify_pin(pin, self._stored_hash):
            self.accept()
        else:
            self.error_label.setText("Incorrect PIN. Please try again.")
            self.pin_input.clear()
            self.pin_input.setFocus()

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
