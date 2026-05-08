from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFrame, QStackedWidget, QLabel,
)

from ui.actions_tab import ActionsTab
from ui.instruments_page import InstrumentsPage
from ui.students_page import StudentsPage
from ui.contracts_tab import ContractsTab
from ui.reports_tab import ReportsTab
from ui.options_tab import OptionsTab


_NAV = [
    ("⚡", "Check In / Out", ActionsTab),
    ("🎺", "Instruments",    InstrumentsPage),
    ("🎓", "Students",       StudentsPage),
    ("📄", "Contracts",      ContractsTab),
    None,
    ("📊", "Reports",        ReportsTab),
    None,
    ("⚙",  "Options",        OptionsTab),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Band Room Instrument Tracker")
        self.setMinimumSize(600, 400)
        self.resize(1200, 780)

        root = QWidget()
        self.setCentralWidget(root)
        root_v = QVBoxLayout(root)
        root_v.setContentsMargins(0, 0, 0, 0)
        root_v.setSpacing(0)

        # Update banner (hidden until an update is found)
        self._update_banner = self._build_update_banner()
        root_v.addWidget(self._update_banner)

        body = QWidget()
        outer = QHBoxLayout(body)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        root_v.addWidget(body, 1)

        self._items = []   # (btn, page_widget)
        self._stack = QStackedWidget()

        outer.addWidget(self._build_sidebar())
        outer.addWidget(self._stack, 1)

        # Cross-page navigation
        actions_tab     = self._items[0][1]
        instruments_page = self._items[1][1]
        students_page    = self._items[2][1]
        actions_tab.navigate_to_instrument.connect(
            lambda iid: (self._navigate(1), instruments_page.show_instrument([iid]))
        )
        students_page.navigate_to_instrument.connect(
            lambda ids: (self._navigate(1), instruments_page.show_instrument(ids))
        )
        instruments_page.navigate_to_student.connect(
            lambda ids: (self._navigate(2), students_page.show_student(ids))
        )
        instruments_page.status_changed.connect(actions_tab._refresh_activity)

        self._current_version = ""
        self._pending_download_url = ""

        self._navigate(0)

    # ── Update banner ─────────────────────────────────────────────────────────

    def _build_update_banner(self):
        banner = QFrame()
        banner.setObjectName("update_banner")
        banner.setStyleSheet(
            "QFrame#update_banner {"
            "  background-color: #1e4a8a;"
            "  border-bottom: 1px solid #2d6bc4;"
            "}"
        )
        banner.setVisible(False)

        h = QHBoxLayout(banner)
        h.setContentsMargins(14, 6, 14, 6)
        h.setSpacing(10)

        self._update_label = QLabel("")
        self._update_label.setStyleSheet("color: #e8f0ff; font-weight: bold;")
        h.addWidget(self._update_label, 1)

        update_btn = QPushButton("Update Now")
        update_btn.setObjectName("primary")
        update_btn.setMinimumHeight(28)
        update_btn.clicked.connect(self._do_update)
        h.addWidget(update_btn)

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setMinimumHeight(28)
        dismiss_btn.clicked.connect(lambda: banner.setVisible(False))
        h.addWidget(dismiss_btn)

        return banner

    def start_onboarding_tour(self):
        from ui.onboarding import OnboardingOverlay, OnboardingStep
        from PySide6.QtWidgets import QTableWidgetItem
        from PySide6.QtGui import QColor
        from PySide6.QtCore import Qt, QRect, QPoint

        actions = self._items[0][1]
        instruments = self._items[1][1]
        students = self._items[2][1]

        def _populate_fake_instruments():
            t = instruments.table
            if t.rowCount() > 0:
                return
            rows = [
                # Name, Model, Serial, Status, Student, CO date, CI date
                ("Trumpet",        "Bach TR300",        "T-0042", "Checked Out",    "Emily Davis",    "2025-09-04", ""),
                ("Clarinet",       "Buffet E11",        "C-0118", "Available",      "",               "",           "2025-06-10"),
                ("Flute",          "Yamaha YFL-222",    "F-0031", "Out for Repair", "",               "",           ""),
                ("Alto Saxophone", "Conn-Selmer AS700", "S-0079", "Checked Out",    "Marcus Johnson", "2025-09-02", ""),
            ]
            status_colors = {
                "Available":      QColor(0, 200, 0),
                "Checked Out":    QColor(Qt.yellow),
                "Out for Repair": QColor("#e87d2f"),
            }
            t.setSortingEnabled(False)
            t.setRowCount(len(rows))
            for r, (name, model, serial, status, student, co, ci) in enumerate(rows):
                for c, val in enumerate(["", name, model, serial, status, student, co, ci]):
                    item = QTableWidgetItem(val)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    t.setItem(r, c, item)
                if status in status_colors:
                    t.item(r, 4).setForeground(status_colors[status])
                if student:
                    t.item(r, 5).setForeground(QColor("#7eb8f7"))
            t.setSortingEnabled(True)

        def _populate_fake_students():
            t = students.table
            if t.rowCount() > 0:
                return
            rows = [
                # Name, Student ID, Grade, Instrument
                ("Emily Davis",    "S1001", "10", "Trumpet"),
                ("Marcus Johnson", "S1002", "9",  "Alto Saxophone"),
                ("Olivia Chen",    "S1003", "11", "—"),
                ("Tyler Brooks",   "S1004", "10", "—"),
            ]
            t.setSortingEnabled(False)
            t.setRowCount(len(rows))
            for r, (name, sid, grade, instr) in enumerate(rows):
                for c, val in enumerate(["", name, sid, grade, instr]):
                    item = QTableWidgetItem(val)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    t.setItem(r, c, item)
            t.setSortingEnabled(True)

        def _col_rect(table, col):
            """QRect for a table column (header + data rows) in main-window coords."""
            vp = table.viewport()
            x = table.columnViewportPosition(col)
            hdr_h = table.horizontalHeader().height()
            tl = vp.mapTo(self, QPoint(x, 0))
            return QRect(tl.x(), tl.y() - hdr_h, table.columnWidth(col), vp.height() + hdr_h)

        def _rows_rect(table, first_row, last_row):
            """QRect for a range of rows (all columns) in main-window coords."""
            if table.rowCount() == 0:
                return None
            last_row = min(last_row, table.rowCount() - 1)
            vp = table.viewport()
            y0 = table.rowViewportPosition(first_row)
            y1 = table.rowViewportPosition(last_row) + table.rowHeight(last_row)
            tl = vp.mapTo(self, QPoint(0, y0))
            return QRect(tl.x(), tl.y(), vp.width(), y1 - y0)

        def _on_finish():
            if hasattr(instruments, "refresh"):
                instruments.refresh()
            if hasattr(students, "refresh"):
                students.refresh()

        steps = [
            OnboardingStep(
                "Welcome to Instrument Tracker!",
                "This quick tour covers the key features. You can skip at any time — "
                "or restart the tour later from Options.",
                tab_index=0,
            ),
            OnboardingStep(
                "Checking Instruments In & Out",
                "Use Camera mode to scan a QR code with your webcam, or switch to "
                "Manual / Scanner to type a code or use a barcode gun.\n\n"
                "Click Check Out or Check In to complete the action.",
                tab_index=0,
                highlight_fn=lambda: [actions._mode_toggle, actions._co_card, actions._ci_card],
            ),
            OnboardingStep(
                "Change an Instrument's Status",
                "Right-click any row in the Status column to change its status — "
                "check out, check in, mark for repair, summer hold, and more.",
                tab_index=1,
                highlight_fn=lambda: [_col_rect(instruments.table, 4)],
                on_enter=_populate_fake_instruments,
            ),
            OnboardingStep(
                "View Full History & Contracts",
                "Double-click any instrument row to open its full history and manage "
                "contracts attached to it.",
                tab_index=1,
                highlight_fn=lambda: [r for r in [_rows_rect(instruments.table, 0, 1)] if r],
                on_enter=_populate_fake_instruments,
            ),
            OnboardingStep(
                "Bulk Actions & Keyboard Shortcuts",
                "Ctrl+click or Shift+click to select multiple rows, then use the action "
                "buttons to check in/out or change status in bulk.\n\n"
                "Keyboard shortcuts (table must be focused):\n"
                "  Delete — remove selected\n"
                "  Enter or F2 — edit selected",
                tab_index=1,
                highlight_fn=lambda: [r for r in [_rows_rect(instruments.table, 0, 3)] if r],
                on_enter=_populate_fake_instruments,
            ),
            OnboardingStep(
                "Clickable Names",
                "Names shown in blue are clickable links — click a student name to jump "
                "to their record, or click an instrument name to open its detail.",
                tab_index=1,
                highlight_fn=lambda: [_col_rect(instruments.table, 5)],
                on_enter=_populate_fake_instruments,
            ),
            OnboardingStep(
                "Student History & Contracts",
                "Double-click a student to open their full instrument history. "
                "From there you can also add contracts for any instrument they have checked out.",
                tab_index=2,
                highlight_fn=lambda: [r for r in [_rows_rect(students.table, 0, 3)] if r],
                on_enter=_populate_fake_students,
            ),
            OnboardingStep(
                "You're all set!",
                "Find these tips anytime with the ? button on the Instruments or Students page.\n\n"
                "You can restart this tour from Options.",
            ),
        ]
        self._tour = OnboardingOverlay(steps, self, on_finish=_on_finish)

    def check_whats_new(self, version: str, repo: str):
        import config as cfg
        from PySide6.QtCore import QTimer
        c = cfg.load_config()
        if c.get("last_seen_whats_new") != version:
            from ui.whats_new_checker import WhatsNewDialog
            QTimer.singleShot(500, lambda: WhatsNewDialog(version, repo, self).exec())

    def start_update_check(self, current_version: str, repo: str):
        from ui.update_checker import UpdateChecker
        self._current_version = current_version
        self._checker = UpdateChecker(current_version, repo, self)
        self._checker.update_available.connect(self._on_update_available)
        self._checker.start()

    def _on_update_available(self, new_version: str, download_url: str):
        self._pending_download_url = download_url
        self._update_label.setText(
            f"🔔  Version {new_version} is available — you're on {self._current_version}"
        )
        self._update_banner.setVisible(True)

    def _do_update(self):
        from PySide6.QtWidgets import QApplication
        from ui.update_checker import download_and_launch
        url = getattr(self, "_pending_download_url", "")
        if not url:
            return
        if download_and_launch(url, self):
            QApplication.quit()

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(160)

        v = QVBoxLayout(sidebar)
        v.setContentsMargins(0, 14, 0, 14)
        v.setSpacing(0)

        for item in _NAV:
            if item is None:
                div = QFrame()
                div.setObjectName("sidebar_divider")
                div.setFixedHeight(1)
                v.addSpacing(6)
                v.addWidget(div)
                v.addSpacing(6)
                continue

            icon, label, page_cls = item
            page = page_cls()
            idx = len(self._items)

            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("sidebar_item")
            btn.setCheckable(True)
            btn.setMinimumHeight(42)
            btn.clicked.connect(lambda _, i=idx: self._navigate(i))
            v.addWidget(btn)

            self._stack.addWidget(page)
            self._items.append((btn, page))

        v.addStretch()
        return sidebar

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate(self, idx):
        for i, (btn, _) in enumerate(self._items):
            btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)
        page = self._stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()
