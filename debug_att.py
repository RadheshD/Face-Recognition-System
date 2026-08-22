import sys
sys.path.insert(0, './backend')
from database import SessionLocal
from services.attendance_service import AttendanceService
import models

db = SessionLocal()
emp = db.query(models.Employee).first()

svc = AttendanceService()
try:
    record, result_msg = svc.mark(
        db=db,
        employee_id=emp.id,
        camera_id=None,
        confidence=95.0,
        is_live=True,
        liveness_score=1.0,
    )
    if record:
        print(f"SUCCESS: {record.event_type} - {result_msg}")
    else:
        print(f"SKIPPED: {result_msg}")
except Exception as e:
    print(f"ERROR: {e}")

