import sys
import os

sys.path.insert(0, r"c:\Users\radhe\OneDrive\Desktop\Face Recognition\attendance_ai\backend")

import main
from fastapi.testclient import TestClient
from security import get_current_admin
import numpy as np
import base64
import cv2

main.app.dependency_overrides[get_current_admin] = lambda: {"username": "admin"}

# Create fake image
img = np.zeros((100, 100, 3), dtype=np.uint8)
cv2.rectangle(img, (20,20), (80,80), (255,255,255), -1)

success, encoded = cv2.imencode('.jpg', img)
b64 = base64.b64encode(encoded).decode('utf-8')

# Mock detect faces to always return a bounding box
import services.face_service
def mock_detect_faces(self, img_rgb):
    return [(20, 80, 80, 20)]
services.face_service.FaceService.detect_faces = mock_detect_faces

from database import SessionLocal
import models
db = SessionLocal()

# clear and create employee
db.query(models.Attendance).delete()
db.query(models.Employee).delete()
emp = models.Employee(employee_code="E001", name="Test Emp")
db.add(emp)
db.commit()
db.refresh(emp)

with TestClient(main.app) as client:
    # MANUALLY ADD TO CACHE EXACTLY HOW REGISTER-FACE CACHE WOULD HAVE IT
    fake_encoding = np.zeros(128, dtype=np.float64)
    main.app.state.face_svc.update_cache_entry(emp.id, fake_encoding)
    
    r = client.post('/api/attendance/mark', json={'image_base64': b64})
    print("STATUS:", r.status_code)
    print("RESPONSE:", r.text)
