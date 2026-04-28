from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
)
import database as db
from ui.student_detail_dialog import StudentDetailDialog


class EditStudentDialog(QDialog):
    def __init__(self, student, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Student")
        self.setFixedWidth(380)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.name_edit = QLineEdit(student["name"])
        self.sid_edit = QLineEdit(student["student_id"])
        self.grade_edit = QLineEdit(student["grade"] or "")

        layout.addRow("Name:", self.name_edit)
        layout.addRow("Student ID:", self.sid_edit)
        layout.addRow("Grade:", self.grade_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_values(self):
        return (
            self.name_edit.text().strip(),
            self.sid_edit.text().strip(),
            self.grade_edit.text().strip(),
        )


class ViewStudentsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(10)

        # Title + search row
        top = QHBoxLayout()
        title = QLabel("View All Students")
        title.setObjectName("section_title")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setObjectName("search")
        self.search_box.setPlaceholderText("Filter by Name, Student ID, Grade…")
        self.search_box.setMinimumWidth(80)
        self.search_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_box.textChanged.connect(self._apply_filter)
        top.addWidget(self.search_box)
        layout.addLayout(top)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Student ID", "Grade"])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._view_history)
        layout.addWidget(self.table)

        # Bottom bar
        bottom = QWidget()
        bottom.setObjectName("bottom_bar")
        bar = QHBoxLayout(bottom)
        bar.setContentsMargins(8, 6, 8, 6)
        bar.setSpacing(8)

        def bar_btn(text, slot, danger=False):
            btn = QPushButton(text)
            btn.setMinimumHeight(34)
            btn.setMinimumWidth(60)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if danger:
                btn.setObjectName("danger")
            btn.clicked.connect(slot)
            bar.addWidget(btn)
            return btn

        bar_btn("Refresh", self.refresh)
        bar_btn("Edit Student", self._edit_student)
        bar_btn("History", self._view_history)
        bar_btn("Delete", self._delete_student, danger=True)

        layout.addWidget(bottom)

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self):
        self._data = db.get_all_students()
        self._populate(self._data)

    def _populate(self, rows):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, s in enumerate(rows):
            vals = [str(s["id"]), s["name"], s["student_id"], s["grade"] or ""]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setData(Qt.UserRole, s["id"])
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)

    def _apply_filter(self, text):
        text = text.lower()
        if not text:
            self._populate(self._data)
            return
        filtered = [
            s for s in self._data
            if any(
                text in str(v or "").lower()
                for v in [s["name"], s["student_id"], s["grade"]]
            )
        ]
        self._populate(filtered)

    def _selected_student_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    # ── Actions ───────────────────────────────────────────────────────────────

    def _edit_student(self):
        sid = self._selected_student_id()
        if sid is None:
            QMessageBox.information(self, "No Selection", "Select a student first.")
            return
        student = db.get_student_by_id(sid)
        if not student:
            return
        dlg = EditStudentDialog(student, self)
        if dlg.exec() != QDialog.Accepted:
            return
        name, student_id, grade = dlg.get_values()
        if not name or not student_id:
            QMessageBox.warning(self, "Required", "Name and Student ID are required.")
            return
        try:
            db.update_student(sid, name, student_id, grade)
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _view_history(self):
        sid = self._selected_student_id()
        if sid is None:
            QMessageBox.information(self, "No Selection", "Select a student first.")
            return
        dlg = StudentDetailDialog(sid, self)
        dlg.exec()

    def _delete_student(self):
        sid = self._selected_student_id()
        if sid is None:
            QMessageBox.information(self, "No Selection", "Select a student first.")
            return
        student = db.get_student_by_id(sid)
        if not student:
            return
        reply = QMessageBox.warning(
            self, "Confirm Delete",
            f"Delete student {student['name']} ({student['student_id']})?\n\n"
            "This will also delete all their contracts.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db.delete_student(sid)
            self.refresh()
