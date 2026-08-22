import datetime
import logging
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func
import io
import csv
from sqlalchemy.orm import Session

from database import get_db
from security import get_current_admin
from schemas import DashboardSummary, DailyAttendance, AccuracyReport
import models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


def count_working_days(start_date: datetime.date, end_date: datetime.date) -> int:
    """Count non-weekend days between start and end (inclusive)."""
    days = (end_date - start_date).days + 1
    count = 0
    for i in range(days):
        d = start_date + datetime.timedelta(days=i)
        if d.weekday() < 5:  # Monday=0 ... Friday=4
            count += 1
    return count


@router.get("/dashboard-summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    now = datetime.datetime.utcnow()
    today_start = datetime.datetime(now.year, now.month, now.day)

    total_employees = db.query(func.count(models.Employee.id)).scalar() or 0
    active_employees = db.query(func.count(models.Employee.id)).filter(
        models.Employee.is_active == True  # noqa: E712
    ).scalar() or 0
    total_cameras = db.query(func.count(models.Camera.id)).scalar() or 0
    active_cameras = db.query(func.count(models.Camera.id)).filter(
        models.Camera.status == "active"
    ).scalar() or 0

    today_checkins = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.event_type == "CHECK_IN",
        models.Attendance.timestamp >= today_start,
    ).scalar() or 0
    today_checkouts = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.event_type == "CHECK_OUT",
        models.Attendance.timestamp >= today_start,
    ).scalar() or 0

    avg_conf_result = db.query(func.avg(models.Attendance.confidence)).filter(
        models.Attendance.confidence.isnot(None)
    ).scalar()
    avg_confidence = round(float(avg_conf_result or 0), 2)

    return DashboardSummary(
        total_employees=total_employees,
        active_employees=active_employees,
        total_cameras=total_cameras,
        active_cameras=active_cameras,
        today_checkins=today_checkins,
        today_checkouts=today_checkouts,
        avg_confidence=avg_confidence,
    )


@router.get("/daily", response_model=List[DailyAttendance])
def daily_attendance(days: int = 14, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Return per-day attendance counts for the last N days."""
    results = []
    now = datetime.datetime.utcnow()
    for i in range(days - 1, -1, -1):
        day = now - datetime.timedelta(days=i)
        day_start = datetime.datetime(day.year, day.month, day.day)
        day_end = day_start + datetime.timedelta(days=1)

        checkins = db.query(func.count(models.Attendance.id)).filter(
            models.Attendance.event_type == "CHECK_IN",
            models.Attendance.timestamp >= day_start,
            models.Attendance.timestamp < day_end,
        ).scalar() or 0

        checkouts = db.query(func.count(models.Attendance.id)).filter(
            models.Attendance.event_type == "CHECK_OUT",
            models.Attendance.timestamp >= day_start,
            models.Attendance.timestamp < day_end,
        ).scalar() or 0

        first_checkin = db.query(func.min(models.Attendance.timestamp)).filter(
            models.Attendance.event_type == "CHECK_IN",
            models.Attendance.timestamp >= day_start,
            models.Attendance.timestamp < day_end,
        ).scalar()

        last_checkout = db.query(func.max(models.Attendance.timestamp)).filter(
            models.Attendance.event_type == "CHECK_OUT",
            models.Attendance.timestamp >= day_start,
            models.Attendance.timestamp < day_end,
        ).scalar()

        unique = db.query(func.count(func.distinct(models.Attendance.employee_id))).filter(
            models.Attendance.timestamp >= day_start,
            models.Attendance.timestamp < day_end,
        ).scalar() or 0

        results.append(DailyAttendance(
            date=day_start.strftime("%Y-%m-%d"),
            checkins=checkins,
            checkouts=checkouts,
            unique_employees=unique,
            first_checkin=first_checkin,
            last_checkout=last_checkout,
        ))
    return results


@router.get("/employee/{employee_id}")
def employee_report(
    employee_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        from fastapi import HTTPException
        raise HTTPException(404, "Employee not found")

    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    records = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.employee_id == employee_id,
            models.Attendance.timestamp >= since,
        )
        .order_by(models.Attendance.timestamp.desc())
        .all()
    )
    checkins = sum(1 for r in records if r.event_type == "CHECK_IN")
    checkouts = sum(1 for r in records if r.event_type == "CHECK_OUT")

    # Define scheduled working days (Mon-Fri)
    today = datetime.datetime.utcnow().date()
    start_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).date()
    scheduled_days = count_working_days(start_date, today)

    return {
        "employee_id": emp.id,
        "employee_code": emp.employee_code,
        "name": emp.name,
        "department": emp.department,
        "total_checkins": checkins,
        "total_checkouts": checkouts,
        "scheduled_working_days": scheduled_days,
        "records": [
            {
                "id": r.id,
                "event_type": r.event_type,
                "timestamp": r.timestamp.isoformat(),
                "confidence": r.confidence,
                "is_live": r.is_live,
                "camera_id": r.camera_id,
            }
            for r in records
        ],
    }


@router.get("/accuracy", response_model=AccuracyReport)
def accuracy_report(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    total = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.confidence.isnot(None)
    ).scalar() or 0

    if total == 0:
        return AccuracyReport(
            total_recognitions=0,
            avg_confidence=0.0,
            high_confidence_pct=0.0,
            medium_confidence_pct=0.0,
            low_confidence_pct=0.0,
        )

    avg = db.query(func.avg(models.Attendance.confidence)).scalar() or 0
    high = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.confidence >= 80
    ).scalar() or 0
    medium = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.confidence >= 50,
        models.Attendance.confidence < 80,
    ).scalar() or 0
    low = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.confidence < 50
    ).scalar() or 0

    return AccuracyReport(
        total_recognitions=total,
        avg_confidence=round(float(avg), 2),
        high_confidence_pct=round(high / total * 100, 2),
        medium_confidence_pct=round(medium / total * 100, 2),
        low_confidence_pct=round(low / total * 100, 2),
    )


@router.get("/export/attendance")
def export_attendance_csv(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    records = db.query(models.Attendance).order_by(models.Attendance.timestamp.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Time", "Employee ID", "Employee Code", "Employee Name", 
        "Event Type", "Confidence (%)", "Source", "Liveness Score", "Is Live"
    ])
    
    for r in records:
        date_str = r.timestamp.strftime("%Y-%m-%d")
        time_str = r.timestamp.strftime("%H:%M:%S")
        emp_name = r.employee.name if r.employee else "Unknown"
        emp_code = r.employee.employee_code if r.employee else ""
        conf = f"{r.confidence:.2f}" if r.confidence is not None else ""
        liveness = f"{r.liveness_score:.2f}" if r.liveness_score is not None else ""
        
        writer.writerow([
            date_str, time_str, r.employee_id, emp_code, emp_name,
            r.event_type, conf, r.source, liveness, r.is_live
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_export.csv"}
    )
