import json
import logging
import os
import pickle
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

try:
    import face_recognition
    _fr_available = True
except ImportError:
    _fr_available = False
    logger.warning("face_recognition not installed. Using OpenCV Haar + pixel embedding fallback.")
import cv2

from config import settings
from utils.embedding_cache import EmbeddingCache
from utils.image_utils import normalize_lighting


class FaceService:
    """Core face detection and recognition service (CPU-optimised)."""

    def __init__(self, cache: EmbeddingCache):
        self.cache = cache
        self.threshold = settings.FACE_RECOGNITION_THRESHOLD
        self.model = settings.FACE_RECOGNITION_MODEL  # "hog" on CPU
        
        # Use an absolute path so the file is always found regardless of CWD
        _backend_dir = os.path.dirname(os.path.abspath(__file__))  # .../backend/services
        _backend_root = os.path.dirname(_backend_dir)               # .../backend
        self.encodings_file = os.path.join(_backend_root, "encodings.pkl")
        self.encodings_dict = {}
        self.known_encodings = []
        self.known_names = []
        self.known_employee_ids = []  # parallel list: employee_id for each encoding
        
        self.load_encodings()
        logger.info(f"FaceService initialised. face_recognition available: {_fr_available}. Model: {self.model}")

    @staticmethod
    def _to_dlib_compat(img_rgb: np.ndarray) -> np.ndarray:
        """
        Convert an RGB array to a dlib-compatible array via PIL round-trip.
        This is the only reliable way to satisfy dlib across all numpy versions:
        PIL's buffer always produces the exact memory layout dlib expects.
        """
        img_uint8 = np.clip(img_rgb, 0, 255).astype(np.uint8)
        pil_img = PILImage.fromarray(img_uint8)
        return np.array(pil_img)


    # ── Public API ────────────────────────────────────────────────────────────

    def load_from_db(self, db) -> int:
        """
        Loads user-specific metadata if needed. 
        Note: Facial vectors are primarily managed via encodings.pkl for speed.
        """
        return len(self.known_encodings)

    def detect_faces(self, image_rgb: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect face bounding boxes.
        Returns list of (top, right, bottom, left) tuples.
        """
        # ── Step 1: Lighting Normalisation ──
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        norm_bgr = normalize_lighting(image_bgr)  # always uint8
        # PIL round-trip guarantees dlib compatibility across ALL numpy versions
        norm_rgb = self._to_dlib_compat(cv2.cvtColor(norm_bgr, cv2.COLOR_BGR2RGB))

        if _fr_available:
            try:
                # First pass: fast (no upsample)
                locs = face_recognition.face_locations(norm_rgb, model=self.model, number_of_times_to_upsample=0)
                if not locs:
                    # Second pass: upsample once — catches smaller/farther faces
                    locs = face_recognition.face_locations(norm_rgb, model=self.model, number_of_times_to_upsample=1)
                
                if locs:
                    return locs
                
                logger.debug("face_recognition: no faces found, attempting Haar Cascade fallback...")
            except Exception as exc:
                logger.error(f"face_recognition detect_faces error: {exc}")
        
        # Fallback to OpenCV Haar Cascades
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(norm_rgb, cv2.COLOR_RGB2GRAY)
            gray = cv2.equalizeHist(gray)  # improve contrast for better detection
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4,
                minSize=(30, 30), flags=cv2.CASCADE_SCALE_IMAGE
            )
            locations = []
            for (x, y, w, h) in (faces if len(faces) else []):
                locations.append((y, x + w, y + h, x))
            return locations
        except Exception as exc:
            logger.error(f"cv2 detect_faces error: {exc}")
            return []

    def generate_embedding(
        self,
        image_rgb: np.ndarray,
        face_location: Optional[Tuple] = None,
    ) -> Optional[np.ndarray]:
        """Generate 128-dimensional face embedding (dlib via face_recognition)."""
        # ── Step 1: Lighting Normalisation ──
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        norm_bgr = normalize_lighting(image_bgr)  # always uint8
        # PIL round-trip guarantees dlib compatibility across ALL numpy versions
        norm_rgb = self._to_dlib_compat(cv2.cvtColor(norm_bgr, cv2.COLOR_BGR2RGB))

        if _fr_available:
            try:
                # Convert numpy scalar coords to plain Python ints — dlib rejects np.int32
                if face_location is not None:
                    loc = tuple(int(x) for x in face_location)
                    locations = [loc]
                else:
                    locations = None
                encs = face_recognition.face_encodings(
                    norm_rgb,
                    known_face_locations=locations,
                    num_jitters=1,
                    model="small",  # "small" is much faster; switch to "large" for better accuracy
                )
                if encs:
                    return encs[0]

                # face_recognition is available but returned no encoding for this frame.
                # Do NOT fall back to the pixel-based encoder — it produces incompatible
                # embeddings that break compare_faces(). Return None to signal failure.
                logger.debug(
                    "face_recognition: face_encodings() returned empty for this frame. "
                    "Try repositioning your face or improving lighting."
                )
                return None
            except Exception as exc:
                logger.error(f"face_recognition generate_embedding error: {exc}")
                return None

        # ── Pixel-fallback: only used when face_recognition is NOT installed ──
        # WARNING: these embeddings are NOT compatible with face_recognition.compare_faces().
        # They are only useful for the fallback matching path in find_best_match().
        try:
            if not face_location:
                faces = self.detect_faces(norm_rgb)
                if not faces:
                    return None
                face_location = faces[0]

            top, right, bottom, left = face_location
            # Ensure boundaries
            h, w = norm_rgb.shape[:2]
            top, bottom = max(0, top), min(h, bottom)
            left, right = max(0, left), min(w, right)

            face_img = norm_rgb[top:bottom, left:right]
            if face_img.size == 0:
                return None

            gray = cv2.cvtColor(face_img, cv2.COLOR_RGB2GRAY)
            # Resize to exactly 16x8 = 128 pixels total
            resized = cv2.resize(gray, (8, 16), interpolation=cv2.INTER_AREA)
            flattened = resized.flatten().astype(np.float64)
            # Normalize (Z-score) to make it robust to lighting
            mean = np.mean(flattened)
            std = np.std(flattened)
            if std > 0:
                normalized = (flattened - mean) / std
            else:
                normalized = flattened
            return normalized
        except Exception as exc:
            logger.error(f"cv2 generate_embedding error: {exc}")
            return None

    def load_encodings(self):
        """Encoding Loading on System Start."""
        if os.path.exists(self.encodings_file):
            try:
                with open(self.encodings_file, "rb") as f:
                    data = pickle.load(f)
                    
                if isinstance(data, dict) and "encodings" in data and "names" in data:
                    raw_encodings = data["encodings"]
                    raw_names = data["names"]
                    raw_ids = data.get("employee_ids", [None] * len(raw_names))
                    # Ensure all three lists are the same length
                    min_len = min(len(raw_encodings), len(raw_names), len(raw_ids))
                    raw_encodings = raw_encodings[:min_len]
                    raw_names = raw_names[:min_len]
                    raw_ids = raw_ids[:min_len]

                    # Purge any pixel-fallback (non-dlib) embeddings that may have
                    # been written by earlier buggy versions of the code.
                    clean_encodings, clean_names, clean_ids = [], [], []
                    purge_count = 0
                    for enc, nm, eid in zip(raw_encodings, raw_names, raw_ids):
                        if self._is_dlib_encoding(np.asarray(enc)):
                            clean_encodings.append(enc)
                            clean_names.append(nm)
                            clean_ids.append(eid)
                        else:
                            purge_count += 1
                            logger.warning(
                                f"load_encodings: purged corrupt (non-dlib) encoding for '{nm}' "
                                f"(L2 norm={np.linalg.norm(np.asarray(enc)):.3f})"
                            )

                    if purge_count:
                        # Persist the cleaned data back to disk
                        cleaned_data = {"encodings": clean_encodings, "names": clean_names, "employee_ids": clean_ids}
                        with open(self.encodings_file, "wb") as f:
                            pickle.dump(cleaned_data, f)
                        logger.info(f"Purged {purge_count} corrupt embeddings and saved cleaned {self.encodings_file}.")

                    self.known_encodings = clean_encodings
                    self.known_names = clean_names
                    self.known_employee_ids = clean_ids
                else:
                    self.known_encodings = []
                    self.known_names = []
                    self.known_employee_ids = []
                    
                print(f"Encodings loaded: {len(self.known_encodings)} | File: {self.encodings_file}")
                logger.info(f"✅ Loaded {len(self.known_encodings)} face encodings from {self.encodings_file}.")
            except Exception as e:
                logger.error(f"Error loading {self.encodings_file}: {e}")
                self.known_encodings = []
                self.known_names = []
                self.known_employee_ids = []
                # Recreate the pkl file if corrupted
                try:
                    data = {"encodings": [], "names": [], "employee_ids": []}
                    with open(self.encodings_file, "wb") as f:
                        pickle.dump(data, f)
                    logger.info(f"Recreated corrupted {self.encodings_file}.")
                except Exception as e2:
                    logger.error(f"Could not recreate {self.encodings_file}: {e2}")
        else:
            self.known_encodings = []
            self.known_names = []
            self.known_employee_ids = []
            
            data = {"encodings": [], "names": [], "employee_ids": []}
            with open(self.encodings_file, "wb") as f:
                pickle.dump(data, f)
                
            print(f"Encodings loaded: 0 | File: {self.encodings_file}")
            logger.info(f"Created new empty {self.encodings_file}.")

    @staticmethod
    def _is_dlib_encoding(encoding: np.ndarray) -> bool:
        """
        Validate that an encoding is a real 128-D dlib face_recognition vector.
        Real dlib encodings have L2 norm ≈ 1.0.
        Pixel-fallback z-score embeddings have L2 norm ≈ 11.3.
        """
        if encoding is None:
            return False
        arr = np.asarray(encoding)
        if arr.shape != (128,):
            return False
        norm = float(np.linalg.norm(arr))
        return 0.5 <= norm <= 3.0

    def save_encoding(self, encoding: np.ndarray, name: str, employee_id: int = None):
        """Encoding Saving Logic (Appending instead of overwriting)."""
        # Guard: reject pixel-fallback embeddings — only persist real dlib vectors
        if not self._is_dlib_encoding(encoding):
            logger.error(
                f"save_encoding: rejected non-dlib embedding for '{name}' "
                f"(L2 norm={np.linalg.norm(encoding):.3f}). "
                "Ensure face_recognition library is available and the image contains a clear face."
            )
            return

        data = {"encodings": [], "names": [], "employee_ids": []}
        if os.path.exists(self.encodings_file):
            try:
                with open(self.encodings_file, "rb") as f:
                    loaded_data = pickle.load(f)
                    if isinstance(loaded_data, dict) and "encodings" in loaded_data and "names" in loaded_data:
                        data = loaded_data
                        # Ensure employee_ids key exists for backward-compat
                        if "employee_ids" not in data:
                            data["employee_ids"] = [None] * len(data["names"])
            except Exception as e:
                logger.error(f"Error reading {self.encodings_file} for append: {e}")

        # Append new encoding, name and employee_id
        data["encodings"].append(encoding)
        data["names"].append(name)
        data["employee_ids"].append(employee_id)

        with open(self.encodings_file, "wb") as f:
            pickle.dump(data, f)
        
        # Update in-memory
        self.known_encodings = data["encodings"]
        self.known_names = data["names"]
        self.known_employee_ids = data["employee_ids"]
        logger.info(f"✅ Saved encoding for '{name}' (emp_id={employee_id}). Total records: {len(self.known_encodings)}")

    def reload_encodings(self):
        """Reload encodings from disk into memory (call after external changes to the pkl file)."""
        self.load_encodings()

    def remove_encodings_by_name(self, name: str):
        """Remove all encodings associated with a specific name."""
        if not os.path.exists(self.encodings_file):
            return
            
        try:
            with open(self.encodings_file, "rb") as f:
                data = pickle.load(f)
            
            if isinstance(data, dict) and "encodings" in data and "names" in data:
                emp_ids = data.get("employee_ids", [None] * len(data["names"]))
                new_encodings = []
                new_names = []
                new_emp_ids = []
                for enc, n, eid in zip(data["encodings"], data["names"], emp_ids):
                    if n != name:
                        new_encodings.append(enc)
                        new_names.append(n)
                        new_emp_ids.append(eid)
                
                data["encodings"] = new_encodings
                data["names"] = new_names
                data["employee_ids"] = new_emp_ids
                
                with open(self.encodings_file, "wb") as f:
                    pickle.dump(data, f)
                    
                self.known_encodings = data["encodings"]
                self.known_names = data["names"]
                self.known_employee_ids = data["employee_ids"]
                logger.info(f"Removed encodings for '{name}'. Remaining: {len(self.known_encodings)}")
        except Exception as e:
            logger.error(f"Error removing encodings for {name}: {e}")

    def find_best_match(
        self, query_encoding: np.ndarray
    ) -> Tuple[Optional[str], float, Optional[int]]:
        """
        Recognition Matching logic utilizing minimal distance index.
        Returns (name, confidence, employee_id).
        employee_id is retrieved directly from pickle to avoid DB name lookups.
        """
        if not self.known_encodings:
            return None, 0.0, None

        if not _fr_available:
            # Fallback for when face_recognition is missing
            diffs = np.array(self.known_encodings) - query_encoding
            distances = np.linalg.norm(diffs, axis=1)
            best_idx = int(np.argmin(distances))
            if distances[best_idx] <= self.threshold * 12.0:
                name = self.known_names[best_idx]
                emp_id = self.known_employee_ids[best_idx] if self.known_employee_ids else None
            else:
                name = "Unknown"
                emp_id = None
            print(f"Recognized (fallback): {name} | emp_id={emp_id}")
            return (name, 100.0, emp_id) if name != "Unknown" else (None, 0.0, None)

        # face_recognition comparison
        matches = face_recognition.compare_faces(
            self.known_encodings, query_encoding, tolerance=self.threshold
        )
        distances = face_recognition.face_distance(self.known_encodings, query_encoding)
        if len(distances) == 0:
            return None, 0.0, None

        best_match_index = int(np.argmin(distances))
        min_dist = distances[best_match_index]

        if matches[best_match_index]:
            name = self.known_names[best_match_index]
            emp_id = (
                self.known_employee_ids[best_match_index]
                if self.known_employee_ids and best_match_index < len(self.known_employee_ids)
                else None
            )
        else:
            name = "Unknown"
            emp_id = None

        # Confidence calculation
        confidence = max(0.0, min(100.0, round((1.0 - min_dist) * 100.0, 2)))

        print(f"Recognized: {name} | dist={min_dist:.3f} | conf={confidence:.1f}% | emp_id={emp_id}")

        if name != "Unknown":
            return name, confidence, emp_id
        return None, confidence, None

    def register_face(
        self, image_rgb: np.ndarray
    ) -> Tuple[Optional[np.ndarray], str]:
        """
        Full face registration pipeline:
        detect → validate → embed.
        Returns (encoding_array, message).
        Only returns a real 128-D dlib embedding; rejects pixel-fallback vectors.
        """
        if not _fr_available:
            return None, "face_recognition library not available. Cannot register face."

        locations = self.detect_faces(image_rgb)
        if not locations:
            return None, "No face detected in the image."
        if len(locations) > 1:
            return None, f"Multiple faces detected ({len(locations)}). Please provide an image with a single face."

        embedding = self.generate_embedding(image_rgb, locations[0])
        if embedding is None:
            return None, "Could not generate face embedding. Please try a clearer image."

        # Reject pixel-fallback embeddings — they are z-score normalised and have
        # L2 norm ≈ 11 which is incompatible with face_recognition.compare_faces().
        if not self._is_dlib_encoding(embedding):
            return None, (
                "Face detected but could not generate a valid recognition embedding. "
                "Please ensure your face is clearly visible and well-lit."
            )

        return embedding, "Face registered successfully."

    def update_cache_entry(self, employee_id: int, encoding: np.ndarray) -> None:
        self.cache.set(employee_id, encoding)

    def remove_cache_entry(self, employee_id: int) -> None:
        self.cache.delete(employee_id)
