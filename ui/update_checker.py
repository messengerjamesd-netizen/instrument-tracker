import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
import json

from PySide6.QtCore import QThread, Signal


class UpdateChecker(QThread):
    """
    Background thread that checks GitHub releases for a newer version.
    Emits update_available(new_version, download_url) if one is found.
    Silently ignores all network/parse errors — update check is best-effort.
    """

    update_available = Signal(str, str)  # (new_version, asset_download_url)

    def __init__(self, current_version: str, repo: str, parent=None):
        super().__init__(parent)
        self._current = current_version
        self._repo = repo

    def run(self):
        try:
            url = f"https://api.github.com/repos/{self._repo}/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "InstrumentTracker"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())

            tag = data.get("tag_name", "").lstrip("v")
            if not tag or not self._is_newer(tag, self._current):
                return

            # Find the installer asset (.exe)
            download_url = ""
            for asset in data.get("assets", []):
                if asset.get("name", "").lower().endswith(".exe"):
                    download_url = asset.get("browser_download_url", "")
                    break

            if download_url:
                self.update_available.emit(tag, download_url)

        except Exception:
            pass  # network unavailable, rate limited, repo not found, etc.

    @staticmethod
    def _is_newer(remote: str, current: str) -> bool:
        def parts(v):
            try:
                return tuple(int(x) for x in v.split("."))
            except ValueError:
                return (0,)
        return parts(remote) > parts(current)


def download_and_launch(download_url: str, parent=None):
    """
    Download the installer to a temp file and launch it.
    Returns True if launched successfully, False otherwise.
    """
    from PySide6.QtWidgets import QProgressDialog, QMessageBox
    from PySide6.QtCore import Qt

    tmp_dir = tempfile.mkdtemp(prefix="InstrumentTrackerUpdate_")
    tmp_path = os.path.join(tmp_dir, "InstrumentTracker_Setup.exe")

    progress = QProgressDialog("Downloading update…", "Cancel", 0, 100, parent)
    progress.setWindowTitle("Downloading Update")
    progress.setWindowModality(Qt.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)

    cancelled = [False]

    def _reporthook(block_num, block_size, total_size):
        if progress.wasCanceled():
            cancelled[0] = True
            raise Exception("Cancelled")
        if total_size > 0:
            pct = min(100, int(block_num * block_size * 100 / total_size))
            progress.setValue(pct)
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    try:
        urllib.request.urlretrieve(download_url, tmp_path, _reporthook)
        progress.setValue(100)
        progress.close()
    except Exception as e:
        progress.close()
        if not cancelled[0]:
            QMessageBox.critical(parent, "Download Failed", f"Could not download update:\n{e}")
        return False

    try:
        subprocess.Popen([tmp_path])
        return True
    except Exception as e:
        QMessageBox.critical(parent, "Launch Failed",
                             f"Downloaded the installer but could not launch it:\n{e}\n\n"
                             f"You can run it manually:\n{tmp_path}")
        return False
