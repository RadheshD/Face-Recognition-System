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
    
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    mag = 20 * np.log(np.abs(fshift) + 1)
    ch, cw = mag.shape
    cy, cx = ch//2, cw//2
    mag[max(0, cy-15):min(ch, cy+15), max(0, cx-15):min(cw, cx+15)] = 0
    hf_mean = np.mean(mag)
    
    print(f"Laplacian Var: {lap_var}")
    print(f"High Freq Mean: {hf_mean}")
    
