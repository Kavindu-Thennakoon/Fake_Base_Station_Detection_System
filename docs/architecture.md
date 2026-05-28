# System Architecture

## Overview

The Fake Base Station Detection System is a three-tier web application that uses machine learning to detect rogue cell towers from LTE/5G Measurement Report (MR) data.

## Architecture Diagram

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   React Frontend    │     │   Django REST API     │     │   ML Service        │
│                     │     │                      │     │                     │
│  - Dashboard        │     │  - detection app     │     │  - RRCF Training    │
│  - Detection Runs   │◄───►│  - alerts app        │◄───►│  - RRCF Detection   │
│  - Alerts           │HTTP │  - analytics app     │ sub │  - C++ Backend      │
│  - Anomalies + XAI  │     │  - accounts app      │proc │  - GPU Acceleration │
│  - Cell Models      │     │                      │     │                     │
│  - Geographic Map   │     │  ExplainabilityService│     │  Output CSVs:       │
│  - Training         │     │  MLBridge            │     │  - anomalies.csv    │
│  - Analytics        │     │  ReportParser        │     │  - neighbor_details │
│                     │     │                      │     │  - ranked neighbors │
│  Vite + Tailwind    │     │  SQLite / PostgreSQL  │     │  - windows + abnorm│
│  Recharts + Leaflet │     │  Token Auth          │     │                     │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
        │                              │                          │
        │                              │                          │
        ▼                              ▼                          ▼
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   PowerBI Desktop   │     │   SQLite Database    │     │   Trained Models    │
│   (External)        │◄────│   db.sqlite3         │     │   combined_meta.pkl │
│   4 Dashboard Pages │ CSV │                      │     │   798 cell .pkl     │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
```

## Data Flow

### Training Pipeline
1. Raw MR CSV data (46M+ rows) → `train_rrcf_gpu_mp_v4.py`
2. Per-cell feature engineering: `3×K` vector (Presence + RSRP + RSRQ)
3. 150 RRCF trees built per cell → `combined_meta.pkl` + per-cell `.pkl` files
4. `sync_cell_models` command loads metadata into Django `CellModel` table

### Detection Pipeline
1. New MR CSV uploaded via frontend → saved to `media/uploads/`
2. Django `MLBridge` triggers `detect_rrcf_v4.py` as subprocess
3. Two-layer detection (OR logic):
   - **Layer 1**: RRCF CoDisp score > threshold → flags unusual neighbor *combinations*
   - **Layer 2**: Z-Score > threshold → flags abnormal signal *values*
4. Post-processing: 30-min sliding window filter (≥10 events to survive)
5. Output: 5 CSV files parsed by `ReportParser` into database models

### Alert Generation
1. `SuspiciousNeighbor` records aggregated per detection run
2. Alerts generated with severity based on cumulative score + occurrence count
3. Alert lifecycle: New → Acknowledged → Resolved/False Positive
4. Full audit trail via `AlertHistory` model

### Explainability Flow
1. `ExplainabilityService` provides 3-level XAI:
   - **Per-anomaly**: RRCF score breakdown + neighbor Z-scores
   - **Per-cell**: Baseline profile + anomaly history
   - **Per-neighbor**: Cross-run risk profile

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React, Vite, Tailwind CSS v4 | React 19, Vite 8 |
| Charts | Recharts | 2.x |
| Maps | Leaflet, react-leaflet | 1.9, 5.x |
| UI Components | Lucide React, MUI | Latest |
| Backend | Django, Django REST Framework | Django 5.x |
| Auth | Token Authentication | DRF authtoken |
| Database | SQLite (dev), PostgreSQL (prod) | SQLite 3 |
| ML Engine | RRCF, pandas, NumPy, scikit-learn | Python 3.10+ |
| C++ Backend | pybind11, CMake | C++17 |
| PowerBI | PowerBI Desktop (Web connector) | Latest |

## Database Schema

### detection app
- `DetectionRun` — Pipeline execution records
- `TrainingRun` — Training pipeline records
- `CellModel` — Per-cell RRCF model metadata (K, CoDisp stats, neighbor baselines)
- `Anomaly` — Individual anomalous MR records
- `NeighborAnomalyDetail` — Per-neighbor signal details for each anomaly
- `SuspiciousNeighbor` — Aggregated suspicion rankings
- `DetectedWindow` — Time windows with anomaly clusters
- `AbnormalNeighbor` — Window-filtered summary
- `CellLocation` — Geographic coordinates for map visualization

### alerts app
- `Alert` — Security alerts with severity/status lifecycle
- `AlertHistory` — Audit trail for status transitions

### accounts app
- `UserProfile` — Role-based access (admin/analyst/viewer) + organization

## Security

- Token-based authentication (DRF `TokenAuthentication`)
- Role-based user profiles
- CORS restricted to frontend origin
- CSRF protection via Django middleware
- File upload validation (CSV only, 500MB max, header validation)
