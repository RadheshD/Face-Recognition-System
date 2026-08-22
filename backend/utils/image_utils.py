import base64
import io
import logging
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def base64_to_numpy(b64_string: str) -> Optional[np.ndarray]:
    """Decode a base64 image string to a BGR numpy array."""
    try:
        # Strip data URI prefix if present
        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]

        img_bytes = base64.b64decode(b64_string)
        pil_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        return bgr
    except Exception as exc:
        logger.error(f"base64_to_numpy failed: {exc}")
        return None


def numpy_to_base64(image: np.ndarray, fmt: str = ".jpg") -> str:
    """Encode a BGR numpy array to base64 string."""
    success, buffer = cv2.imencode(fmt, image)
    if not success:
        raise ValueError("Could not encode image")
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


def resize_for_recognition(image: np.ndarray, max_width: int = 640) -> np.ndarray:
    """Downscale large images for faster face detection."""
    h, w = image.shape[:2]
    if w > max_width:
        scale = max_width / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image


def bgr_to_rgb(image: np.ndarray) -> np.ndarray:
    """Convert BGR (OpenCV) to RGB (face_recognition)."""
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def normalize_lighting(image_bgr: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    to balance lighting in over-exposed or dark environments.
    Always returns a valid uint8 BGR image.
    """
    # Guard: ensure input is uint8 (face_recognition and OpenCV require this)
    if image_bgr.dtype != np.uint8:
        image_bgr = np.clip(image_bgr, 0, 255).astype(np.uint8)

    try:
        lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L-channel only
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)

        limg = cv2.merge((cl, a, b))
        result = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # Explicit uint8 cast to satisfy face_recognition / dlib
        return np.clip(result, 0, 255).astype(np.uint8)
    except Exception as exc:
        logger.error(f"normalize_lighting failed: {exc}. Returning original.")
        return image_bgr


def validate_image(image: Optional[np.ndarray]) -> Tuple[bool, str]:
    """Basic image quality checks."""
    if image is None:
        return False, "Could not decode image"
    if image.size == 0:
        return False, "Empty image"
    h, w = image.shape[:2]
    if h < 60 or w < 60:
        return False, f"Image too small ({w}x{h}). Minimum 60x60."
    # Focus primarily on face detection — disable strict Laplacian blur check for webcams
    # (since webcam streams naturally have JPEG artifacts/noise that lower the laplacian score)
    return True, "ok"


def draw_face_boxes(
    image: np.ndarray,
    locations: list,
    labels: Optional[list] = None,
) -> np.ndarray:
    """Draw bounding boxes around detected faces."""
    out = image.copy()
    for i, (top, right, bottom, left) in enumerate(locations):
        cv2.rectangle(out, (left, top), (right, bottom), (0, 255, 0), 2)
        if labels and i < len(labels):
            cv2.putText(
                out, labels[i], (left, top - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
            )
    return out
