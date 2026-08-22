import re

with open('backend/services/face_service.py', 'r') as f:
    code = f.read()

# 1. Update init
code = code.replace(
    'self.known_employee_ids = []  # parallel list: employee_id for each encoding',
    'self.known_employee_ids = []  # parallel list: employee_id for each encoding\n        self.known_tenant_ids = []'
)

# 2. Update load_encodings initialization
code = code.replace(
    'raw_ids = data.get("employee_ids", [None] * len(raw_names))\n                    # Ensure all three lists are the same length\n                    min_len = min(len(raw_encodings), len(raw_names), len(raw_ids))\n                    raw_encodings = raw_encodings[:min_len]\n                    raw_names = raw_names[:min_len]\n                    raw_ids = raw_ids[:min_len]',
    'raw_ids = data.get("employee_ids", [None] * len(raw_names))\n                    raw_tids = data.get("tenant_ids", [1] * len(raw_names))\n                    # Ensure all lists are the same length\n                    min_len = min(len(raw_encodings), len(raw_names), len(raw_ids), len(raw_tids))\n                    raw_encodings = raw_encodings[:min_len]\n                    raw_names = raw_names[:min_len]\n                    raw_ids = raw_ids[:min_len]\n                    raw_tids = raw_tids[:min_len]'
)

# 3. Update load_encodings loop
code = code.replace(
    'clean_encodings, clean_names, clean_ids = [], [], []\n                    purge_count = 0\n                    for enc, nm, eid in zip(raw_encodings, raw_names, raw_ids):\n                        if self._is_dlib_encoding(np.asarray(enc)):\n                            clean_encodings.append(enc)\n                            clean_names.append(nm)\n                            clean_ids.append(eid)',
    'clean_encodings, clean_names, clean_ids, clean_tids = [], [], [], []\n                    purge_count = 0\n                    for enc, nm, eid, tid in zip(raw_encodings, raw_names, raw_ids, raw_tids):\n                        if self._is_dlib_encoding(np.asarray(enc)):\n                            clean_encodings.append(enc)\n                            clean_names.append(nm)\n                            clean_ids.append(eid)\n                            clean_tids.append(tid)'
)

# 4. Update load_encodings persist clean
code = code.replace(
    'cleaned_data = {"encodings": clean_encodings, "names": clean_names, "employee_ids": clean_ids}',
    'cleaned_data = {"encodings": clean_encodings, "names": clean_names, "employee_ids": clean_ids, "tenant_ids": clean_tids}'
)

# 5. Update load_encodings self assignments
code = code.replace(
    'self.known_employee_ids = clean_ids',
    'self.known_employee_ids = clean_ids\n                    self.known_tenant_ids = clean_tids'
)

# 6. Update load_encodings self assignments else
code = code.replace(
    'self.known_employee_ids = []\n                    \n                print(f"Encodings loaded:',
    'self.known_employee_ids = []\n                    self.known_tenant_ids = []\n                    \n                print(f"Encodings loaded:'
)

code = code.replace(
    'self.known_employee_ids = []\n                # Recreate the pkl file if corrupted',
    'self.known_employee_ids = []\n                self.known_tenant_ids = []\n                # Recreate the pkl file if corrupted'
)

code = code.replace(
    'data = {"encodings": [], "names": [], "employee_ids": []}\n                    with open(self.encodings_file, "wb") as f:',
    'data = {"encodings": [], "names": [], "employee_ids": [], "tenant_ids": []}\n                    with open(self.encodings_file, "wb") as f:'
)

code = code.replace(
    'self.known_employee_ids = []\n            \n            data = {"encodings": [], "names": [], "employee_ids": []}',
    'self.known_employee_ids = []\n            self.known_tenant_ids = []\n            \n            data = {"encodings": [], "names": [], "employee_ids": [], "tenant_ids": []}'
)

# 7. Update save_encoding
code = code.replace(
    'def save_encoding(self, encoding: np.ndarray, name: str, employee_id: int = None):',
    'def save_encoding(self, encoding: np.ndarray, name: str, employee_id: int = None, tenant_id: int = None):'
)

code = code.replace(
    'data = {"encodings": [], "names": [], "employee_ids": []}',
    'data = {"encodings": [], "names": [], "employee_ids": [], "tenant_ids": []}'
)

code = code.replace(
    'data["employee_ids"] = [None] * len(data["names"])',
    'data["employee_ids"] = [None] * len(data["names"])\n                        if "tenant_ids" not in data:\n                            data["tenant_ids"] = [1] * len(data["names"])'
)

code = code.replace(
    'data["names"].append(name)\n        data["employee_ids"].append(employee_id)',
    'data["names"].append(name)\n        data["employee_ids"].append(employee_id)\n        data["tenant_ids"].append(tenant_id if tenant_id is not None else 1)'
)

code = code.replace(
    'self.known_employee_ids = data["employee_ids"]\n        logger.info(',
    'self.known_employee_ids = data["employee_ids"]\n        self.known_tenant_ids = data["tenant_ids"]\n        logger.info('
)

# 8. Update remove_encodings_by_name
code = code.replace(
    'new_emp_ids = []\n                for enc, n, eid in zip(data["encodings"], data["names"], emp_ids):\n                    if n != name:\n                        new_encodings.append(enc)\n                        new_names.append(n)\n                        new_emp_ids.append(eid)',
    'new_emp_ids = []\n                tids = data.get("tenant_ids", [1] * len(data["names"]))\n                new_tids = []\n                for enc, n, eid, tid in zip(data["encodings"], data["names"], emp_ids, tids):\n                    if n != name:\n                        new_encodings.append(enc)\n                        new_names.append(n)\n                        new_emp_ids.append(eid)\n                        new_tids.append(tid)'
)

code = code.replace(
    'data["employee_ids"] = new_emp_ids\n                \n                with open(',
    'data["employee_ids"] = new_emp_ids\n                data["tenant_ids"] = new_tids\n                \n                with open('
)

code = code.replace(
    'self.known_employee_ids = data["employee_ids"]\n                logger.info',
    'self.known_employee_ids = data["employee_ids"]\n                self.known_tenant_ids = data["tenant_ids"]\n                logger.info'
)

# 9. find_best_match
find_best_match_old_body = """    def find_best_match(
        self, query_encoding: np.ndarray
    ) -> Tuple[Optional[str], float, Optional[int]]:
        \"\"\"
        Recognition Matching logic utilizing minimal distance index.
        Returns (name, confidence, employee_id).
        employee_id is retrieved directly from pickle to avoid DB name lookups.
        \"\"\"
        if not self.known_encodings:
            return None, 0.0, None

        if not _fr_available:
            # Fallback for when face_recognition is missing
            diffs = np.array(self.known_encodings) - query_encoding
            distances = np.linalg.norm(diffs, axis=1)
            best_idx = int(np.argmin(distances))
            if distances[best_idx] <= self.threshold * 12.0:
                name = self.known_names[best_idx]
                emp_id = self.known_employee_ids[best_idx] if self.known_employee_ids else None
            else:
                name = "Unknown"
                emp_id = None
            print(f"Recognized (fallback): {name} | emp_id={emp_id}")
            return (name, 100.0, emp_id) if name != "Unknown" else (None, 0.0, None)

        # face_recognition comparison
        matches = face_recognition.compare_faces(
            self.known_encodings, query_encoding, tolerance=self.threshold
        )
        distances = face_recognition.face_distance(self.known_encodings, query_encoding)
        if len(distances) == 0:
            return None, 0.0, None

        best_match_index = int(np.argmin(distances))
        min_dist = distances[best_match_index]

        if matches[best_match_index]:
            name = self.known_names[best_match_index]
            emp_id = (
                self.known_employee_ids[best_match_index]
                if self.known_employee_ids and best_match_index < len(self.known_employee_ids)
                else None
            )
        else:
            name = "Unknown"
            emp_id = None

        # Confidence calculation
        confidence = max(0.0, min(100.0, round((1.0 - min_dist) * 100.0, 2)))

        print(f"Recognized: {name} | dist={min_dist:.3f} | conf={confidence:.1f}% | emp_id={emp_id}")

        if name != "Unknown":
            return name, confidence, emp_id
        return None, confidence, None"""


find_best_match_new_body = """    def find_best_match(
        self, query_encoding: np.ndarray, tenant_id: int = None
    ) -> Tuple[Optional[str], float, Optional[int]]:
        \"\"\"
        Recognition Matching logic utilizing minimal distance index.
        Returns (name, confidence, employee_id).
        employee_id is retrieved directly from pickle to avoid DB name lookups.
        \"\"\"
        if not self.known_encodings:
            return None, 0.0, None

        tenant_indices = []
        if tenant_id is not None and hasattr(self, 'known_tenant_ids') and self.known_tenant_ids:
            for i, tid in enumerate(self.known_tenant_ids):
                if tid == tenant_id or tid is None: # handle legacy unassigned
                    tenant_indices.append(i)
        else:
            tenant_indices = list(range(len(self.known_encodings)))
            
        if not tenant_indices:
            return None, 0.0, None
            
        subset_encodings = [self.known_encodings[i] for i in tenant_indices]
        subset_names = [self.known_names[i] for i in tenant_indices]
        subset_emp_ids = [self.known_employee_ids[i] if self.known_employee_ids else None for i in tenant_indices]

        if not _fr_available:
            # Fallback for when face_recognition is missing
            diffs = np.array(subset_encodings) - query_encoding
            distances = np.linalg.norm(diffs, axis=1)
            best_idx = int(np.argmin(distances))
            if distances[best_idx] <= self.threshold * 12.0:
                name = subset_names[best_idx]
                emp_id = subset_emp_ids[best_idx]
            else:
                name = "Unknown"
                emp_id = None
            print(f"Recognized (fallback): {name} | emp_id={emp_id}")
            return (name, 100.0, emp_id) if name != "Unknown" else (None, 0.0, None)

        # face_recognition comparison
        matches = face_recognition.compare_faces(
            subset_encodings, query_encoding, tolerance=self.threshold
        )
        distances = face_recognition.face_distance(subset_encodings, query_encoding)
        if len(distances) == 0:
            return None, 0.0, None

        best_match_index = int(np.argmin(distances))
        min_dist = distances[best_match_index]

        if matches[best_match_index]:
            name = subset_names[best_match_index]
            emp_id = subset_emp_ids[best_match_index]
        else:
            name = "Unknown"
            emp_id = None

        # Confidence calculation
        confidence = max(0.0, min(100.0, round((1.0 - min_dist) * 100.0, 2)))

        print(f"Recognized: {name} | dist={min_dist:.3f} | conf={confidence:.1f}% | emp_id={emp_id}")

        if name != "Unknown":
            return name, confidence, emp_id
        return None, confidence, None"""

code = code.replace(find_best_match_old_body, find_best_match_new_body)

with open('backend/services/face_service.py', 'w') as f:
    f.write(code)

print("FaceService successfully rewritten.")
