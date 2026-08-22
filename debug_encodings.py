import sys
sys.path.insert(0, './backend')
import pickle
import os
from database import SessionLocal
import models

print("Checking encodings.pkl")
pkl_path = "backend/encodings.pkl"
try:
    with open(pkl_path, "rb") as f:
        data = pickle.load(f)
    print("Datatype:", type(data))
    if isinstance(data, dict):
        print("Keys:", list(data.keys()))
        for k, v in data.items():
            print(f"  {k} -> type: {type(v)}, shape: {getattr(v, 'shape', 'No shape')}")
    else:
        print("Data is not dictionary!", type(data), data.keys() if hasattr(data, 'keys') else 'no keys')
except Exception as e:
    print("Failed to read pkl", e)

print("\nChecking Employees in DB")
db = SessionLocal()
emps = db.query(models.Employee).all()
for emp in emps:
    print(f"ID: {emp.id}, Name: {emp.name}, encoded? {emp.face_encoding is not None}")

