# 🛡️ Fake Base Station Detection System

[![CI/CD](https://github.com/Kavindu-Thennakoon/Fake_Base_Station_Detection_System/actions/workflows/ci.yml/badge.svg)](https://github.com/Kavindu-Thennakoon/Fake_Base_Station_Detection_System/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Django 4.2](https://img.shields.io/badge/django-4.2-092E20?logo=django&logoColor=white)](https://djangoproject.com)
[![React 18](https://img.shields.io/badge/react-18-61DAFB?logo=react&logoColor=black)](https://reactjs.org)
[![C++17](https://img.shields.io/badge/c++-17-00599C?logo=cplusplus&logoColor=white)](https://isocpp.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **An AI-powered system for detecting fake (rogue) base stations in 4G LTE networks** using the
> **Robust Random Cut Forest (RRCF)** anomaly detection algorithm with GPU acceleration
> and a C++ optimized backend (~25× faster than pure Python).

---

## 🏗️ System Architecture

```
┌──────────────────┐       ┌───────────────────┐       ┌────────────────────────┐
│                  │       │                   │       │                        │
│   React 18       │◄─────►│   Django REST     │◄─────►│   ML Service           │
│   Dashboard      │ HTTP  │   API (DRF)       │       │   (RRCF + C++ Backend) │
│   (Vite)         │       │   Port 8000       │       │   GPU + Multiprocessing│
│                  │       │                   │       │                        │
└──────────────────┘       └────────┬──────────┘       └───────────┬────────────┘
                                    │                              │
                              ┌─────▼──────┐              ┌───────▼──────────┐
                              │            │              │                  │
                              │ PostgreSQL │              │  Cell Tower MR   │
                              │ Database   │              │  Data (CSV)      │
                              │            │              │                  │
                              └────────────┘              └──────────────────┘
```

---

## 📋 Features

| Feature | Description |
|---------|-------------|
| 🔍 **Real-Time Anomaly Detection** | Detects rogue cell towers from Measurement Report (MR) data using RRCF |
| ⚡ **GPU-Accelerated Training** | CUDA support via `cudf.pandas` for large-scale datasets |
| 🚀 **C++ Optimized Backend** | pybind11-based C++ RRCF implementation — ~25× faster than pure Python |
| 🧠 **Two-Layer Detection** | Layer 1: RRCF anomaly score + Layer 2: Z-Score neighbor check (OR logic) |
| 📊 **Interactive Dashboard** | Real-time charts, cell tower maps, anomaly tables |
| 🔌 **REST API** | Full CRUD API for programmatic access to detection results |
| 📈 **Explainable AI** | Analytics for anomaly interpretation and investigation |
| 🏗️ **Parallel Processing** | Multiprocessing (loky) for parallel per-cell training across 800+ cells |
| 🪟 **Window Filtering** | Sliding window post-processing to reduce false positives |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **ML Pipeline** | Python 3.10+, RRCF, pandas, NumPy, joblib, tqdm, scikit-learn |
| **C++ Backend** | C++17, pybind11, CMake |
| **API Backend** | Django 4.2, Django REST Framework, Celery, Redis |
| **Frontend** | React 18, Vite, Axios, Recharts, Leaflet |
| **Database** | PostgreSQL 15 |
| **DevOps** | Docker, Docker Compose, GitHub Actions CI/CD |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- Docker & Docker Compose (optional)

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/Kavindu-Thennakoon/Fake_Base_Station_Detection_System.git
cd Fake_Base_Station_Detection_System
cp .env.example .env          # Configure your environment variables
docker-compose up --build     # Start all services
```

Access the app:
- **Frontend Dashboard:** http://localhost:5173
- **Backend API:** http://localhost:8000/api/v1/
- **API Docs:** http://localhost:8000/api/docs/

### Option 2: Manual Setup

#### 1️⃣ ML Service

```bash
cd ml_service
python -m venv venv && source venv/bin/activate    # Create virtual env
pip install -r requirements.txt                     # Install dependencies

# Install C++ backend (optional but recommended — 25× faster)
cd rrcf_cpp && bash install.sh && cd ..

# Train the model
python scripts/train_rrcf_gpu_mp_v4.py \
  --train-file data/processed/train_70_filtered.csv \
  --model-dir models/v4_model \
  --cell-details-file data/raw/Cell_Details.csv \
  --num-trees 150 --tree-size 1024 --n-jobs 4

# Run detection
python scripts/detect_rrcf_v4.py \
  --model-dir models/v4_model \
  --check-file data/processed/newnewdetect_30_filtered.csv \
  --cell-details-file data/raw/Cell_Details.csv \
  --output-dir output \
  --threshold-mult 1.0 --z-threshold 2.0 --min-anomaly-score 4.0 --n-jobs -1
```

#### 2️⃣ Backend API

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env     # Configure database credentials
python manage.py migrate       # Apply database migrations
python manage.py createsuperuser
python manage.py runserver     # Start API at http://localhost:8000
```

#### 3️⃣ Frontend Dashboard

```bash
cd frontend
npm install                    # Install Node dependencies
npm run dev                    # Start dev server at http://localhost:5173
```

---

## 🧠 How It Works

### The RRCF Algorithm

The system uses **Robust Random Cut Forest (RRCF)** — an unsupervised anomaly detection algorithm:

1. **Training Phase** — Learns normal neighbor patterns for each serving cell from historical Measurement Report data
2. **Feature Engineering** — Each MR is converted to a `3×K` feature vector: `[Presence | RSRP | RSRQ]` for all K neighbors
3. **Forest Building** — 150 RRCF trees built per cell, each with up to 1024 data points
4. **Detection Phase** — New MR data is scored against trained models

### Two-Layer Detection (OR Logic)

```
Layer 1: RRCF Score      →  Detects unusual neighbor COMBINATIONS
Layer 2: Z-Score Check   →  Detects abnormal signal VALUES for known neighbors

IF (RRCF score > threshold) OR (Z-score > threshold) → FLAG AS ANOMALY
```

### Window Filter (Post-Processing)

A sliding window reduces false positives:
- A neighbor must appear anomalous **≥10 times** within any **30-minute window**
- Only persistent anomalies survive → reported in final output

---

## 📊 Data

The system processes **4G LTE Measurement Report data** with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `Cell_Name` | String | Human-readable cell tower name |
| `Site_ID` | String | Physical site identifier |
| `Node_Id` | Integer | Network node identifier |
| `Cell_Id` | Integer | Unique cell identifier |
| `Technology` | String | Network technology (4G LTE FDD) |
| `Technology_Description` | String | Detailed tech description |
| `Band` | Integer | Frequency band number |
| `Global_Cellid` | Integer | Global unique cell ID (`eNodeBID × 256 + CellID`) |

### MR (Measurement Report) Data Format

| Column | Description |
|--------|-------------|
| `serving_cell_id` | Tower the phone is connected to |
| `time_timestamp` | Measurement timestamp |
| `nbr_cell_[1-4]_id` | Neighbor cell IDs (up to 4) |
| `nbr_cell_[1-4]_rsrp` | Signal strength per neighbor (dBm) |
| `nbr_cell_[1-4]_rsrq` | Signal quality per neighbor (dB) |

---

## 📁 Project Structure

```
Fake_Base_Station_Detection_System/
│
├── ml_service/                         # ML Pipeline Service
│   ├── config/                         # Global settings & logging
│   ├── data/
│   │   ├── raw/Cell_Details.csv        # Cell tower whitelist
│   │   └── processed/                  # Train/test splits
│   ├── scripts/
│   │   ├── train_rrcf_gpu_mp_v4.py    # Training (GPU + multiprocessing)
│   │   ├── detect_rrcf_v4.py          # Detection / inference
│   │   └── data_preprocessing.py      # Data cleaning & feature eng.
│   ├── rrcf_cpp/                       # C++ RRCF backend (25× faster)
│   │   ├── include/rctree.hpp         # C++ tree implementation
│   │   ├── src/bindings.cpp           # pybind11 Python↔C++ bridge
│   │   ├── setup.py                   # Build configuration
│   │   └── install.sh                 # One-click installer
│   ├── models/                         # Trained model artifacts
│   ├── output/                         # Detection run outputs
│   ├── notebooks/                      # Jupyter EDA & experiments
│   └── tests/                          # ML pipeline tests
│
├── backend/                            # Django REST API
│   ├── fbs_api/                        # Django project settings
│   ├── detection/                      # Detection app (models, views, API)
│   ├── analytics/                      # XAI & analytics endpoints
│   └── users/                          # Authentication & authorization
│
├── frontend/                           # React Dashboard (Vite)
│   └── src/
│       ├── components/                 # Charts, maps, tables
│       ├── pages/                      # Dashboard, Detection, Analytics
│       └── services/                   # API integration (Axios)
│
├── docs/                               # Documentation
├── .github/workflows/                  # CI/CD pipelines
├── docker-compose.yml                  # Multi-service orchestration
├── .gitignore                          # Git ignore rules
├── .env.example                        # Environment variable template
├── LICENSE                             # MIT License
└── README.md                           # This file
```

---

## ⚡ Performance Benchmarks

| Metric | Python `rrcf` | C++ `_rrcf_core` | Speedup |
|--------|--------------|-------------------|---------|
| Tree build (150 trees, 1024 pts) | ~45 sec/cell | ~1.8 sec/cell | **~25×** |
| Batch scoring (1000 rows) | ~12 sec | ~0.5 sec | **~24×** |
| Full training (800K rows, 800 cells) | ~4 hours | ~9 min | **~32×** |
| Full detection (350K rows, 800 cells) | ~8 hours | ~11 min | **~48×** |

---

## 🔧 Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--num-trees` | 150 | Number of RRCF trees per cell |
| `--tree-size` | 1024 | Max data points per tree |
| `--threshold-mult` | 1.0 | RRCF threshold = mean + mult × std |
| `--z-threshold` | 2.0 | Z-score threshold per metric |
| `--min-anomaly-score` | 4.0 | Min combined Z-score to flag neighbor |
| `--min-samples` | 50 | Skip cells with fewer training rows |
| `--n-jobs` | 4 | Parallel workers (-1 = all CPUs) |

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Kavindu Thennakoon**

- 🐙 GitHub: [@Kavindu-Thennakoon](https://github.com/Kavindu-Thennakoon)
- 🎓 KIU — Computer Networks & Cyber Security

---

<p align="center">
  <i>Built with ❤️ for telecom network security</i>
</p>
