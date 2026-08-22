import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from security import verify_password, create_access_token, hash_password, settings
from schemas import LoginRequest, TokenResponse
import models

router = APIRouter(tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Unified login for admins and users.
    - Checks admins table first (role=admin)
    - Falls back to users table (role=user)
    Response includes `role` so the frontend can redirect appropriately.
    """
    # ── Try Admin ─────────────────────────────────────────────────────────────
    admin = db.query(models.Admin).filter(
        models.Admin.username == payload.username
    ).first()

    if admin:
        if not verify_password(payload.password, admin.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if not admin.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")

        admin.last_login = datetime.datetime.utcnow()
        db.commit()

        token = create_access_token({
            "sub":  admin.username,
            "role": "admin",
        })
        return TokenResponse(
            access_token=token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            role="admin",
        )

    raise HTTPException(status_code=401, detail="Invalid username or password")


@router.post("/auth/logout")
def logout():
    """Client-side token deletion — server returns 200 OK."""
    return {"message": "Logged out successfully"}
