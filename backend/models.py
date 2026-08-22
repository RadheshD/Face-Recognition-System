import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float,
    DateTime, Boolean, Text, ForeignKey,
)
from sqlalchemy.orm import relationship
from database import Base



# ── Admin (unchanged) ─────────────────────────────────────────────────────────

class Admin(Base):
    __tablename__ = "admins"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(100), unique=True, nullable=False, index=True)
    email           = Column(String(200), unique=True)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow)
    last_login      = Column(DateTime, nullable=True)



# ── Employee (unchanged) ──────────────────────────────────────────────────────

class Employee(Base):
    __tablename__ = "employees"

    id              = Column(Integer, primary_key=True, index=True)
    employee_code   = Column(String(50), unique=True, nullable=False, index=True)
    name            = Column(String(200), nullable=False)
    email           = Column(String(200), unique=True, index=True)
    department      = Column(String(100))
    position        = Column(String(100))

    # Face data
    face_encoding      = Column(Text, nullable=True)        # JSON 128-d float array
    face_registered_at = Column(DateTime, nullable=True)

    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    attendances = relationship("Attendance", back_populates="employee",
                               lazy="dynamic", cascade="all, delete-orphan")


# ── Camera (unchanged) ────────────────────────────────────────────────────────

class Camera(Base):
    __tablename__ = "cameras"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    location    = Column(String(200))
    stream_url  = Column(String(500), nullable=False)
    camera_type = Column(String(50), default="rtsp")  # rtsp, usb, http, webcam

    status         = Column(String(20), default="inactive")   # active, inactive, error
    is_enabled     = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime, nullable=True)
    last_error     = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    attendances = relationship("Attendance", back_populates="camera",
                               lazy="dynamic")


# ── Attendance (unchanged) ────────────────────────────────────────────────────

class Attendance(Base):
    __tablename__ = "attendance"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    camera_id   = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"),
                         nullable=True, index=True)

    event_type    = Column(String(20), nullable=False)   # CHECK_IN | CHECK_OUT
    timestamp     = Column(DateTime, default=datetime.datetime.utcnow,
                           nullable=False, index=True)
    confidence    = Column(Float, nullable=True)          # 0-100

    is_live       = Column(Boolean, default=True)
    liveness_score = Column(Float, nullable=True)

    source     = Column(String(50), default="api")         # api | camera_processor
    note       = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    employee = relationship("Employee", back_populates="attendances")
    camera   = relationship("Camera", back_populates="attendances")


