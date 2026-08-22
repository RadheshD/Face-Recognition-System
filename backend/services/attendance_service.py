import datetime
import logging
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from config import settings
import models

logger = logging.getLogger(__name__)


class AttendanceService:
    """
    Handles check-in / check-out logic with duplicate prevention.
    """

    def mark(
        self,
        db: Session,
        employee_id: int,
        camera_id: Optional[int],
        confidence: float,
        is_live: bool = True,
        liveness_score: Optional[float] = None,
        source: str = "api",
    ) -> Tuple[Optional[models.Attendance], str]:
        """
        Mark attendance for an employee.

        Logic:
          - Reject if a record exists within DUPLICATE_PREVENTION_MINUTES
          - If no CHECK_IN today → CHECK_IN
          - If CHECK_IN exists but no CHECK_OUT → CHECK_OUT
          - If both exist → new CHECK_IN (next session)

        Returns (attendance_record, status_message).
        """
        now = datetime.datetime.utcnow()

        # ── Duplicate guard ────────────────────────────────────────────────
        window = now - datetime.timedelta(minutes=settings.DUPLICATE_PREVENTION_MINUTES)
        recent = (
            db.query(models.Attendance)
            .filter(
                models.Attendance.employee_id == employee_id,
                models.Attendance.timestamp >= window,
            )
            .order_by(models.Attendance.timestamp.desc())
            .first()
        )
        if recent:
            elapsed = int((now - recent.timestamp).total_seconds() // 60)
            return recent, f"Active {recent.event_type} valid."

        # ── Determine event type ───────────────────────────────────────────
        today_start = datetime.datetime(now.year, now.month, now.day)
        today_records = (
            db.query(models.Attendance)
            .filter(
                models.Attendance.employee_id == employee_id,
                models.Attendance.timestamp >= today_start,
            )
            .order_by(models.Attendance.timestamp.asc())
            .all()
        )

        checkins  = [r for r in today_records if r.event_type == "CHECK_IN"]
        checkouts = [r for r in today_records if r.event_type == "CHECK_OUT"]

        if len(checkins) > len(checkouts):
            event_type = "CHECK_OUT"
        else:
            event_type = "CHECK_IN"

        # ── Persist ────────────────────────────────────────────────────────
        record = models.Attendance(
            employee_id=employee_id,
            camera_id=camera_id,
            event_type=event_type,
            timestamp=now,
            confidence=confidence,
            is_live=is_live,
            liveness_score=liveness_score,
            source=source,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(
            f"Attendance: {event_type} emp={employee_id} "
            f"conf={confidence:.1f}% cam={camera_id}"
        )
        return record, event_type

    def get_today(self, db: Session, limit: int = 200):
        now = datetime.datetime.utcnow()
        today_start = datetime.datetime(now.year, now.month, now.day)
        return (
            db.query(models.Attendance)
            .filter(models.Attendance.timestamp >= today_start)
            .order_by(models.Attendance.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_by_employee(self, db: Session, employee_id: int, days: int = 30):
        since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        return (
            db.query(models.Attendance)
            .filter(
                models.Attendance.employee_id == employee_id,
                models.Attendance.timestamp >= since,
            )
            .order_by(models.Attendance.timestamp.desc())
            .all()
        )
