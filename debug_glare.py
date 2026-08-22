import sys
import cv2
import numpy as np

img_path = r"c:\Users\radhe\OneDrive\Desktop\FRS\Face-Recognition-System\attendance_ai\debug_capture.jpg"
img = cv2.imread(img_path)

if img is None:
    print("Cannot read image")
    sys.exit()

import face_recognition

rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
locs = face_recognition.face_locations(rgb)

if locs:
    top, right, bottom, left = locs[0]
    face_crop = img[top:bottom, left:right]
    
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    _, bright_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    bright_ratio = cv2.countNonZero(bright_mask) / (gray.shape[0] * gray.shape[1])

    print(f"Laplacian Var: {lap_var}")
    print(f"Bright Ratio: {bright_ratio}")
