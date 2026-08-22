from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str = "admin"           # "admin" | "user"  — backward-compatible default


# ── Organization ──────────────────────────────────────────────────────────────

class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)

class OrgOut(BaseModel):
    id: int
    name: str
    slug: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ── User ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    org_id: int
    employee_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=200)
    email: str
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)

class UserOut(BaseModel):
    id: int
    org_id: int
    employee_id: Optional[int]
    name: str
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    model_config = {"from_attributes": True}

class UserProfileOut(BaseModel):
    id: int
    org_id: int
    name: str
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    # Employee info (if linked)
    employee_id: Optional[int]
    employee_code: Optional[str]
    department: Optional[str]
    position: Optional[str]
    face_registered: bool
    org_name: Optional[str]
    model_config = {"from_attributes": True}

class UpdateUsernameRequest(BaseModel):
    new_username: str = Field(..., min_length=3, max_length=100)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str


# ── Employee ──────────────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None

class EmployeeOut(BaseModel):
    id: int
    employee_code: str
    name: str
    email: Optional[str]
    department: Optional[str]
    position: Optional[str]
    is_active: bool
    face_registered: bool
    face_registered_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

class FaceRegisterRequest(BaseModel):
    employee_id: int
    image_base64: str = Field(..., description="Base64-encoded JPEG/PNG image")

class FaceRegisterResponse(BaseModel):
    success: bool
    message: str
    employee_id: Optional[int] = None


# ── Camera ────────────────────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = None
    stream_url: str = Field(..., description="RTSP URL, HTTP stream URL, or USB index (e.g. '0')")
    camera_type: str = Field("rtsp", pattern="^(rtsp|usb|http|webcam)$")

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    stream_url: Optional[str] = None
    is_enabled: Optional[bool] = None

class CameraOut(BaseModel):
    id: int
    name: str
    location: Optional[str]
    stream_url: str
    camera_type: str
    status: str
    is_enabled: bool
    last_heartbeat: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Attendance ─────────────────────────────────────────────────────────────────

class VerifyFaceRequest(BaseModel):
    image_base64: str
    camera_id: Optional[int] = None

class VerifyFaceResponse(BaseModel):
    matched: bool
    employee_id: Optional[int]
    employee_name: Optional[str]
    employee_code: Optional[str]
    confidence: float
    liveness_score: Optional[float]
    is_live: bool
    message: str

class AttendanceMarkRequest(BaseModel):
    image_base64: str
    camera_id: Optional[int] = None

class AttendanceMatchResult(BaseModel):
    success: bool
    event_type: Optional[str]           # CHECK_IN | CHECK_OUT
    employee_id: Optional[int]
    employee_name: Optional[str]
    employee_code: Optional[str]
    confidence: float
    is_live: bool
    box_2d: Optional[List[int]] = None   # [top, right, bottom, left]
    timestamp: Optional[datetime]
    message: str

class AttendanceMarkResponse(BaseModel):
    results: List[AttendanceMatchResult]

class AttendanceOut(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str]
    employee_code: Optional[str]
    camera_id: Optional[int]
    camera_name: Optional[str]
    event_type: str
    timestamp: datetime
    confidence: Optional[float]
    is_live: bool
    source: str

    model_config = {"from_attributes": True}


# ── Recognition Events ────────────────────────────────────────────────────────

class RecognitionEventOut(BaseModel):
    id: int
    employee_id: Optional[int]
    employee_name: Optional[str]
    user_id: Optional[int]
    timestamp: datetime
    confidence: Optional[float]
    camera_id: Optional[int]
    camera_name: Optional[str]
    image_path: Optional[str]
    is_live: bool
    event_type: Optional[str]

    model_config = {"from_attributes": True}


# ── Analytics ─────────────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_employees: int
    active_employees: int
    total_cameras: int
    active_cameras: int
    today_checkins: int
    today_checkouts: int
    avg_confidence: float

class DailyAttendance(BaseModel):
    date: str
    checkins: int
    checkouts: int
    unique_employees: int
    first_checkin: Optional[datetime] = None
    last_checkout: Optional[datetime] = None

class EmployeeAttendanceReport(BaseModel):
    employee: EmployeeOut
    total_checkins: int
    total_checkouts: int
    records: List[AttendanceOut]

class AccuracyReport(BaseModel):
    total_recognitions: int
    avg_confidence: float
    high_confidence_pct: float   # > 80%
    medium_confidence_pct: float # 50-80%
    low_confidence_pct: float    # < 50%


# ── User Analytics ────────────────────────────────────────────────────────────

class UserAttendanceSummary(BaseModel):
    today_checkin: Optional[datetime]
    today_checkout: Optional[datetime]
    today_status: str            # "present" | "absent" | "checked_out"
    streak_days: int
    total_days_this_month: int
    avg_confidence: float
    total_recognitions: int
