import datetime
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from security import get_current_admin
from schemas import CameraCreate, CameraUpdate, CameraOut
import models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cameras", tags=["Cameras"])


def _cam_out(c: models.Camera) -> CameraOut:
    return CameraOut(
        id=c.id, name=c.name, location=c.location,
        stream_url=c.stream_url, camera_type=c.camera_type,
        status=c.status, is_enabled=c.is_enabled,
        last_heartbeat=c.last_heartbeat, last_error=c.last_error,
        created_at=c.created_at,
    )


@router.post("/", response_model=CameraOut)
def add_camera(
    payload: CameraCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cam = models.Camera(**payload.model_dump())
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return _cam_out(cam)


@router.get("/", response_model=List[CameraOut])
def list_cameras(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return [_cam_out(c) for c in db.query(models.Camera).order_by(models.Camera.name).all()]


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")
    return _cam_out(cam)


@router.put("/{camera_id}", response_model=CameraOut)
def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(cam, field, val)
    cam.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(cam)
    return _cam_out(cam)


@router.delete("/{camera_id}")
def delete_camera(
    camera_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")
    # Stop processor if running
    request.app.state.camera_mgr.stop_camera(camera_id)
    db.delete(cam)
    db.commit()
    return {"message": f"Camera {camera_id} deleted"}


@router.post("/{camera_id}/start")
def start_camera(
    camera_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")
    if not cam.is_enabled:
        raise HTTPException(400, "Camera is disabled")

    mgr = request.app.state.camera_mgr
    if mgr.is_running(camera_id):
        return {"message": "Camera already running"}

    from database import SessionLocal
    mgr.start_camera(
        camera_id=camera_id,
        stream_url=cam.stream_url,
        face_svc=request.app.state.face_svc,
        anti_spoof_svc=request.app.state.anti_spoof_svc,
        attendance_svc=request.app.state.attendance_svc,
        db_session_factory=SessionLocal,
    )
    return {"message": f"Camera {cam.name} started"}


@router.post("/{camera_id}/stop")
def stop_camera(
    camera_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    request.app.state.camera_mgr.stop_camera(camera_id)
    return {"message": f"Camera {camera_id} stopped"}


@router.get("/{camera_id}/status")
def camera_status(camera_id: int, request: Request, _=Depends(get_current_admin)):
    statuses = request.app.state.camera_mgr.status()
    return statuses.get(camera_id, {"running": False, "frames": 0, "error": None})
