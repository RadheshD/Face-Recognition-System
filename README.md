# 👁️ FaceAttend AI — Autonomous Real-Time Facial Recognition Kiosk & Workforce Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-Anti--Spoofing-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

**FaceAttend AI** is a state-of-the-art, fully autonomous, zero-latency facial recognition attendance kiosk and workforce intelligence platform. Engineered to operate **100% on-premise**, it replaces legacy fingerprint scanners, physical swipe cards, and vulnerable manual sign-in sheets with sub-second biometrics, active deep-learning liveness detection (Anti-Spoofing), and adaptive lighting resilience.

---

## 🌟 Key Capabilities & Highlights

* ⚡ **Zero-Click Kiosk Mode**: Continuous live camera scanning with WebRTC streaming and dynamic HTML5 `<canvas>` bounding boxes. Employees walk up to the camera and are instantly logged without touching a button.
* 🛡️ **Active Deep-Learning Liveness (Anti-Spoofing)**: Integrated `MiniFASNet` PyTorch pipeline inspects texture, depth cues, and specular reflections to defeat presentation attacks (photos, smartphone/tablet screens, cutouts, and video replays).
* 🌓 **CLAHE Adaptive Lighting Resilience**: Enhanced image normalization using **CLAHE (Contrast Limited Adaptive Histogram Equalization)** ensures accurate facial detection under extreme lighting—direct glare, low-light corridors, or harsh background shadows.
* 🚀 **Sub-50ms RAM Vector Cache**: Biometric face descriptors (128-D vectors) are serialized into a high-performance in-memory matrix cache (`encodings.pkl`), executing C-speed Euclidean distance matching across thousands of profiles instantly.
* 🔄 **Smart Auto-Shift Toggling & Cooldown**: Automatically calculates shift progression (`CHECK_IN` ↔ `CHECK_OUT`) based on prior attendance history, with configurable cooldown timers to prevent duplicate accidental scans.
* 📊 **Executive Analytics & Reporting**: Rich browser-based dashboard featuring real-time attendance logs, department breakdowns, punctuality rates, late arrival tracking, and single-click CSV exports.
* 🌐 **Multi-Camera & Geofence Support**: Manage multiple USB/WebRTC or RTSP camera feeds alongside GPS geofencing parameters for remote or multi-entrance deployments.
* 🔐 **Privacy-First & On-Premise**: Zero cloud dependencies, zero external API consumption fees, and complete local data sovereignty over employee biometric templates.

---

## 🏗️ Architecture & Processing Pipeline

```
  +-----------------------------------------------------------------------------------+
  |                                  FRONTEND KIOSK                                  |
  |   WebRTC Camera Stream  --->  HTML5 Canvas Render  --->  Base64 Frame Snapshots   |
  +---------------------------------------------------+-------------------------------+
                                                      |
                                           HTTP POST  | /attendance/mark
                                                      v
  +-----------------------------------------------------------------------------------+
  |                                FASTAPI BACKEND API                                |
  |                                                                                   |
  |  1. CLAHE Image Normalization (Contrast & Exposure Balancing)                     |
  |  2. OpenCV Frame Rescaling & Bounding Box Detection                               |
  |  3. MiniFASNet Neural Liveness Check (Real vs Spoof Attack)                       |
  |  4. dlib 128-Dimensional Vector Embedding Generation                             |
  |  5. RAM Vector Cache Comparison (encodings.pkl - Euclidean Distance Engine)       |
  |  6. Chronological Shift Logic (CHECK_IN ↔ CHECK_OUT Auto-Toggle)                  |
  +---------------------------------------------------+-------------------------------+
                                                      |
                                          SQLAlchemy  | ACID Commit
                                                      v
  +-----------------------------------------------------------------------------------+
  |                                  LOCAL PERSISTENCE                                |
  |                 SQLite Database (attendance.db) & Pickle Vector File              |
  +-----------------------------------------------------------------------------------+
```

---

## 🛠️ Technology Stack & Technical Justification

| Layer | Technology | Primary Rationale & Engineering Advantage |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI (Python 3.10)** | Ultra-fast asynchronous non-blocking event loop; automatic OpenAPI/Swagger documentation; minimal request overhead. |
| **Computer Vision Engine** | **OpenCV + `face_recognition` (dlib)** | C++ optimized HOG (Histogram of Oriented Gradients) and Deep ResNet facial landmarks for 128-D vector mapping. |
| **Anti-Spoofing Engine** | **MiniFASNet + PyTorch** | Light-weight Convolutional Neural Network trained on presentation attack patterns for instantaneous real-time liveness scoring. |
| **Exposure Equalizer** | **CLAHE (OpenCV)** | Adaptive localized histogram normalization preventing recognition degradation under backlit or low-light conditions. |
| **Vector Storage** | **Pickle (.pkl) RAM Cache** | Eliminates database array coercion latency by loading raw NumPy vectors into system memory at boot for sub-50ms matching. |
| **Persistence Engine** | **SQLite & SQLAlchemy** | Zero-maintenance, single-file ACID-compliant relational storage. No external daemon configuration required. |
| **Frontend UI/UX** | **Vanilla HTML5 / CSS3 / ES6 JS** | Ultra-lightweight footprint, zero build-step overhead, native WebRTC hardware camera access, and responsive Glassmorphism layout. |
| **Security & Auth** | **JWT & Bcrypt (`passlib`)** | Role-based token access (Admin vs Kiosk) protecting settings, analytics, and employee record management. |

---

## 📂 Project Structure

```
attendance_ai/
├── backend/
│   ├── main.py                  # FastAPI Application Entry Point & CORS Setup
│   ├── config.py                # Environment Config & System Threshold Settings
│   ├── database.py              # SQLAlchemy Engine & Session Factory
│   ├── models.py                # Database ORM Schemas (Employees, Logs, Users, Geofence)
│   ├── schemas.py               # Pydantic Request/Response Validation Models
│   ├── security.py              # JWT Token Handling & Password Hashing
│   ├── encodings.pkl            # Serialized Vector Cache (128-D Face Embeddings)
│   ├── attendance.db            # SQLite Production Database File
│   ├── routes/                  # API Endpoint Controllers
│   │   ├── attendance_routes.py # /attendance/mark, /attendance/logs
│   │   ├── employee_routes.py   # Employee CRUD & Face Registration
│   │   ├── analytics_routes.py  # Summary Metrics & CSV Export Routes
│   │   ├── auth_routes.py       # Authentication & Token Issuance
│   │   ├── camera_routes.py     # Multi-Camera Feed Configurations
│   │   ├── geofence_routes.py   # GPS Boundary Verification
│   │   └── settings_routes.py   # System Threshold Adjustments
│   ├── services/
│   │   └── face_service.py      # Core AI Recognition & In-Memory Matching Service
│   └── utils/
│       ├── image_utils.py       # CLAHE Equalization & Frame Processing Utilities
│       └── liveness_utils.py    # MiniFASNet PyTorch Model Wrapper
├── frontend/
│   ├── index.html               # Main Entry / Redirect Controller
│   ├── kiosk.html               # Zero-Click WebRTC Attendance Kiosk Interface
│   ├── dashboard.html           # Real-Time Operational Overview
│   ├── analytics.html           # Deep Intelligence, Attendance Trends & CSV Export
│   ├── employees.html           # Employee Management & Instant Face Enrollment
│   ├── cameras.html             # Multi-Camera RTSP/USB Management Page
│   ├── settings.html            # Liveness, Cooldown, & System Threshold Controls
│   ├── login.html               # Admin & Manager Authentication Portal
│   ├── css/                     # Custom Responsive Glassmorphism Styling
│   └── js/                      # Modular WebRTC & API Client Scripts
├── docker/                      # Containerization Configurations
├── dlib-19.22.99-*.whl          # Pre-compiled C++ dlib Wheel for Windows x64
├── setup_windows.bat            # Automated One-Click Windows Setup Script
├── run_app.bat                  # Instant System Launch Batch Script
├── requirements.txt             # Python Package Dependencies
├── CHANGELOG_DETAILS.md         # Detailed System Update History
└── README.md                    # Project Documentation
```

---

## ⚡ Quick Start Guide (Windows Setup)

### Option A: One-Click Automated Setup (Recommended)

1. Double-click **`setup_windows.bat`** or execute it in PowerShell:
   ```cmd
   .\setup_windows.bat
   ```
   *This script automatically creates a Python virtual environment (`venv`), installs the pre-compiled `dlib` wheel, fetches all requirements, and initializes the SQLite database.*

2. Start the application by running:
   ```cmd
   .\run_app.bat
   ```
3. Open your browser and navigate to:
   - **Kiosk Interface**: [http://localhost:8000/frontend/kiosk.html](http://localhost:8000/frontend/kiosk.html)
   - **Admin Dashboard**: [http://localhost:8000/frontend/dashboard.html](http://localhost:8000/frontend/dashboard.html)
   - **Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option B: Manual Installation

#### Prerequisites
* **Python 3.10+ (64-bit)**
* **Git** & **C++ Build Tools** (if compiling dlib from source, or use the included pre-compiled wheel)

#### 1. Clone Repository & Prepare Environment
```bash
git clone https://github.com/your-username/Face-Recognition-System.git
cd Face-Recognition-System/attendance_ai

# Create Virtual Environment
python -m venv venv
# Activate on Windows:
venv\Scripts\activate
# Activate on Linux/macOS:
source venv/bin/activate
```

#### 2. Install Dependencies & C++ dlib Wheel
```bash
# Upgrade Pip & Install dlib wheel (Windows 64-bit Python 3.10)
python -m pip install --upgrade pip
pip install dlib-19.22.99-cp310-cp310-win_amd64.whl

# Install Python Libraries
pip install -r requirements.txt
```

#### 3. Start the Server
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔌 Core API Reference

### 1. Attendance Marking
* **`POST /attendance/mark`**
  * **Payload**: `FormData` containing Base64 image snapshot, optional `camera_id`, `latitude`, `longitude`.
  * **Response**:
    ```json
    {
      "status": "success",
      "action": "CHECK_IN",
      "employee_name": "Radhesh",
      "employee_id": "EMP-102",
      "confidence": 0.94,
      "liveness_passed": true,
      "timestamp": "2026-07-22T11:22:00"
    }
    ```

### 2. Employee Registration
* **`POST /employee/register`**
  * **Payload**: `FormData` (`name`, `department`, `employee_code`, `image_file`).
  * **Function**: Normalizes lighting via CLAHE, extracts 128-D embedding, appends vector to `encodings.pkl`, and saves database entry.

### 3. Analytics Summary
* **`GET /analytics/summary?period=today`**
  * **Response**: Total workforce count, present count, late arrivals, on-time percentage, and department activity.

---

## 📈 Recent System Updates & Engineering Fixes

As detailed in `CHANGELOG_DETAILS.md`:

1. **Manual-First Camera Control**: Backend camera auto-grabbing on startup was decoupled to eliminate hardware lockouts ("Device in use"). Cameras now initialize dynamically via client WebRTC signals.
2. **CLAHE Exposure Equalization**: Integrated Contrast Limited Adaptive Histogram Equalization into `utils/image_utils.py`, eliminating false negatives under severe shadow or backlighting.
3. **Engine-Agnostic Vector Loading**: Enhanced `services/face_service.py` loader to seamlessly synchronize legacy vectors with modern dlib encodings.
4. **Enhanced Data Persistence**: Refined transaction fallbacks ensuring strict SQLite consistency across continuous kiosk runs.

---

## 🔐 Security & Compliance

* **Data Privacy**: Biometric raw images can be discarded post-registration; only non-reconstructible 128-D numerical vector arrays are retained.
* **Anti-Spoofing Protection**: MiniFASNet neural evaluation blocks physical and digital presentation attacks.
* **Local Isolation**: Designed for air-gapped intranet environments with zero outbound internet traffic requirement.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

