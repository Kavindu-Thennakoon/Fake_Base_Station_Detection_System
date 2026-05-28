# Fake Base Station Detection System

**Detection of Fake Base Stations Using Machine Learning on LTE/5G Measurement Reports with an Explainable Web-Based System**

> BSc (Hons) in Computer Networks and Cyber Security  
> KIU — Kavindu Thennakoon (Reg: 14512)  
> Supervised by Mr. Tharindu De Zoysa

---

## Research Objectives Mapping

| # | Objective | Implementation |
|---|-----------|----------------|
| 1 | Data Engineering Pipeline | `ml_service/scripts/` — preprocessing, train/test split, feature engineering |
| 2 | RRCF Anomaly Detection Model | `ml_service/scripts/train_rrcf_gpu_mp_v4.py` + `detect_rrcf_v4.py` — 798 cell models, two-layer detection |
| 3 | Explainable Django Alert System | `backend/` — REST API, 3-level XAI, alert lifecycle with audit trail |
| 4 | Interactive Visualization + PowerBI | React dashboard (10 pages), Leaflet map, PowerBI export endpoints |
| 5 | System Evaluation | `ml_service/scripts/evaluate_model.py` — precision/recall/F1, simulated FBS attacks |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data --clear
python manage.py import_cell_locations
python manage.py runserver 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Login

Open **http://localhost:3000** and sign in:
- Username: `admin`
- Password: `admin123`

---

## System Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   React Frontend    │     │   Django REST API     │     │   ML Service        │
│   (Vite + Tailwind) │◄───►│   (DRF + SQLite)     │◄───►│   (RRCF + C++)      │
│   Port 3000         │HTTP │   Port 8000           │sub  │   GPU + MP          │
└─────────────────────┘     └──────────────────────┘proc └─────────────────────┘
```

### Detection Pipeline
1. CSV upload via web UI → validated and saved to server
2. `MLBridge` triggers `detect_rrcf_v4.py` subprocess
3. **Layer 1**: RRCF CoDisp score detects unusual neighbor *combinations*
4. **Layer 2**: Z-Score detects abnormal signal *values*
5. OR logic: flagged if *either* layer triggers
6. 30-min sliding window filter removes transient false positives
7. Results parsed into DB → alerts generated → XAI available

---

## Features

| Feature | Page |
|---------|------|
| Overview dashboard with system health | `/` |
| Detection run management with CSV upload | `/detection` |
| Alert management with lifecycle + audit trail | `/alerts` |
| Anomaly browser with filters + pagination | `/anomalies` |
| Per-anomaly XAI explanations | `/anomalies/:id` |
| Cell model viewer with radar chart + baselines | `/cells/:cellId` |
| Geographic map (Leaflet, risk-colored markers) | `/map` |
| Analytics charts and rankings | `/analytics` |
| Training run management | `/training` |
| PowerBI data export (JSON + CSV) | API only |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, Tailwind CSS v4, Recharts, Leaflet, Lucide |
| Backend | Django 5, Django REST Framework, Token Auth |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ML Engine | RRCF, pandas, NumPy, C++17 backend (pybind11) |
| Visualization | PowerBI Desktop via Web connector |

---

## Project Structure

```
Fake_Base_Station_Detection_System/
├── backend/                        # Django REST API
│   ├── detection/                  # Detection models, views, services
│   │   ├── models.py              # 9 models (DetectionRun, Anomaly, CellModel, etc.)
│   │   ├── views.py               # ViewSets + CSV upload
│   │   ├── services/              # MLBridge, ReportParser, ExplainabilityService
│   │   └── management/commands/   # seed_demo_data, sync_cell_models, import_cell_locations
│   ├── alerts/                     # Alert CRUD + audit trail
│   ├── analytics/                  # Dashboard stats, trends, PowerBI export
│   ├── accounts/                   # Auth (register, login, profiles)
│   └── fbs_project/               # Django settings + URL config
├── frontend/                       # React SPA
│   └── src/
│       ├── pages/                  # 10 pages (Dashboard, Map, CellDetail, etc.)
│       ├── components/             # Sidebar, MapView, FileUpload, etc.
│       ├── contexts/               # AuthContext
│       └── services/               # API layer (axios)
├── ml_service/                     # ML Pipeline
│   ├── scripts/
│   │   ├── train_rrcf_gpu_mp_v4.py
│   │   ├── detect_rrcf_v4.py
│   │   ├── generate_fbs_attack_data.py
│   │   └── evaluate_model.py
│   └── rrcf_cpp/                   # C++ RRCF backend (~25x faster)
├── powerbi/                        # PowerBI M queries + setup
│   ├── queries/                    # 4 .pq files for PowerBI import
│   └── README.md
├── docs/                           # Documentation
│   ├── architecture.md
│   ├── api-reference.md
│   ├── deployment.md
│   ├── user-manual.md
│   └── powerbi-setup.md
└── README.md
```

---

## Testing

### Backend Tests (53 tests)

```bash
cd backend
python manage.py test --verbosity=2
```

Tests cover: authentication flow, detection models + API, alert lifecycle + audit trail, analytics + PowerBI endpoints, CSV upload validation.

### ML Evaluation

```bash
cd ml_service/scripts
python generate_fbs_attack_data.py --output ../data/fbs_attack_test.csv --rows 5000
python evaluate_model.py --test-data ../data/fbs_attack_test.csv --demo-mode
```

Evaluation metrics (demo): Precision 0.756, Recall 0.868, F1 0.808, Accuracy 93.8%

---

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--num-trees` | 150 | RRCF trees per cell |
| `--tree-size` | 1024 | Max data points per tree |
| `--threshold-mult` | 1.0 | RRCF threshold = mean + mult * std |
| `--z-threshold` | 2.0 | Z-score threshold per metric |
| `--min-anomaly-score` | 4.0 | Min combined Z-score to flag |

---

## Documentation

- [System Architecture](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Deployment Guide](docs/deployment.md)
- [User Manual](docs/user-manual.md)
- [PowerBI Setup](docs/powerbi-setup.md)

---

## Author

**Kavindu Thennakoon** — KIU, Computer Networks & Cyber Security (Reg: 14512)
