import datetime
import logging
import threading
import time
from typing import Dict, Optional

import cv2
import numpy as np

from config import settings

logger = logging.getLogger(__name__)


class CameraProcessor:
    """
    Background thread that continuously reads frames from a camera stream,
    detects faces, and marks attendance automatically.
    """

    def __init__(
        self,
        camera_id: int,
        stream_url: str,
        face_svc,
        anti_spoof_svc,
        attendance_svc,
        db_session_factory,
    ):
        self.camera_id = camera_id
        self.stream_url = stream_url
        self.face_svc = face_svc
        self.anti_spoof_svc = anti_spoof_svc
        self.attendance_svc = attendance_svc
        self.db_session_factory = db_session_factory

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.is_running = False
        self.frames_processed = 0
        self.last_error: Optional[str] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"cam-{self.camera_id}"
        )
        self._thread.start()
        self.is_running = True
        logger.info(f"Camera processor started: cam_id={self.camera_id}")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self.is_running = False
        logger.info(f"Camera processor stopped: cam_id={self.camera_id}")

    # ── Main thread loop ──────────────────────────────────────────────────────

    def _run(self) -> None:
        self.is_running = True
        while not self._stop_event.is_set():
            cap = None
            try:
                # Resolve stream URL (integer index for USB cameras)
                source = int(self.stream_url) if self.stream_url.isdigit() else self.stream_url
                cap = cv2.VideoCapture(source)

                if not cap.isOpened():
                    raise ConnectionError(f"Cannot open stream: {self.stream_url}")

                self._update_status("active")
                logger.info(f"Cam {self.camera_id}: stream opened.")

                while not self._stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning(f"Cam {self.camera_id}: frame read failed — reconnecting.")
                        break

                    try:
                        self._process_frame(frame)
                    except Exception as exc:
                        logger.error(f"Cam {self.camera_id} frame error: {exc}")

                    self.frames_processed += 1
                    # Sleep between frames
                    if self._stop_event.wait(timeout=settings.FRAME_PROCESS_INTERVAL):
                        break

            except Exception as exc:
                self.last_error = str(exc)
                logger.error(f"Cam {self.camera_id} connection error: {exc}")
                self._update_status("error")
            finally:
                if cap:
                    cap.release()

            if not self._stop_event.is_set():
                logger.info(f"Cam {self.camera_id}: reconnecting in {settings.CAMERA_RECONNECT_DELAY}s …")
                self._stop_event.wait(timeout=settings.CAMERA_RECONNECT_DELAY)

        self._update_status("inactive")

    def _process_frame(self, frame_bgr: np.ndarray) -> None:
        from utils.image_utils import bgr_to_rgb, resize_for_recognition

        resized = resize_for_recognition(frame_bgr, max_width=640)
        image_rgb = bgr_to_rgb(resized)

        locations = self.face_svc.detect_faces(image_rgb)
        if not locations:
            return

        for loc in locations:
            embedding = self.face_svc.generate_embedding(image_rgb, loc)
            if embedding is None:
                continue

            recognized_name, confidence, emp_id_from_pkl = self.face_svc.find_best_match(embedding)
            if not recognized_name:
                continue  # Unknown face

            # Resolve to employee_id — prefer pickle, fall back to DB name-lookup
            db = self.db_session_factory()
            try:
                from models import Employee
                if emp_id_from_pkl:
                    emp = db.query(Employee).filter(Employee.id == emp_id_from_pkl).first()
                else:
                    emp = db.query(Employee).filter(Employee.name == recognized_name).first()
                    
                if not emp:
                    logger.warning(f"Recognized name '{recognized_name}' not found in DB.")
                    continue
                
                employee_id = emp.id

                # Anti-spoofing
                is_live, liveness_score, _ = self.anti_spoof_svc.check_liveness(resized, loc)
                if settings.ENABLE_ANTI_SPOOFING and not is_live:
                    logger.info(f"Cam {self.camera_id}: spoof rejected emp={employee_id}")
                    continue

                self.attendance_svc.mark(
                    db=db,
                    employee_id=employee_id,
                    camera_id=self.camera_id,
                    confidence=confidence,
                    is_live=is_live,
                    liveness_score=liveness_score,
                    source="camera_processor",
                )
                logger.info(f"Cam {self.camera_id}: attendance marked for '{recognized_name}' (emp_id={employee_id})")
            finally:
                db.close()

    def _update_status(self, status: str) -> None:
        db = self.db_session_factory()
        try:
            from models import Camera
            cam = db.query(Camera).filter(Camera.id == self.camera_id).first()
            if cam:
                cam.status = status
                cam.last_heartbeat = datetime.datetime.utcnow()
                if status == "error":
                    cam.last_error = self.last_error
                db.commit()
        except Exception as exc:
            logger.debug(f"Status update error: {exc}")
        finally:
            db.close()


class CameraManager:
    """Manages a pool of CameraProcessor instances."""

    def __init__(self):
        self._processors: Dict[int, CameraProcessor] = {}
        self._lock = threading.Lock()

    def start_camera(
        self, camera_id: int, stream_url: str,
        face_svc, anti_spoof_svc, attendance_svc, db_session_factory,
    ) -> None:
        if self.is_running(camera_id):
            return  # already running
        with self._lock:
            if len(self._processors) >= settings.MAX_SIMULTANEOUS_CAMERAS:
                raise RuntimeError(
                    f"Max cameras ({settings.MAX_SIMULTANEOUS_CAMERAS}) reached."
                )
            proc = CameraProcessor(
                camera_id, stream_url,
                face_svc, anti_spoof_svc, attendance_svc, db_session_factory,
            )
            proc.start()
            self._processors[camera_id] = proc

    def stop_camera(self, camera_id: int) -> None:
        with self._lock:
            proc = self._processors.pop(camera_id, None)
            if proc:
                proc.stop()

    def stop_all(self) -> None:
        with self._lock:
            for proc in self._processors.values():
                proc.stop()
            self._processors.clear()

    def status(self) -> Dict[int, dict]:
        return {
            cid: {
                "running": p.is_running,
                "frames": p.frames_processed,
                "error": p.last_error,
            }
            for cid, p in self._processors.items()
        }

    def is_running(self, camera_id: int) -> bool:
        with self._lock:
            if camera_id in self._processors:
                proc = self._processors[camera_id]
                if proc._thread and proc._thread.is_alive():
                    return True
                else:
                    proc.is_running = False
                    self._processors.pop(camera_id, None)
            return False
