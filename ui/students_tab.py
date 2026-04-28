from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QFileDialog, QMessageBox,
)
import database as db


class StudentsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Manage Students")
        title.setObjectName("section_title")
        layout.addWidget(title)

        layout.addWidget(self._build_add_group())
        layout.addWidget(self._build_import_group())
        layout.addWidget(self._build_export_group())
        layout.addStretch()

    # ── Add single ────────────────────────────────────────────────────────────

    def _build_add_group(self):
        group = QGroupBox("Add Single Student")
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

        self.name_edit = row("Name:", "Student Name")
        self.sid_edit = row("Student ID:", "Student ID (must be unique)")
        self.grade_edit = row("Grade:", "e.g., 9, 10, 11, 12")

        add_btn = QPushButton("Add New Student")
        add_btn.setObjectName("primary")
        add_btn.setMinimumHeight(38)
        add_btn.clicked.connect(self._add_student)
        v.addWidget(add_btn)

        self.add_status = QLabel("")
        self.add_status.setObjectName("status")
        v.addWidget(self.add_status)

        return group

    def _add_student(self):
        name = self.name_edit.text().strip()
        sid = self.sid_edit.text().strip()
        grade = self.grade_edit.text().strip()

        if not name or not sid:
            self.add_status.setText("Name and Student ID are required.")
            return
        try:
            db.add_student(name, sid, grade)
            self.add_status.setText(f"Added: {name} (ID: {sid})")
            self.name_edit.clear()
            self.sid_edit.clear()
            self.grade_edit.clear()
            self.name_edit.setFocus()
        except Exception as e:
            self.add_status.setText(f"Error: {e}")

    # ── Import ────────────────────────────────────────────────────────────────

    def _build_import_group(self):
        group = QGroupBox("Import Students from CSV")
        v = QVBoxLayout(group)
        v.setSpacing(8)

        v.addWidget(QLabel("Expected columns: Name, Student ID, Grade"))

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
            added, skipped = db.import_students_from_csv(path)
            self.import_status.setText(
                f"Done. Added: {added}  Skipped/Errors: {skipped}"
            )
        except Exception as e:
            self.import_status.setText(f"Error: {e}")

    # ── Export ────────────────────────────────────────────────────────────────

    def _build_export_group(self):
        group = QGroupBox("Export Students")
        v = QVBoxLayout(group)
        v.setSpacing(8)

        btn = QPushButton("Export Students to CSV")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._export_csv)
        v.addWidget(btn)

        self.export_status = QLabel("")
        self.export_status.setObjectName("status")
        v.addWidget(self.export_status)

        return group

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "students.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            count = db.export_students_to_csv(path)
            self.export_status.setText(f"Exported {count} students.")
        except Exception as e:
            self.export_status.setText(f"Error: {e}")
