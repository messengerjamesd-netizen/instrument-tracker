import json
import re
import urllib.request

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
)
import config as cfg


class WhatsNewFetcher(QThread):
    finished = Signal(str)  # emits markdown body, empty string on failure

    def __init__(self, version: str, repo: str, parent=None):
        super().__init__(parent)
        self._version = version
        self._repo = repo

    def run(self):
        try:
            url = f"https://api.github.com/repos/{self._repo}/releases/tags/v{self._version}"
            req = urllib.request.Request(url, headers={"User-Agent": "InstrumentTracker"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            self.finished.emit(data.get("body", ""))
        except Exception:
            self.finished.emit("")


def _md_to_html(md: str) -> str:
    html_lines = []
    in_ul = False

    def _inline(text):
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
        return text

    for line in md.splitlines():
        if line.startswith("### "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<h4>{_inline(line[4:])}</h4>")
        elif line.startswith("## "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<h3>{_inline(line[3:])}</h3>")
        elif line.startswith("# "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<h2>{_inline(line[2:])}</h2>")
        elif re.match(r"^[-*] ", line):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{_inline(line[2:])}</li>")
        elif not line.strip():
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append("<br>")
        else:
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<p>{_inline(line)}</p>")

    if in_ul:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


class WhatsNewDialog(QDialog):
    def __init__(self, version: str, repo: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"What's New in v{version}")
        self.setMinimumSize(500, 400)
        self.resize(580, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel(f"<b>What's New in v{version}</b>"))

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setHtml(
            "<p style='color: #7a8fa8; font-style: italic;'>Loading release notes…</p>"
        )
        layout.addWidget(self._browser)

        h = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        h.addStretch()
        h.addWidget(close_btn)
        layout.addLayout(h)

        # Mark as seen immediately so it won't show again next launch
        c = cfg.load_config()
        c["last_seen_whats_new"] = version
        cfg.save_config(c)

        self._fetcher = WhatsNewFetcher(version, repo, self)
        self._fetcher.finished.connect(self._on_fetched)
        self._fetcher.start()

    def _on_fetched(self, body: str):
        if body:
            self._browser.setHtml(_md_to_html(body))
        else:
            self._browser.setHtml(
                "<p style='color: #7a8fa8; font-style: italic;'>"
                "Could not load release notes — check GitHub for the latest changes."
                "</p>"
            )
