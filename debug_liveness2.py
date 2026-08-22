import sys
import os
import cv2
import traceback

# Add backend directory to sys.path
backend_dir = r"c:\Users\radhe\OneDrive\Desktop\FRS\Face-Recognition-System\attendance_ai\backend"
sys.path.append(backend_dir)
os.chdir(backend_dir)  # Change CWD so resources/ are found!

try:
    print(f"CWD: {os.getcwd()}")
    from services.anti_spoof_service import AntiSpoofService
    svc = AntiSpoofService()
    
    # Create a dummy image
    import numpy as np
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw a shape to make it non-empty
    cv2.rectangle(dummy_img, (100, 100), (300, 300), (255, 255, 255), -1)
    
    face_loc = (100, 300, 300, 100) # top, right, bottom, left
    
    print("Testing check_liveness...")
    is_live, score, msg = svc.check_liveness(dummy_img, face_loc)
    print(f"Result: is_live={is_live}, score={score}, msg={msg}")
    
except Exception as e:
    print("EXCEPTION CAUGHT:")
    traceback.print_exc()
