import json
import logging
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import redis as redis_lib
    _redis_available = True
except ImportError:
    _redis_available = False


class EmbeddingCache:
    """
    In-memory + Redis cache for face embeddings.
    Falls back gracefully to memory-only if Redis is unavailable.
    """

    REDIS_KEY_PREFIX = "face_emb:"
    REDIS_INDEX_KEY = "face_emb_index"
    TTL = 3600 * 24  # 24 hours

    def __init__(self, redis_url: Optional[str] = None):
        self._memory: Dict[int, np.ndarray] = {}  # employee_id -> 128-d vector
        self._redis: Optional[object] = None

        if _redis_available and redis_url:
            try:
                self._redis = redis_lib.from_url(redis_url, decode_responses=False)
                self._redis.ping()
                logger.info("✅ Redis connected — embedding cache active.")
            except Exception as exc:
                logger.warning(f"⚠️  Redis unavailable ({exc}). Using in-memory only.")
                self._redis = None

    # ── Write ─────────────────────────────────────────────────────────────────

    def set(self, employee_id: int, encoding: np.ndarray) -> None:
        self._memory[employee_id] = encoding
        if self._redis:
            try:
                key = f"{self.REDIS_KEY_PREFIX}{employee_id}"
                self._redis.set(key, json.dumps(encoding.tolist()), ex=self.TTL)
            except Exception as exc:
                logger.debug(f"Redis write error: {exc}")

    def bulk_set(self, encodings: Dict[int, np.ndarray]) -> None:
        self._memory = dict(encodings)
        if self._redis:
            try:
                pipe = self._redis.pipeline()
                for eid, enc in encodings.items():
                    key = f"{self.REDIS_KEY_PREFIX}{eid}"
                    pipe.set(key, json.dumps(enc.tolist()), ex=self.TTL)
                pipe.execute()
            except Exception as exc:
                logger.debug(f"Redis bulk write error: {exc}")

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, employee_id: int) -> Optional[np.ndarray]:
        if employee_id in self._memory:
            return self._memory[employee_id]
        if self._redis:
            try:
                key = f"{self.REDIS_KEY_PREFIX}{employee_id}"
                raw = self._redis.get(key)
                if raw:
                    enc = np.array(json.loads(raw), dtype=np.float64)
                    self._memory[employee_id] = enc
                    return enc
            except Exception:
                pass
        return None

    def all(self) -> Dict[int, np.ndarray]:
        return dict(self._memory)

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, employee_id: int) -> None:
        self._memory.pop(employee_id, None)
        if self._redis:
            try:
                self._redis.delete(f"{self.REDIS_KEY_PREFIX}{employee_id}")
            except Exception:
                pass

    def clear(self) -> None:
        self._memory.clear()

    def count(self) -> int:
        return len(self._memory)
