from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QFileDialog,
)

import database as db
import config as cfg
from ui.student_detail_dialog import StudentDetailDialog
from ui.instruments_page import _read_spreadsheet


# ── Dialogs ───────────────────────────────────────────────────────────────────

class AddStudentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Student")
        self.setFixedWidth(380)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Student Name  (required)")
        self.sid_edit = QLineEdit()
        self.sid_edit.setPlaceholderText("Student ID — must be unique  (required)")
        self.grade_edit = QLineEdit()
        self.grade_edit.setPlaceholderText("e.g., 9, 10, 11, 12")

        layout.addRow("Name *", self.name_edit)
        layout.addRow("Student ID *", self.sid_edit)
        layout.addRow("Grade", self.grade_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

        self.name_edit.setFocus()

    def _on_accept(self):
        if not self.name_edit.text().strip() or not self.sid_edit.text().strip():
            QMessageBox.warning(self, "Required", "Name and Student ID are required.")
            return
        self.accept()

    def get_values(self):
        return (
            self.name_edit.text().strip(),
            self.sid_edit.text().strip(),
            self.grade_edit.text().strip(),
        )


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


# ── Main page ─────────────────────────────────────────────────────────────────

class StudentsPage(QWidget):
    navigate_to_instrument = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(10)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setObjectName("search")
        self.search_box.setPlaceholderText("Filter by name, student ID, grade…")
        self.search_box.setMinimumWidth(80)
        self.search_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_box.textChanged.connect(lambda _: self._apply_filter())
        toolbar.addWidget(self.search_box)

        toolbar.addSpacing(12)
        import_btn = QPushButton("Import Spreadsheet")
        import_btn.setMinimumHeight(32)
        import_btn.setToolTip(
            "Expected columns: Name, Student ID, Grade\n"
            "Supports .csv, .tsv, .xlsx, .xls, .ods"
        )
        import_btn.clicked.connect(self._import_spreadsheet)
        toolbar.addWidget(import_btn)

        add_btn = QPushButton("+ Add Student")
        add_btn.setObjectName("primary")
        add_btn.setMinimumHeight(32)
        add_btn.clicked.connect(self._add_student)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Student ID", "Grade", "Instrument"])
        self.table.setColumnHidden(0, True)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionsClickable(True)
        hdr.sectionClicked.connect(self._on_header_clicked)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._view_history)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        self.table.cellEntered.connect(self._on_cell_hovered)
        self.table.viewport().installEventFilter(self)
        self._hovered_link_cell = None
        layout.addWidget(self.table)

        # Hint + row count
        hint = QLabel("Tip: Double-click a row to view a student's full instrument history.")
        hint.setStyleSheet("font-size: 11px; color: #5a7aaa; padding: 2px 0;")
        layout.addWidget(hint)

        self.row_count_label = QLabel("")
        self.row_count_label.setObjectName("status")
        layout.addWidget(self.row_count_label)

        # Bottom action bar
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

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if self.table.hasFocus():
            if event.key() == Qt.Key_Delete:
                self._delete_student()
                return
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_F2):
                self._edit_student()
                return
        super().keyPressEvent(event)

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self):
        self._data = db.get_student_roster()
        self._apply_filter()
        self._restore_sort()

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

            instrument_id = s["instrument_id"] if s["instrument_id"] else None
            count = s["instrument_count"] if s["instrument_count"] else 0
            if instrument_id:
                instrument_name = s["instrument_name"] or ""
                model = s["model"] or ""
                label = f"{instrument_name} ({model})" if model else instrument_name
                if count > 1:
                    label += f" + {count - 1} more"
                instr_item = QTableWidgetItem(label)
                instr_item.setForeground(QColor("#7eb8f7"))
                instr_item.setToolTip("Click to view this instrument")
            else:
                instr_item = QTableWidgetItem("—")
            instr_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            instr_item.setData(Qt.UserRole, s["id"])
            instr_item.setData(Qt.UserRole + 1, instrument_id)
            self.table.setItem(r, 4, instr_item)

        self.table.setSortingEnabled(True)

        total = len(self._data)
        shown = len(rows)
        if total == 0:
            self.row_count_label.setText(
                "No students yet — click + Add Student to get started."
            )
        elif shown == 0:
            self.row_count_label.setText("No students match your search.")
        elif shown == total:
            self.row_count_label.setText(
                f"Showing {shown} student{'s' if shown != 1 else ''}"
            )
        else:
            self.row_count_label.setText(f"Showing {shown} of {total} students")

    def _apply_filter(self):
        text = self.search_box.text().lower()
        if not text:
            self._populate(self._data)
            return
        filtered = [
            s for s in self._data
            if any(
                text in str(v or "").lower()
                for v in [s["name"], s["student_id"], s["grade"], s["instrument_name"]]
            )
        ]
        self._populate(filtered)

    def show_student(self, student_id):
        self.search_box.clear()
        self.refresh()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == student_id:
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                break

    def _on_cell_hovered(self, row, col):
        self._clear_link_hover()
        item = self.table.item(row, col)
        if col == 4 and item and item.data(Qt.UserRole + 1):
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            self._hovered_link_cell = (row, col)

    def _clear_link_hover(self):
        if self._hovered_link_cell:
            r, c = self._hovered_link_cell
            item = self.table.item(r, c)
            if item:
                font = item.font()
                font.setBold(False)
                item.setFont(font)
            self._hovered_link_cell = None

    def eventFilter(self, obj, event):
        if obj is self.table.viewport() and event.type() == QEvent.Leave:
            self._clear_link_hover()
        return super().eventFilter(obj, event)

    def _on_cell_clicked(self, row, col):
        if col != 4:
            return
        item = self.table.item(row, 4)
        if not item:
            return
        instrument_id = item.data(Qt.UserRole + 1)
        if instrument_id:
            self.navigate_to_instrument.emit(instrument_id)

    def _selected_student_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    # ── Sort memory ───────────────────────────────────────────────────────────

    def _on_header_clicked(self, col):
        order = self.table.horizontalHeader().sortIndicatorOrder()
        c = cfg.load_config()
        c["students_sort_col"] = col
        c["students_sort_asc"] = (order == Qt.AscendingOrder)
        cfg.save_config(c)

    def _restore_sort(self):
        c = cfg.load_config()
        col = c.get("students_sort_col", 1)
        asc = c.get("students_sort_asc", True)
        order = Qt.AscendingOrder if asc else Qt.DescendingOrder
        self.table.horizontalHeader().setSortIndicator(col, order)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_student(self):
        dlg = AddStudentDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        name, sid, grade = dlg.get_values()
        try:
            db.add_student(name, sid, grade)
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _import_spreadsheet(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "",
            "Spreadsheets & CSV (*.csv *.tsv *.xlsx *.xls *.ods);;All Files (*)"
        )
        if not path:
            return
        try:
            rows = _read_spreadsheet(path)
        except ImportError as e:
            QMessageBox.critical(
                self, "Missing Library",
                f"Required library not installed:\n{e}\n\n"
                "Run: pip install openpyxl xlrd"
            )
            return
        except Exception as e:
            QMessageBox.critical(self, "Read Error", str(e))
            return

        added, skipped = 0, 0
        with db.get_connection() as conn:
            for row in rows:
                name = row.get("Name", "").strip()
                sid = row.get("Student ID", "").strip()
                grade = row.get("Grade", "").strip()
                if not name or not sid:
                    skipped += 1
                    continue
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO students (name, student_id, grade) VALUES (?, ?, ?)",
                        (name, sid, grade),
                    )
                    added += 1
                except Exception:
                    skipped += 1

        self.refresh()
        QMessageBox.information(
            self, "Import Complete",
            f"Added: {added}  Skipped/Errors: {skipped}"
        )

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
