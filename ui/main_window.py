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
            lambda iid: (self._navigate(1), instruments_page.show_instrument(iid))
        )
        students_page.navigate_to_instrument.connect(
            lambda iid: (self._navigate(1), instruments_page.show_instrument(iid))
        )
        instruments_page.navigate_to_student.connect(
            lambda sid: (self._navigate(2), students_page.show_student(sid))
        )

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

    def start_update_check(self, current_version: str, repo: str):
        from ui.update_checker import UpdateChecker
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
