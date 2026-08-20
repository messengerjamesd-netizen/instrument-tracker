from PySide6.QtCore import Qt, Signal, QEvent, QItemSelection, QItemSelectionModel, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QFileDialog, QFrame,
    QCheckBox, QScrollArea,
)

import database as db
import config as cfg
from ui.student_detail_dialog import StudentDetailDialog
from ui.instruments_page import _read_spreadsheet, _find_col


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
    def __init__(self, student, parent=None, position=None, total=None):
        super().__init__(parent)
        title = "Edit Student"
        if position and total and total > 1:
            title += f"  ({position} of {total})"
        self.setWindowTitle(title)
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


class AdvanceGradesDialog(QDialog):
    """Bulk-promote every student's grade by one at the start of a new year."""

    def __init__(self, students, top_grade, parent=None):
        super().__init__(parent)
        self.top_grade = top_grade
        self.setWindowTitle("Advance Grades")
        self.setMinimumSize(480, 480)
        self._checkboxes = []  # (checkbox, student, new_grade_int_or_None)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel(
            "Every checked student's grade will go up by one.\n"
            f"Students at grade {top_grade} will graduate — they'll be archived instead."
        ))

        sel_row = QHBoxLayout()
        all_btn = QPushButton("Select All")
        all_btn.setMinimumHeight(28)
        all_btn.clicked.connect(lambda: self._set_all(True))
        none_btn = QPushButton("Deselect All")
        none_btn.setMinimumHeight(28)
        none_btn.clicked.connect(lambda: self._set_all(False))
        sel_row.addWidget(all_btn)
        sel_row.addWidget(none_btn)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        list_widget = QWidget()
        self._list_layout = QVBoxLayout(list_widget)
        self._list_layout.setSpacing(4)
        self._list_layout.setContentsMargins(4, 4, 4, 4)

        skipped = 0
        for s in students:
            grade_text = (s["grade"] or "").strip()
            try:
                grade_num = int(grade_text)
            except ValueError:
                skipped += 1
                continue
            if grade_num >= top_grade:
                label = f"{s['name']} ({s['student_id']})  —  Grade {grade_num} → Graduating (will be archived)"
            else:
                label = f"{s['name']} ({s['student_id']})  —  Grade {grade_num} → {grade_num + 1}"
            cb = QCheckBox(label)
            cb.setChecked(True)
            if grade_num >= top_grade:
                cb.setStyleSheet("color: #d98c3f;")
            self._list_layout.addWidget(cb)
            self._checkboxes.append((cb, s, grade_num))

        self._list_layout.addStretch()
        scroll.setWidget(list_widget)
        layout.addWidget(scroll, 1)

        if skipped:
            note = QLabel(
                f"{skipped} student{'s' if skipped != 1 else ''} skipped — "
                "no numeric grade set. Edit them individually if needed."
            )
            note.setStyleSheet("color: #5a7aaa; font-style: italic;")
            note.setWordWrap(True)
            layout.addWidget(note)

        if not self._checkboxes:
            layout.addWidget(QLabel("No students with a numeric grade to advance."))

        btns = QDialogButtonBox()
        apply_btn = btns.addButton("Apply", QDialogButtonBox.AcceptRole)
        apply_btn.setObjectName("primary")
        apply_btn.setEnabled(bool(self._checkboxes))
        btns.addButton("Cancel", QDialogButtonBox.RejectRole)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _set_all(self, checked):
        for cb, _, _ in self._checkboxes:
            cb.setChecked(checked)

    def get_selected(self):
        """Returns (to_promote, to_graduate) — lists of student rows."""
        to_promote, to_graduate = [], []
        for cb, student, grade_num in self._checkboxes:
            if not cb.isChecked():
                continue
            if grade_num >= self.top_grade:
                to_graduate.append(student)
            else:
                to_promote.append(student)
        return to_promote, to_graduate


# ── Main page ─────────────────────────────────────────────────────────────────

class StudentsPage(QWidget):
    navigate_to_instrument = Signal(object)  # emits list of instrument IDs

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._view_archived = False
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
            "Supports .csv, .tsv, .xlsx, .xls"
        )
        import_btn.clicked.connect(self._import_spreadsheet)
        toolbar.addWidget(import_btn)

        add_btn = QPushButton("+ Add Student")
        add_btn.setObjectName("primary")
        add_btn.setMinimumHeight(32)
        add_btn.clicked.connect(self._add_student)
        toolbar.addWidget(add_btn)

        toolbar.addSpacing(12)
        self._archived_toggle = QPushButton("Show Archived")
        self._archived_toggle.setCheckable(True)
        self._archived_toggle.setMinimumHeight(32)
        self._archived_toggle.toggled.connect(self._toggle_view_archived)
        toolbar.addWidget(self._archived_toggle)

        help_btn = QPushButton("?")
        help_btn.setMinimumHeight(32)
        help_btn.setFixedWidth(32)
        help_btn.setFocusPolicy(Qt.NoFocus)
        help_btn.setStyleSheet("QPushButton { color: #c8d8f0; font-weight: bold; padding: 0px; }")
        help_btn.clicked.connect(lambda: QMessageBox.information(
            self, "Tips",
            "Double-click a row to view a student's full instrument history.\n\n"
            "Ctrl+click or Shift+click to select multiple rows for bulk actions.\n\n"
            "Advance Grades (in Options → Student Records) bumps every student's "
            "grade by one for the new year — students at the configured top "
            "grade are archived instead (graduated).\n\n"
            "Archive removes a student from active lists and pickers without "
            "deleting their history. Toggle \"Show Archived\" to view, restore, "
            "or permanently delete archived students.\n\n"
            "Keyboard shortcuts (with table focused):\n"
            "  Delete — archive selected student(s) (or permanently delete, "
            "when viewing archived students)\n"
            "  Enter or F2 — edit selected student\n\n"
            "Instrument names shown in blue are clickable — "
            "click to jump directly to that instrument's record."
        ))
        toolbar.addWidget(help_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Student ID", "Grade", "Instrument"])
        self.table.setColumnHidden(0, True)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionsClickable(True)
        self.table.setSortingEnabled(True)
        hdr.setSortIndicator(1, Qt.AscendingOrder)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._view_history)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        self.table.cellEntered.connect(self._on_cell_hovered)
        self.table.viewport().installEventFilter(self)
        self._hovered_link_cell = None
        layout.addWidget(self.table)

        self.row_count_label = QLabel("")
        self.row_count_label.setObjectName("status")
        layout.addWidget(self.row_count_label)

        # Bottom action bar — adaptive (single row wide, two rows narrow)
        self._selection_buttons = []

        def mk(text, slot, danger=False, fixed=False, needs_selection=False):
            btn = QPushButton(text)
            btn.setMinimumHeight(34)
            btn.setSizePolicy(
                QSizePolicy.Preferred if fixed else QSizePolicy.Expanding,
                QSizePolicy.Fixed)
            if danger:
                btn.setObjectName("danger")
            btn.clicked.connect(slot)
            if needs_selection:
                btn.setEnabled(False)
                self._selection_buttons.append(btn)
            return btn

        def sep():
            f = QFrame()
            f.setFrameShape(QFrame.VLine)
            f.setFrameShadow(QFrame.Plain)
            return f

        self._view_toggle_buttons = []  # (button, visible_when_archived)

        self._wide_bar = QWidget()
        self._wide_bar.setObjectName("bottom_bar")
        wide = QHBoxLayout(self._wide_bar)
        wide.setContentsMargins(8, 6, 8, 6)
        wide.setSpacing(8)
        wide.addWidget(mk("Edit", self._edit_student, fixed=True, needs_selection=True))
        archive_btn = mk("Archive", self._archive_student, fixed=True, needs_selection=True)
        wide.addWidget(archive_btn)
        unarchive_btn = mk("Unarchive", self._unarchive_student, fixed=True, needs_selection=True)
        wide.addWidget(unarchive_btn)
        delete_btn = mk("Delete", self._delete_student, danger=True, fixed=True, needs_selection=True)
        wide.addWidget(delete_btn)
        wide.addWidget(sep())
        wide.addWidget(mk("History", self._view_history, needs_selection=True))
        self._view_toggle_buttons += [
            (archive_btn, False), (unarchive_btn, True), (delete_btn, True),
        ]

        self._narrow_bar = QWidget()
        self._narrow_bar.setObjectName("bottom_bar")
        narrow = QVBoxLayout(self._narrow_bar)
        narrow.setContentsMargins(8, 4, 8, 4)
        narrow.setSpacing(4)
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(mk("Edit", self._edit_student, needs_selection=True))
        n_archive_btn = mk("Archive", self._archive_student, needs_selection=True)
        row1.addWidget(n_archive_btn)
        n_unarchive_btn = mk("Unarchive", self._unarchive_student, needs_selection=True)
        row1.addWidget(n_unarchive_btn)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        n_delete_btn = mk("Delete", self._delete_student, danger=True, needs_selection=True)
        row2.addWidget(n_delete_btn)
        row2.addWidget(mk("History", self._view_history, needs_selection=True))
        narrow.addLayout(row1)
        narrow.addLayout(row2)
        self._narrow_bar.hide()
        self._view_toggle_buttons += [
            (n_archive_btn, False), (n_unarchive_btn, True), (n_delete_btn, True),
        ]

        layout.addWidget(self._wide_bar)
        layout.addWidget(self._narrow_bar)
        self._update_view_buttons()

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        narrow = event.size().width() < 500
        self._wide_bar.setVisible(not narrow)
        self._narrow_bar.setVisible(narrow)

    def keyPressEvent(self, event):
        if self.table.hasFocus():
            if event.key() == Qt.Key_Delete:
                self._delete_student() if self._view_archived else self._archive_student()
                return
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_F2):
                self._edit_student()
                return
        super().keyPressEvent(event)

    # ── View state ────────────────────────────────────────────────────────────

    def _update_view_buttons(self):
        for btn, visible_when_archived in self._view_toggle_buttons:
            btn.setVisible(visible_when_archived == self._view_archived)

    def _toggle_view_archived(self, checked):
        self._view_archived = checked
        self._archived_toggle.setText("Show Active" if checked else "Show Archived")
        self._update_view_buttons()
        self.refresh()

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self):
        self._data = db.get_student_roster(archived=self._view_archived)
        self._apply_filter()

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
                all_instr_names = s["all_instrument_names"] or ""
                if count > 1 and all_instr_names:
                    instr_item.setToolTip(all_instr_names.replace(", ", "\n"))
                else:
                    instr_item.setToolTip("Click to view this instrument")
            else:
                instr_item = QTableWidgetItem("—")
            instr_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            instr_item.setData(Qt.UserRole, s["id"])
            instr_item.setData(Qt.UserRole + 1, instrument_id)
            all_ids_raw = s["all_instrument_ids"] or ""
            instr_item.setData(Qt.UserRole + 2, all_ids_raw)
            self.table.setItem(r, 4, instr_item)

        self.table.setSortingEnabled(True)

        total = len(self._data)
        shown = len(rows)
        suffix = " (archived)" if self._view_archived else ""
        if total == 0:
            if self._view_archived:
                self.row_count_label.setText("No archived students.")
            else:
                self.row_count_label.setText(
                    "No students yet — click Add Student or Import Spreadsheet to get started."
                )
        elif shown == 0:
            self.row_count_label.setText("No students match your search.")
        elif shown == total:
            self.row_count_label.setText(
                f"Showing {shown} student{'s' if shown != 1 else ''}{suffix}"
            )
        else:
            self.row_count_label.setText(f"Showing {shown} of {total} students{suffix}")

    def _apply_filter(self):
        text = self.search_box.text().lower()
        if not text:
            self._populate(self._data)
            return
        filtered = [
            s for s in self._data
            if any(
                text in str(v or "").lower()
                for v in [s["name"], s["student_id"], s["grade"],
                          s["all_instrument_names"]]
            )
        ]
        self._populate(filtered)

    def show_student(self, student_ids):
        if isinstance(student_ids, int):
            student_ids = [student_ids]
        id_set = set(student_ids)

        # If none of the target students are in the active roster, they may
        # have been archived — switch views so the link still resolves.
        if id_set and not (id_set & {s["id"] for s in db.get_student_roster(archived=False)}):
            if id_set & {s["id"] for s in db.get_student_roster(archived=True)}:
                self._archived_toggle.setChecked(True)  # triggers _toggle_view_archived

        self.search_box.clear()
        self.refresh()
        first_item = None
        found = 0
        sel_model = self.table.selectionModel()
        sel_model.clearSelection()
        ncols = self.table.columnCount()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) in id_set:
                sel = QItemSelection(
                    self.table.model().index(row, 0),
                    self.table.model().index(row, ncols - 1),
                )
                sel_model.select(sel, QItemSelectionModel.Select)
                if first_item is None:
                    first_item = item
                found += 1
        if first_item:
            self.table.scrollToItem(first_item)
        if found > 1:
            prev = self.row_count_label.text()
            self.row_count_label.setText(
                f"{found} students sharing this instrument — highlighted above"
            )
            QTimer.singleShot(5000, lambda: self.row_count_label.setText(prev))

    def _on_cell_hovered(self, row, col):
        self._clear_link_hover()
        item = self.table.item(row, col)
        if col == 4 and item and item.data(Qt.UserRole + 1):
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            self._hovered_link_cell = (row, col)
            self.table.viewport().setCursor(Qt.PointingHandCursor)

    def _clear_link_hover(self):
        if self._hovered_link_cell:
            r, c = self._hovered_link_cell
            item = self.table.item(r, c)
            if item:
                font = item.font()
                font.setBold(False)
                item.setFont(font)
            self._hovered_link_cell = None
            self.table.viewport().unsetCursor()

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
        all_ids_raw = item.data(Qt.UserRole + 2) or ""
        if all_ids_raw:
            ids = [int(x) for x in all_ids_raw.split(",") if x.strip()]
            if ids:
                self.navigate_to_instrument.emit(ids)
                return
        instrument_id = item.data(Qt.UserRole + 1)
        if instrument_id:
            self.navigate_to_instrument.emit([instrument_id])

    def _selected_student_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _selected_student_ids(self):
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        ids = []
        for row in sorted(rows):
            item = self.table.item(row, 0)
            if item:
                ids.append(item.data(Qt.UserRole))
        return ids

    # ── Selection state ───────────────────────────────────────────────────────

    def _on_selection_changed(self):
        has_sel = self.table.selectionModel().hasSelection()
        for btn in self._selection_buttons:
            btn.setEnabled(has_sel)

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
            "Spreadsheets & CSV (*.csv *.tsv *.xlsx *.xls);;All Files (*)"
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
                name = _find_col(row,
                    "Name", "Student Name", "Full Name", "Student",
                    "Last Name", "First Name")
                sid = _find_col(row,
                    "Student ID", "Student #", "Student No", "Student Number",
                    "ID", "ID Number", "StudentID", "Student_ID")
                grade = _find_col(row,
                    "Grade", "Grade Level", "Year", "Class", "Grade/Year")
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
        sids = self._selected_student_ids()
        if not sids:
            QMessageBox.information(self, "No Selection", "Select one or more students first.")
            return
        edited, skipped = 0, 0
        for i, sid in enumerate(sids, start=1):
            student = db.get_student_by_id(sid)
            if not student:
                continue
            dlg = EditStudentDialog(student, self, position=i, total=len(sids))
            if dlg.exec() != QDialog.Accepted:
                skipped += 1
                continue
            name, student_id, grade = dlg.get_values()
            if not name or not student_id:
                QMessageBox.warning(self, "Required", "Name and Student ID are required.")
                skipped += 1
                continue
            try:
                db.update_student(sid, name, student_id, grade)
                edited += 1
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
                skipped += 1
        self.refresh()
        if len(sids) > 1:
            msg = f"Updated {edited} student{'s' if edited != 1 else ''}."
            if skipped:
                msg += f"\n{skipped} skipped or cancelled."
            QMessageBox.information(self, "Done", msg)

    def _view_history(self):
        sid = self._selected_student_id()
        if sid is None:
            QMessageBox.information(self, "No Selection", "Select a student first.")
            return
        dlg = StudentDetailDialog(sid, self)
        dlg.instruments_changed.connect(self.refresh)
        dlg.exec()

    def _delete_student(self):
        sids = self._selected_student_ids()
        if not sids:
            QMessageBox.information(self, "No Selection", "Select one or more students first.")
            return
        if len(sids) == 1:
            student = db.get_student_by_id(sids[0])
            if not student:
                return
            msg = (f"Delete student {student['name']} ({student['student_id']})?\n\n"
                   "This will also delete all their contracts.")
        else:
            students = [db.get_student_by_id(s) for s in sids]
            names = "\n".join(
                f"  • {s['name']} ({s['student_id']})"
                for s in students if s
            )
            msg = (f"Delete {len(sids)} students?\n\n{names}\n\n"
                   "This will also delete all their contracts.")
        reply = QMessageBox.warning(self, "Confirm Delete", msg,
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for sid in sids:
                db.delete_student(sid)
            self.refresh()

    def _archive_student(self):
        sids = self._selected_student_ids()
        if not sids:
            QMessageBox.information(self, "No Selection", "Select one or more students first.")
            return

        blocked, archivable = [], []
        for sid in sids:
            student = db.get_student_by_id(sid)
            if not student:
                continue
            if db.get_checked_out_for_student(sid):
                blocked.append(student)
            else:
                archivable.append(student)

        if blocked:
            names = "\n".join(f"  • {s['name']} ({s['student_id']})" for s in blocked)
            QMessageBox.warning(
                self, "Instruments Checked Out",
                f"These student(s) still have an instrument checked out — "
                f"check it in before archiving:\n\n{names}"
            )

        if not archivable:
            return

        if len(archivable) == 1:
            s = archivable[0]
            msg = (f"Archive {s['name']} ({s['student_id']})?\n\n"
                   "They'll be hidden from active lists and checkout/contract "
                   "pickers, but their history is kept. You can unarchive them later.")
        else:
            names = "\n".join(f"  • {s['name']} ({s['student_id']})" for s in archivable)
            msg = (f"Archive {len(archivable)} students?\n\n{names}\n\n"
                   "They'll be hidden from active lists and checkout/contract "
                   "pickers, but their history is kept. You can unarchive them later.")
        reply = QMessageBox.question(self, "Confirm Archive", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for s in archivable:
                db.archive_student(s["id"])
            self.refresh()

    def _unarchive_student(self):
        sids = self._selected_student_ids()
        if not sids:
            QMessageBox.information(self, "No Selection", "Select one or more students first.")
            return
        for sid in sids:
            db.unarchive_student(sid)
        self.refresh()

    def _advance_grades(self):
        top_grade = cfg.load_config().get("top_grade", 12)
        students = db.get_all_students()
        if not students:
            QMessageBox.information(self, "No Students", "No active students in the system yet.")
            return
        dlg = AdvanceGradesDialog(students, top_grade, self)
        if dlg.exec() != QDialog.Accepted:
            return
        to_promote, to_graduate = dlg.get_selected()

        promoted = 0
        for s in to_promote:
            new_grade = str(int(s["grade"]) + 1)
            db.update_student(s["id"], s["name"], s["student_id"], new_grade)
            promoted += 1

        graduated, blocked = 0, []
        for s in to_graduate:
            checked_out = db.get_checked_out_for_student(s["id"])
            if checked_out:
                blocked.append((s, checked_out))
                continue
            db.archive_student(s["id"])
            graduated += 1

        self.refresh()

        msg = f"Promoted {promoted} student{'s' if promoted != 1 else ''}."
        if graduated:
            msg += f"\nArchived {graduated} graduating student{'s' if graduated != 1 else ''}."
        QMessageBox.information(self, "Advance Grades Complete", msg)

        if blocked:
            lines = []
            for s, instruments in blocked:
                instr_names = ", ".join(i["name"] for i in instruments)
                lines.append(f"  • {s['name']} ({s['student_id']}) — still has: {instr_names}")
            warn_msg = (
                f"{len(blocked)} student{'s' if len(blocked) != 1 else ''} at grade "
                f"{top_grade} were NOT advanced or archived, because they still have "
                f"an instrument checked out:\n\n" + "\n".join(lines) +
                "\n\nCheck those instruments in, then archive these students manually "
                "from the Students page (or re-run Advance Grades)."
            )
            QMessageBox.warning(self, "Students Not Advanced", warn_msg)
