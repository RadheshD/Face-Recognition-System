import sys
import os
import pickle
import numpy as np
import logging

# Ensure backend dir is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from config import settings
from services.face_service import FaceService
from utils.embedding_cache import EmbeddingCache

logging.basicConfig(level=logging.INFO)

def test_load():
    cache = EmbeddingCache(redis_url=settings.REDIS_URL)
    svc = FaceService(cache=cache)
    print(f"Known names count: {len(svc.known_names)}")
    print(f"Known names: {svc.known_names}")
    
    if len(svc.known_names) > 0:
        print("SUCCESS: encodings.pkl loaded successfully!")
    else:
        print("FAILURE: encodings.pkl is either empty or not found.")

if __name__ == "__main__":
    test_load()
