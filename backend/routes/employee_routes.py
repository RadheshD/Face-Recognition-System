import datetime
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from security import get_current_admin
from schemas import (
    EmployeeCreate, EmployeeUpdate, EmployeeOut,
    FaceRegisterRequest, FaceRegisterResponse,
)
import models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/employees", tags=["Employees"])


def _employee_out(emp: models.Employee) -> EmployeeOut:
    return EmployeeOut(
        id=emp.id,
        employee_code=emp.employee_code,
        name=emp.name,
        email=emp.email,
        department=emp.department,
        position=emp.position,
        is_active=emp.is_active,
        face_registered=emp.face_encoding is not None,
        face_registered_at=emp.face_registered_at,
        created_at=emp.created_at,
    )


@router.post("/", response_model=EmployeeOut)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    if db.query(models.Employee).filter(
        models.Employee.employee_code == payload.employee_code
    ).first():
        raise HTTPException(400, "Employee code already exists")

    emp = models.Employee(**payload.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return _employee_out(emp)


@router.get("/", response_model=List[EmployeeOut])
def list_employees(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    employees = (
        db.query(models.Employee)
        .order_by(models.Employee.name)
        .offset(skip).limit(limit).all()
    )
    return [_employee_out(e) for e in employees]


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    return _employee_out(emp)


@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(emp, field, val)
    emp.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(emp)
    return _employee_out(emp)


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    # Remove from face cache and persistent storage
    request.app.state.face_svc.remove_encodings_by_name(emp.name)
    db.delete(emp)
    db.commit()
    return {"message": f"Employee {employee_id} deleted and face data removed"}


@router.post("/register-face", response_model=FaceRegisterResponse)
def register_face(
    payload: FaceRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Detect face in image, generate embedding, store in database."""
    emp = db.query(models.Employee).filter(
        models.Employee.id == payload.employee_id
    ).first()
    if not emp:
        raise HTTPException(404, "Employee not found")

    # Decode image
    from utils.image_utils import base64_to_numpy, bgr_to_rgb, validate_image, resize_for_recognition
    image_bgr = base64_to_numpy(payload.image_base64)
    ok, msg = validate_image(image_bgr)
    if not ok:
        raise HTTPException(400, msg)

    image_rgb = bgr_to_rgb(resize_for_recognition(image_bgr, 640))

    # Face service from app state
    face_svc = request.app.state.face_svc
    embedding, message = face_svc.register_face(image_rgb)

    if embedding is None:
        return FaceRegisterResponse(success=False, message=message)

    # Only use Pickle for encoding storage (frontend uses column as boolean)
    emp.face_encoding = "PICKLE"
    emp.face_registered_at = datetime.datetime.utcnow()
    db.commit()

    # Update persistent pickle storage (name + employee_id for direct lookup)
    face_svc.save_encoding(embedding, emp.name, employee_id=emp.id)

    return FaceRegisterResponse(
        success=True,
        message=f"Face registered for {emp.name}",
        employee_id=emp.id,
    )
