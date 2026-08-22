"""
settings_routes.py — GET / POST /api/settings
Persists settings to a JSON file (backend/settings.json).
Does NOT modify any existing attendance, recognition, or analytics logic.
"""

import json
import os
import logging
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Settings"])
logger = logging.getLogger("settings")

_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "settings.json")

# ── Default settings ──────────────────────────────────────────────────────────

DEFAULTS = {
    "ai": {
        "sensitivity": 1,        # 0=Strict, 1=Balanced, 2=Relaxed
        "confidence": 85,        # percentage (40–99)
        "cooldown": 30,          # seconds before same face re-triggers
        "camera": "built-in",    # built-in | usb | ip-rtsp
    },
    "attendance": {
        "checkin": "09:00",
        "late": "09:15",
        "checkout": "18:00",
        "grace": 15,             # minutes
    },
    "alerts": {
        "unknown_face": True,
        "missed_checkout": True,
        "daily_summary": False,
    },
}


def _read_settings() -> dict:
    """Read settings from disk, falling back to defaults."""
    if os.path.isfile(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults so new keys are always present
            merged = json.loads(json.dumps(DEFAULTS))
            for section, values in data.items():
                if section in merged and isinstance(values, dict):
                    merged[section].update(values)
                else:
                    merged[section] = values
            return merged
        except Exception as exc:
            logger.warning(f"Failed to read settings file: {exc}")
    return json.loads(json.dumps(DEFAULTS))


def _write_settings(data: dict) -> None:
    """Write settings dict to disk as pretty JSON."""
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Settings saved to %s", _SETTINGS_FILE)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/settings")
def get_settings():
    """Return current settings (merged with defaults)."""
    return _read_settings()


@router.post("/settings")
def save_settings(payload: dict):
    """
    Save settings payload to JSON config file.
    Accepts a free-form dict so the frontend can evolve independently.
    """
    try:
        _write_settings(payload)
        return {"status": "ok", "message": "Settings saved successfully"}
    except Exception as exc:
        logger.error("Failed to save settings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
