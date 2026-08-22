import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# ── Ensure backend dir is on path ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from config import settings  # type: ignore
from database import init_db, SessionLocal  # type: ignore
from security import ensure_default_admin  # type: ignore
from utils.embedding_cache import EmbeddingCache  # type: ignore
from services.face_service import FaceService  # type: ignore
from services.anti_spoof_service import AntiSpoofService  # type: ignore
from services.attendance_service import AttendanceService  # type: ignore
from services.camera_service import CameraManager  # type: ignore

import models  # type: ignore  # noqa — registers models with Base before init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────
    logger.info("🚀 Starting FaceAttend AI …")

    # Database
    init_db()

    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()

    # Services
    cache = EmbeddingCache(redis_url=settings.REDIS_URL)
    face_svc = FaceService(cache=cache)
    anti_spoof_svc = AntiSpoofService()
    attendance_svc = AttendanceService()
    camera_mgr = CameraManager()

    # Load face encodings into cache
    db = SessionLocal()
    try:
        count = face_svc.load_from_db(db)
        logger.info(f"✅ {count} face encodings loaded into cache.")
    finally:
        db.close()

    # Attach to app state
    app.state.face_svc = face_svc
    app.state.anti_spoof_svc = anti_spoof_svc
    app.state.attendance_svc = attendance_svc
    app.state.camera_mgr = camera_mgr

    # Auto-start enabled cameras logic disabled to avoid holding the webcam.
    # Users can use the attendance kiosk instead.
    # db = SessionLocal()
    # try:
    #     enabled_cameras = (
    #         db.query(models.Camera)
    #         .filter(models.Camera.is_enabled == True)  # noqa: E712
    #         .all()
    #     )
    #     for cam in enabled_cameras:
    #         try:
    #             camera_mgr.start_camera(
    #                 camera_id=cam.id,
    #                 stream_url=cam.stream_url,
    #                 face_svc=face_svc,
    #                 anti_spoof_svc=anti_spoof_svc,
    #                 attendance_svc=attendance_svc,
    #                 db_session_factory=SessionLocal,
    #             )
    #             logger.info(f"  📷 Auto-started camera: {cam.name}")
    #         except Exception as exc:
    #             logger.warning(f"  ⚠️  Could not start camera {cam.name}: {exc}")
    # finally:
    #     db.close()

    logger.info("✅ FaceAttend AI is ready.")
    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("🛑 Shutting down — stopping camera processors …")
    camera_mgr.stop_all()
    logger.info("👋 Goodbye.")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Face Recognition Attendance System",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Rate limiting removed for compatibility

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers (all prefixed with /api) ──────────────────────────────────
from routes.auth_routes import router as auth_router
from routes.employee_routes import router as employee_router
from routes.camera_routes import router as camera_router
from routes.attendance_routes import router as attendance_router
from routes.analytics_routes import router as analytics_router
from routes.geofence_routes import router as geofence_router
from routes.settings_routes import router as settings_router

app.include_router(auth_router, prefix="/api")
app.include_router(employee_router, prefix="/api")
app.include_router(camera_router, prefix="/api")
app.include_router(attendance_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(geofence_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# ── Serve frontend static files ───────────────────────────────────────────────
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return RedirectResponse("/api/docs")


# ── Run directly ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
