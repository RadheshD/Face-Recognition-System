import sys
import os
import numpy as np
import logging

# Ensure backend dir is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from config import settings  # type: ignore
from services.face_service import FaceService  # type: ignore
from utils.embedding_cache import EmbeddingCache  # type: ignore

logging.basicConfig(level=logging.INFO)

def test_save_and_load():
    cache = EmbeddingCache(redis_url=settings.REDIS_URL)
    svc = FaceService(cache=cache)
    
    test_name = "Test User"
    test_encoding = np.random.rand(128).astype(np.float64)
    test_encoding /= np.linalg.norm(test_encoding)
    print(f"Adding {test_name}...")
    svc.save_encoding(test_encoding, test_name)
    
    # Reload to verify persistence
    svc_new = FaceService(cache=cache)
    if test_name in svc_new.known_names:
        print(f"SUCCESS: {test_name} found in reloaded encodings.")
        # Cleanup
        svc_new.remove_encodings_by_name(test_name)
        print("Cleanup done.")
    else:
        print(f"FAILURE: {test_name} NOT found in reloaded encodings.")

if __name__ == "__main__":
    test_save_and_load()
