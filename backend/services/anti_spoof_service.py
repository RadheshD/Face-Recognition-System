import logging
import os
from typing import Tuple, Optional

import cv2
import numpy as np

from config import settings

logger = logging.getLogger(__name__)

class AntiSpoofService:
    """
    OpenCV Heuristic Anti-Spoofing Service.
    
    This replaces the problematic PyTorch neural network with a stable, deterministic 
    fallback algorithm that checks for common spoofing artifacts:
    1. Lack of 3D Texture / Focus Loss (Detects printed photos & screen gloss blur directly using Laplacian Variance).
    2. Screen Glare / Specularity (Detects LED screen light emission masking using brightness ratio).
    """

    def __init__(self):
        logger.info("✅ Using OpenCV Heuristic Liveness Detection (Fallback Alternative)")

    def check_liveness(self, image_bgr: np.ndarray, face_location: Optional[Tuple[int,int,int,int]] = None) -> Tuple[bool, float, str]:
        if not face_location:
            return False, 0.0, "No face location provided"

        try:
            top, right, bottom, left = face_location
            
            # Ensure boundaries are valid
            h, w = image_bgr.shape[:2]
            top, bottom = max(0, top), min(h, bottom)
            left, right = max(0, left), min(w, right)
            
            face_crop = image_bgr[top:bottom, left:right]
            if face_crop.size == 0 or face_crop.shape[0] < 30 or face_crop.shape[1] < 30:
                return False, 0.0, "Face crop too small"

            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            
            # 1. Blur and Depth Texture Detection
            # Printed photos lack micro-textures. Phone screens held to webcams often break lens focus.
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 2. Specular Glare Detection
            # LCD/OLED phone screens emit light and reflect room lighting fiercely, 
            # causing bright glare clipping which humans rarely have naturally on standard webcams.
            _, bright_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
            bright_ratio = cv2.countNonZero(bright_mask) / (gray.shape[0] * gray.shape[1])
            
            is_live = True
            score = 1.0
            msg = "Liveness confirmed"
            
            if laplacian_var < 20.0:
                is_live = False
                score = 0.2
                msg = f"Spoof Attack: Blurry / Flat texture (var={laplacian_var:.1f})"
            elif bright_ratio > 0.20:
                is_live = False
                score = 0.1
                msg = f"Spoof Attack: Screen glare detected"
            else:
                # Construct passing score
                score = min(1.0, 0.5 + (laplacian_var / 1000.0))
                
            return is_live, score, msg

        except Exception as exc:
            logger.error(f"Heuristic liveness check error: {exc}")
            return False, 0.0, "Processing error - strict fail"
