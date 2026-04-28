import cv2
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtMultimedia import QMediaDevices


def _to_bgr(frame):
    """Normalise any OpenCV frame to 3-channel BGR."""
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    if frame.shape[2] == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    return frame


class CameraWorker(QThread):
    frame_ready   = Signal(object)   # BGR numpy frame
    qr_detected   = Signal(str)
    camera_opened = Signal(bool)

    def __init__(self, cam_index):
        super().__init__()
        self.cam_index  = cam_index
        self._running   = True
        self._emit      = False
        self._detect_qr = False
        self._qr_tick   = 0

    def activate(self, detect_qr=False):
        self._detect_qr = detect_qr
        self._qr_tick   = 0
        self._emit      = True

    def deactivate(self):
        self._emit      = False
        self._detect_qr = False

    def stop(self):
        self._running = False

    def run(self):
        cap = self._open_camera()
        self.camera_opened.emit(cap is not None)
        if cap is None:
            return

        qr_det = cv2.QRCodeDetector()

        while self._running:
            ret, frame = cap.read()
            if not ret or frame is None:
                self.msleep(10)
                continue

            frame = _to_bgr(frame)

            if not self._emit:
                continue

            if self._detect_qr:
                self._qr_tick += 1
                if self._qr_tick >= 3:
                    self._qr_tick = 0
                    try:
                        data, bbox, _ = qr_det.detectAndDecode(frame)
                    except Exception:
                        data = ""
                    if data:
                        if bbox is not None:
                            pts = bbox[0].astype(int)
                            for j in range(len(pts)):
                                cv2.line(frame,
                                         tuple(pts[j]),
                                         tuple(pts[(j + 1) % len(pts)]),
                                         (45, 107, 196), 3)
                        self.frame_ready.emit(frame.copy())
                        self.qr_detected.emit(data)
                        self._detect_qr = False
                        continue
                    # No QR found — fall through and show the live frame

            self.frame_ready.emit(frame.copy())

        cap.release()

    def _open_camera(self):
        for backend in (cv2.CAP_MSMF, cv2.CAP_DSHOW, 0):
            cap = cv2.VideoCapture(self.cam_index, backend)
            if not cap.isOpened():
                cap.release()
                continue
            ret, frame = cap.read()
            if ret and frame is not None:
                return cap
            cap.release()
        return None


class CameraManager(QObject):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = CameraManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._worker: CameraWorker | None = None
        self._stopping: list[CameraWorker] = []
        self.cam_index = None

    def get_camera_list(self):
        cameras = []
        qt_devs = QMediaDevices.videoInputs()
        if qt_devs:
            for i, dev in enumerate(qt_devs):
                name = dev.description() or f"Camera {i}"
                up = name.upper()
                if any(kw in up for kw in ("IR", "INFRARED", "HELLO")):
                    continue
                cameras.append((i, name))
        else:
            for i in range(6):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    cameras.append((i, f"Camera {i}"))
                    cap.release()
        return cameras

    def get_worker(self, cam_index):
        if (self._worker and self.cam_index == cam_index
                and self._worker.isRunning()):
            return self._worker, True
        self._stop_worker()
        worker = CameraWorker(cam_index)
        self._worker = worker
        self.cam_index = cam_index
        worker.start()
        return worker, False

    def switch_camera(self, cam_index):
        self._stop_worker()
        worker = CameraWorker(cam_index)
        self._worker = worker
        self.cam_index = cam_index
        worker.start()
        return worker

    def release_dialog(self):
        if self._worker:
            self._worker.deactivate()

    def shutdown(self):
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)
            self._worker = None
        for w in list(self._stopping):
            w.wait(2000)
        self._stopping.clear()

    def _stop_worker(self):
        if self._worker:
            w = self._worker
            self._worker = None
            w.stop()
            self._stopping.append(w)
            w.finished.connect(lambda worker=w: self._reap(worker))

    def _reap(self, worker):
        try:
            self._stopping.remove(worker)
        except ValueError:
            pass
        worker.deleteLater()
