import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QDialogButtonBox, QSizePolicy,
)
from ui.camera_manager import CameraManager, CameraWorker


def _frame_to_pixmap(frame, target_size):
    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.shape[2] == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    img = QImage(rgb.tobytes(), w, h, w * ch, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(img).scaled(
        target_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class CameraDialog(QDialog):
    """Live camera feed — closes automatically when a QR code is detected."""

    def __init__(self, parent=None, title="Scan QR Code"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(640, 520)
        self.resize(700, 560)

        self._mgr = CameraManager.instance()
        self._worker: CameraWorker | None = None
        self.scanned_value = None
        self._ready = False

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        cam_row = QHBoxLayout()
        cam_row.addWidget(QLabel("Camera:"))
        self.camera_combo = QComboBox()
        self.camera_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.camera_combo.currentIndexChanged.connect(self._on_combo_changed)
        cam_row.addWidget(self.camera_combo)
        layout.addLayout(cam_row)

        self.preview = QLabel("Initializing camera…")
        self.preview.setObjectName("camera_preview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview.setMinimumHeight(360)
        self.preview.setStyleSheet("color: #5a7aaa; font-size: 15px;")
        layout.addWidget(self.preview)

        self.status_label = QLabel("Starting up…")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        btn_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ready:
            self._ready = True
            QTimer.singleShot(60, self._init_cameras)

    def _init_cameras(self):
        cameras = self._mgr.get_camera_list()
        if not cameras:
            self.status_label.setText("No cameras found.")
            self.preview.setText("No cameras found.")
            return

        self.camera_combo.blockSignals(True)
        for idx, name in cameras:
            self.camera_combo.addItem(name, idx)

        if self._mgr.cam_index is not None:
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i) == self._mgr.cam_index:
                    self.camera_combo.setCurrentIndex(i)
                    break

        self.camera_combo.blockSignals(False)
        self._start_camera()

    def _on_combo_changed(self, _index):
        if self._ready:
            self._disconnect_worker()
            cam_index = self.camera_combo.currentData()
            if cam_index is None:
                return
            self._set_loading("Opening camera, please wait…")
            QTimer.singleShot(60, lambda: self._switch_and_connect(cam_index))

    def _switch_and_connect(self, cam_index):
        worker = self._mgr.switch_camera(cam_index)
        self._connect_worker(worker, warm=False)

    def _start_camera(self):
        cam_index = self.camera_combo.currentData()
        if cam_index is None:
            return
        worker, warm = self._mgr.get_worker(cam_index)
        self._connect_worker(worker, warm)

    def _connect_worker(self, worker, warm):
        self._worker = worker
        worker.frame_ready.connect(self._on_frame, Qt.UniqueConnection)
        worker.qr_detected.connect(self._on_qr, Qt.UniqueConnection)
        worker.camera_opened.connect(self._on_opened, Qt.UniqueConnection)

        if warm or worker.isRunning():
            worker.activate(detect_qr=True)
            self._set_live()
        else:
            self._set_loading("Opening camera, please wait…")
            QTimer.singleShot(500, self._check_running)

    def _check_running(self):
        if self._worker and self._worker.isRunning() and self.preview.text():
            self._on_opened(True)

    def _on_opened(self, success):
        if success:
            self._worker.activate(detect_qr=True)
            self._set_live()
        else:
            self.status_label.setText("Could not open camera. Try a different one.")
            self.preview.setText("Camera unavailable.")

    def _set_live(self):
        # Keep the loading text until the first real frame arrives
        self.preview.setStyleSheet("color: #5a7aaa; font-size: 15px;")
        self.preview.setText("Loading camera preview…")
        self.status_label.setText("Point camera at a QR code…")

    def _set_loading(self, msg):
        self.preview.clear()
        self.preview.setText(msg)
        self.preview.setStyleSheet("color: #5a7aaa; font-size: 15px;")
        self.status_label.setText(msg)

    def _on_frame(self, frame):
        self.preview.setStyleSheet("")
        self.preview.setPixmap(_frame_to_pixmap(frame, self.preview.size()))

    def _on_qr(self, data):
        self.scanned_value = data
        self._disconnect_worker()
        self._mgr.release_dialog()
        self.accept()

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)

    def reject(self):
        self._cleanup()
        super().reject()

    def _cleanup(self):
        self._disconnect_worker()
        self._mgr.release_dialog()

    def _disconnect_worker(self):
        if self._worker:
            try: self._worker.frame_ready.disconnect(self._on_frame)
            except Exception: pass
            try: self._worker.qr_detected.disconnect(self._on_qr)
            except Exception: pass
            try: self._worker.camera_opened.disconnect(self._on_opened)
            except Exception: pass
            self._worker = None


class PhotoCaptureDialog(QDialog):
    """Live camera feed — captures a still photo on demand."""

    def __init__(self, parent=None, save_path=None):
        super().__init__(parent)
        self.setWindowTitle("Take Contract Photo")
        self.setMinimumSize(640, 560)
        self.resize(720, 580)

        self._mgr = CameraManager.instance()
        self._worker: CameraWorker | None = None
        self._last_frame = None
        self.captured_path = None
        self._save_path = save_path
        self._ready = False

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        cam_row = QHBoxLayout()
        cam_row.addWidget(QLabel("Camera:"))
        self.camera_combo = QComboBox()
        self.camera_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.camera_combo.currentIndexChanged.connect(self._on_combo_changed)
        cam_row.addWidget(self.camera_combo)
        layout.addLayout(cam_row)

        self.preview = QLabel("Initializing camera…")
        self.preview.setObjectName("camera_preview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview.setMinimumHeight(380)
        self.preview.setStyleSheet("color: #5a7aaa; font-size: 15px;")
        layout.addWidget(self.preview)

        self.status_label = QLabel("Starting up…")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.capture_btn = QPushButton("Capture Photo")
        self.capture_btn.setObjectName("primary")
        self.capture_btn.setEnabled(False)
        self.capture_btn.clicked.connect(self._capture)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.capture_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ready:
            self._ready = True
            QTimer.singleShot(60, self._init_cameras)

    def _init_cameras(self):
        cameras = self._mgr.get_camera_list()
        if not cameras:
            self.status_label.setText("No cameras found.")
            self.preview.setText("No cameras found.")
            return

        self.camera_combo.blockSignals(True)
        for idx, name in cameras:
            self.camera_combo.addItem(name, idx)

        if self._mgr.cam_index is not None:
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i) == self._mgr.cam_index:
                    self.camera_combo.setCurrentIndex(i)
                    break

        self.camera_combo.blockSignals(False)
        self._start_camera()

    def _on_combo_changed(self, _index):
        if self._ready:
            self._disconnect_worker()
            cam_index = self.camera_combo.currentData()
            if cam_index is None:
                return
            self.capture_btn.setEnabled(False)
            self._set_loading("Opening camera, please wait…")
            QTimer.singleShot(60, lambda: self._switch_and_connect(cam_index))

    def _switch_and_connect(self, cam_index):
        worker = self._mgr.switch_camera(cam_index)
        self._connect_worker(worker, warm=False)

    def _start_camera(self):
        cam_index = self.camera_combo.currentData()
        if cam_index is None:
            return
        worker, warm = self._mgr.get_worker(cam_index)
        self._connect_worker(worker, warm)

    def _connect_worker(self, worker, warm):
        self._worker = worker
        worker.frame_ready.connect(self._on_frame, Qt.UniqueConnection)
        worker.camera_opened.connect(self._on_opened, Qt.UniqueConnection)

        if warm or worker.isRunning():
            worker.activate(detect_qr=False)
            self._set_live()
        else:
            self._set_loading("Opening camera, please wait…")
            QTimer.singleShot(500, self._check_running)

    def _check_running(self):
        if self._worker and self._worker.isRunning() and self.preview.text():
            self._on_opened(True)

    def _on_opened(self, success):
        if success:
            self._worker.activate(detect_qr=False)
            self._set_live()
        else:
            self.status_label.setText("Could not open camera. Try a different one.")
            self.preview.setText("Camera unavailable.")

    def _set_live(self):
        self.preview.setStyleSheet("color: #5a7aaa; font-size: 15px;")
        self.preview.setText("Loading camera preview…")
        self.status_label.setText("Ready — click Capture Photo when set.")
        self.capture_btn.setEnabled(True)

    def _set_loading(self, msg):
        self.capture_btn.setEnabled(False)
        self.preview.clear()
        self.preview.setText(msg)
        self.preview.setStyleSheet("color: #5a7aaa; font-size: 15px;")
        self.status_label.setText(msg)

    def _on_frame(self, frame):
        self._last_frame = frame
        self.preview.setStyleSheet("")
        self.preview.setPixmap(_frame_to_pixmap(frame, self.preview.size()))

    def _capture(self):
        if self._last_frame is None:
            return
        import os, sys
        from datetime import datetime
        if self._save_path:
            path = self._save_path
        else:
            if getattr(sys, "frozen", False):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            photos_dir = os.path.join(base, "contract_photos")
            os.makedirs(photos_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(photos_dir, f"contract_{ts}.jpg")

        cv2.imwrite(path, self._last_frame)
        self.captured_path = path
        self._cleanup()
        self.accept()

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)

    def reject(self):
        self._cleanup()
        super().reject()

    def _cleanup(self):
        self._disconnect_worker()
        self._mgr.release_dialog()

    def _disconnect_worker(self):
        if self._worker:
            try: self._worker.frame_ready.disconnect(self._on_frame)
            except Exception: pass
            try: self._worker.camera_opened.disconnect(self._on_opened)
            except Exception: pass
            self._worker = None
