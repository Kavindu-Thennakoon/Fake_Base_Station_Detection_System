# Deployment Guide

## Prerequisites

- Python 3.10+ (3.14 tested)
- Node.js 18+ (24.x tested)
- pip, npm/npx
- Git

## Quick Start (Development)

### 1. Clone and Setup Backend

```bash
git clone <repo-url>
cd Fake_Base_Station_Detection_System

# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Seed demo data (creates admin user: admin/admin123)
python manage.py seed_demo_data --clear

# Generate cell tower locations for map
python manage.py import_cell_locations

# Start backend
python manage.py runserver 8000
```

### 2. Setup Frontend

```bash
cd frontend
npm install

# Start dev server (proxies /api to backend:8000)
npm run dev
# → http://localhost:3000
```

### 3. Login

Open http://localhost:3000 and login with:
- **Username:** `admin`
- **Password:** `admin123`

## Management Commands

| Command | Description |
|---------|-------------|
| `python manage.py seed_demo_data --clear` | Seed DB with 4 detection runs, 160 anomalies, 57 alerts |
| `python manage.py import_cell_locations --clear` | Generate Sri Lankan cell tower coordinates |
| `python manage.py sync_cell_models` | Load trained models from combined_meta.pkl into DB |
| `python manage.py createsuperuser` | Create Django admin user |

## Configuration

### Backend Settings (`backend/fbs_project/settings.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `ML_DEMO_MODE` | `True` | Set `False` to use real ML pipeline |
| `ML_SERVICE_DIR` | `../ml_service` | Path to ML service directory |
| `ML_MODEL_DIR` | `../ml_service/model/v4_model` | Trained model directory |
| `MEDIA_ROOT` | `backend/media` | File upload destination |

### Frontend Config (`frontend/vite.config.js`)

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Production Mode

To use the real ML pipeline instead of demo mode:

```bash
# 1. Ensure trained models exist
ls ml_service/model/v4_model/combined_meta.pkl

# 2. Set production mode
# In settings.py: ML_DEMO_MODE = False

# 3. Sync cell models to DB
python manage.py sync_cell_models

# 4. Restart backend
python manage.py runserver 8000
```

## Database

### Development: SQLite (default)
No configuration needed. Database file: `backend/db.sqlite3`

### Production: PostgreSQL

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'fbs_detection',
        'USER': 'fbs_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Then run: `python manage.py migrate`

## Backup and Restore

### Create SQLite backup
```bash
cp backend/db.sqlite3 backend/db.sqlite3.backup
```

### Restore from backup
```bash
cp backend/db.sqlite3.backup backend/db.sqlite3
```

## Running Tests

```bash
cd backend
python manage.py test --verbosity=2
# 53 tests across 4 apps: accounts, detection, alerts, analytics
```

## ML Evaluation

```bash
cd ml_service/scripts

# Generate synthetic FBS attack test data
python generate_fbs_attack_data.py --output ../data/fbs_attack_test.csv --rows 5000

# Run evaluation (demo mode)
python evaluate_model.py --test-data ../data/fbs_attack_test.csv --demo-mode

# Run evaluation (with real detection results)
python evaluate_model.py --test-data ../data/fbs_attack_test.csv --results-dir ../output/eval_run/
```

## Building Frontend for Production

```bash
cd frontend
npm run build
# Output in frontend/dist/
# Serve with any static file server or Django's staticfiles
```
