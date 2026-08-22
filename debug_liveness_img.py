import sys
import os
import cv2
import traceback
import numpy as np
import torch
import torch.nn.functional as F

# Add backend directory to sys.path
backend_dir = r"c:\Users\radhe\OneDrive\Desktop\FRS\Face-Recognition-System\attendance_ai\backend"
sys.path.append(backend_dir)
os.chdir(backend_dir)  # Change CWD so resources/ are found!

try:
    from services.anti_spoof_service import AntiSpoofService
    svc = AntiSpoofService()
    
    img_path = r"c:\Users\radhe\OneDrive\Desktop\FRS\Face-Recognition-System\attendance_ai\debug_capture.jpg"
    img = cv2.imread(img_path)
    
    if img is None:
        print(f"Could not load {img_path}")
        sys.exit(1)
        
    print(f"Loaded {img_path}, shape: {img.shape}")
    
    import face_recognition
    # Get a face location to use for crop
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    locs = face_recognition.face_locations(rgb)
    if not locs:
        print("No face found by face_recognition.")
        loc = (100, 300, 300, 100) # dummy
    else:
        loc = locs[0]
        print(f"Face found at {loc}")
    
    # Do exactly what the code does
    top, right, bottom, left = loc
    h, w = img.shape[:2]
    face_w = right - left
    face_h = bottom - top
    scale = 2.7
    cx, cy = left + face_w // 2, top + face_h // 2
    new_size = int(max(face_w, face_h) * scale)
    x1 = max(0, cx - new_size // 2)
    y1 = max(0, cy - new_size // 2)
    x2 = min(w, cx + new_size // 2)
    y2 = min(h, cy + new_size // 2)
    cropped = img[y1:y2, x1:x2]
    
    cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
    tensor_img = cv2.resize(cropped_rgb, svc.input_size)
    tensor_img = tensor_img.astype(np.float32) / 255.0
    tensor_img = (tensor_img - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    tensor_img = np.transpose(tensor_img, (2, 0, 1))
    tensor_img = torch.from_numpy(tensor_img).unsqueeze(0).to(svc.device).float()
    
    with torch.no_grad():
        outputs = svc.model(tensor_img)
        probs = F.softmax(outputs, dim=1).cpu().numpy()[0]
        
    print(f"Model RAW outputs: {outputs}")
    print(f"Model PROBS: {probs}")
    print(f"Class 0: {probs[0]:.4f}")
    print(f"Class 1: {probs[1]:.4f}")
    print(f"Class 2: {probs[2]:.4f}")
    
    # See what check_liveness returns
    is_live, score, msg = svc.check_liveness(img, loc)
    print(f"check_liveness Result: is_live={is_live}, score={score}, msg={msg}")
    
except Exception as e:
    print("EXCEPTION CAUGHT:")
    traceback.print_exc()
