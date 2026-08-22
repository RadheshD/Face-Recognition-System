import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from security import get_current_admin
from schemas import (
    VerifyFaceRequest, VerifyFaceResponse,
    AttendanceMarkRequest, AttendanceMarkResponse, AttendanceMatchResult, AttendanceOut,
)
from config import settings
import models

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Attendance"])


def _att_out(a: models.Attendance) -> AttendanceOut:
    return AttendanceOut(
        id=a.id,
        employee_id=a.employee_id,
        employee_name=a.employee.name if a.employee else None,
        employee_code=a.employee.employee_code if a.employee else None,
        camera_id=a.camera_id,
        camera_name=a.camera.name if a.camera else None,
        event_type=a.event_type,
        timestamp=a.timestamp,
        confidence=a.confidence,
        is_live=a.is_live,
        source=a.source,
    )


@router.post("/verify-face", response_model=VerifyFaceResponse)
def verify_face(
    payload: VerifyFaceRequest,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Detect and identify a face without marking attendance."""
    from utils.image_utils import base64_to_numpy, bgr_to_rgb, validate_image, resize_for_recognition

    image_bgr = base64_to_numpy(payload.image_base64)
    ok, msg = validate_image(image_bgr)
    if not ok:
        raise HTTPException(400, msg)

    image_rgb = bgr_to_rgb(resize_for_recognition(image_bgr, 640))
    face_svc = request.app.state.face_svc
    anti_spoof_svc = request.app.state.anti_spoof_svc

    locations = face_svc.detect_faces(image_rgb)
    if not locations:
        return VerifyFaceResponse(
            matched=False, employee_id=None, employee_name=None,
            employee_code=None, confidence=0.0,
            liveness_score=None, is_live=True,
            message="No face detected in image",
        )

    embedding = face_svc.generate_embedding(image_rgb, locations[0])
    if embedding is None:
        return VerifyFaceResponse(
            matched=False, employee_id=None, employee_name=None,
            employee_code=None, confidence=0.0,
            liveness_score=None, is_live=True,
            message="Could not generate face embedding",
        )

    is_live, liveness_score, live_msg = anti_spoof_svc.check_liveness(image_bgr)
    res_name, confidence, emp_id_from_pkl = face_svc.find_best_match(embedding)

    if res_name is None:
        return VerifyFaceResponse(
            matched=False, employee_id=None, employee_name=None,
            employee_code=None, confidence=confidence,
            liveness_score=liveness_score, is_live=is_live,
            message="Face detected but not recognised",
        )

    # Use employee_id from pickle; fall back to DB name-lookup if not stored
    if emp_id_from_pkl:
        emp = db.query(models.Employee).filter(models.Employee.id == emp_id_from_pkl).first()
    else:
        emp = db.query(models.Employee).filter(models.Employee.name == res_name).first()

    return VerifyFaceResponse(
        matched=True,
        employee_id=emp.id if emp else None,
        employee_name=emp.name if emp else res_name,
        employee_code=emp.employee_code if emp else None,
        confidence=confidence,
        liveness_score=liveness_score,
        is_live=is_live,
        message=f"Recognised: {emp.name if emp else res_name} ({confidence:.1f}%)",
    )


@router.post("/attendance/mark", response_model=AttendanceMarkResponse)
def mark_attendance(
    payload: AttendanceMarkRequest,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Full pipeline: detect → anti-spoof → recognise → mark attendance."""
    from utils.image_utils import base64_to_numpy, bgr_to_rgb, validate_image, resize_for_recognition

    image_bgr = base64_to_numpy(payload.image_base64)
    ok, msg = validate_image(image_bgr)
    if not ok:
        logger.error(f"Image validation failed: {msg}")
        raise HTTPException(400, msg)

    h, w = image_bgr.shape[:2]
    logger.info(f"Received image for processing: {w}x{h}")

    resized = resize_for_recognition(image_bgr, 640)
    image_rgb = bgr_to_rgb(resized)
    
    # DEBUG: Save image to ROOT to see what we are receiving
    import cv2
    import os
    # Get the project root (one level up from /backend)
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    debug_path = os.path.join(root_dir, "debug_capture.jpg")
    cv2.imwrite(debug_path, resized)
    logger.info(f"💾 Saved debug capture to: {debug_path}")

    face_svc = request.app.state.face_svc
    anti_spoof_svc = request.app.state.anti_spoof_svc
    attendance_svc = request.app.state.attendance_svc

    # Detect face
    locations = face_svc.detect_faces(image_rgb)
    if not locations:
        return AttendanceMarkResponse(results=[])

    results = []
    for loc in locations:
        # Generate embedding
        embedding = face_svc.generate_embedding(image_rgb, loc)
        if embedding is None:
            results.append(AttendanceMatchResult(
                success=False, event_type=None, employee_id=None,
                employee_name=None, employee_code=None, confidence=0.0,
                timestamp=None, message="Embedding generation failed"
            ))
            continue

        # Liveness check with MiniFASNet (passes by default if model not loaded)
        is_live, liveness_score, live_msg = anti_spoof_svc.check_liveness(resized, face_location=loc)
        
        # Check settings or model status
        if settings.ENABLE_ANTI_SPOOFING and not is_live:
            results.append(AttendanceMatchResult(
                success=False, event_type=None, employee_id=None,
                employee_name=None, employee_code=None, confidence=0.0,
                is_live=is_live, box_2d=list(loc),
                timestamp=None, message=f"{live_msg}"
            ))
            continue

        # Match (RECOGNITION only continues if liveness is REAL)
        res_name, confidence, emp_id_from_pkl = face_svc.find_best_match(embedding)
        if res_name is None:
            results.append(AttendanceMatchResult(
                success=False, event_type=None, employee_id=None,
                employee_name=None, employee_code=None, confidence=confidence,
                is_live=is_live, box_2d=list(loc),
                timestamp=None, message="Face not recognised. Please register first."
            ))
            continue

        # Get employee record — prefer emp_id from pickle (fast), fall back to name lookup
        if emp_id_from_pkl:
            emp = db.query(models.Employee).filter(models.Employee.id == emp_id_from_pkl).first()
        else:
            emp = db.query(models.Employee).filter(models.Employee.name == res_name).first()
        if not emp:
            results.append(AttendanceMatchResult(
                success=False, event_type=None, employee_id=None,
                employee_name=res_name, employee_code=None, confidence=confidence,
                is_live=is_live, box_2d=list(loc),
                timestamp=None, message="Recognised name not found in database records."
            ))
            continue

        employee_id = emp.id

        # Mark attendance
        record, result_msg = attendance_svc.mark(
            db=db,
            employee_id=employee_id,
            camera_id=payload.camera_id,
            confidence=confidence,
            is_live=is_live,
            liveness_score=liveness_score,
        )

        if record is None:
            results.append(AttendanceMatchResult(
                success=False, event_type=None, employee_id=employee_id,
                employee_name=emp.name if emp else None,
                employee_code=emp.employee_code if emp else None,
                confidence=confidence, is_live=is_live, box_2d=list(loc),
                timestamp=None, message=result_msg
            ))
            continue

        # ── Write RecognitionEvent (SaaS extension — non-breaking) ────────────
        try:
            portal_user = (
                db.query(models.User)
                .filter(models.User.employee_id == employee_id)
                .first()
            )
            rec_event = models.RecognitionEvent(
                employee_id=employee_id,
                user_id=portal_user.id if portal_user else None,
                confidence=confidence,
                camera_id=payload.camera_id,
                is_live=is_live,
                event_type=record.event_type,
            )
            db.add(rec_event)
            db.commit()
        except Exception as _rec_exc:
            logger.warning(f"RecognitionEvent write failed (non-critical): {_rec_exc}")

        results.append(AttendanceMatchResult(
            success=True,
            event_type=record.event_type,
            employee_id=employee_id,
            employee_name=emp.name if emp else None,
            employee_code=emp.employee_code if emp else None,
            confidence=confidence,
            is_live=is_live,
            box_2d=list(loc),
            timestamp=record.timestamp,
            message=f"{record.event_type} marked for {emp.name if emp else employee_id}"
        ))

    return AttendanceMarkResponse(results=results)


@router.get("/attendance/today", response_model=List[AttendanceOut])
def today_attendance(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    from services.attendance_service import AttendanceService
    svc = AttendanceService()
    records = svc.get_today(db)
    return [_att_out(r) for r in records]


@router.get("/attendance/employee/{employee_id}", response_model=List[AttendanceOut])
def employee_attendance(
    employee_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    from services.attendance_service import AttendanceService
    svc = AttendanceService()
    records = svc.get_by_employee(db, employee_id, days)
    return [_att_out(r) for r in records]
