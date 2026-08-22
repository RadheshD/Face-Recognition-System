import os
from typing import Optional
from pydantic_settings import BaseSettings

_db_path = os.path.join(os.path.dirname(__file__), "..", "attendance.db")
_default_db = f"sqlite:///{os.path.abspath(_db_path)}"


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "FaceAttend AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database  (default = SQLite for zero-install local run)
    DATABASE_URL: str = _default_db

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "CHANGE-THIS-SECRET-KEY-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Default admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@company.com"

    # Face recognition
    FACE_RECOGNITION_THRESHOLD: float = 0.70
    FACE_RECOGNITION_MODEL: str = "hog"   # hog (CPU) or cnn (GPU)

    # Anti-spoofing
    ENABLE_ANTI_SPOOFING: bool = True
    LIVENESS_SCORE_THRESHOLD: float = 0.40

    # Face encoding encryption
    ENCRYPT_FACE_ENCODINGS: bool = False
    ENCRYPTION_KEY: Optional[str] = None

    # Camera processing
    FRAME_PROCESS_INTERVAL: float = 2.0
    CAMERA_RECONNECT_DELAY: float = 5.0
    MAX_SIMULTANEOUS_CAMERAS: int = 5

    # Attendance
    DUPLICATE_PREVENTION_MINUTES: int = 0

    # ── Geofencing ─────────────────────────────────────────────────────────────
    # Set these to your office / school GPS coordinates.
    # OFFICE_LAT / OFFICE_LON: centre of the allowed zone.
    # GEOFENCE_RADIUS_METERS: maximum allowed distance from centre (metres).
    OFFICE_LAT: float = 17.494177649703424   # Hyderabad office latitude
    OFFICE_LON: float = 78.35410917851893    # Hyderabad office longitude
    GEOFENCE_RADIUS_METERS: float = 250.0    # 250 m — covers indoor GPS drift

    model_config = {"env_file": ".env", "extra": "allow"}


settings = Settings()
