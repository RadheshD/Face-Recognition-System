import datetime
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import bcrypt
from sqlalchemy.orm import Session

from config import settings
from database import get_db
import models

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer()


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hasattr(hashed_password, "encode"):
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=expires_delta or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── FastAPI dependency — Admin (UNCHANGED) ────────────────────────────────────

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.Admin:
    payload = decode_token(credentials.credentials)
    username: Optional[str] = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Support legacy tokens (no role field) and explicit admin tokens
    role = payload.get("role", "admin")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    admin = db.query(models.Admin).filter(models.Admin.username == username).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin account not found or inactive")
    return admin



# ── Bootstrap default admin ───────────────────────────────────────────────────

def ensure_default_admin(db: Session) -> None:
    existing = db.query(models.Admin).filter(
        models.Admin.username == settings.ADMIN_USERNAME
    ).first()
    if not existing:
        admin = models.Admin(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
        )
        db.add(admin)
        db.commit()
        logger.info(f"✅ Default admin '{settings.ADMIN_USERNAME}' created.")
    else:
        logger.info(f"ℹ️  Admin '{settings.ADMIN_USERNAME}' already exists.")
