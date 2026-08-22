import pickle
import numpy as np

data = pickle.load(open('backend/encodings.pkl', 'rb'))
encs = data['encodings']
names = data['names']
emp_ids = data['employee_ids']

print(f"Total encodings: {len(encs)}")
for i, enc in enumerate(encs):
    arr = np.asarray(enc)
    norm = float(np.linalg.norm(arr))
    valid = 0.75 <= norm <= 1.25
    print(f"  [{i}] name={names[i]}, emp_id={emp_ids[i]}, norm={norm:.4f}, valid_dlib={valid}")
