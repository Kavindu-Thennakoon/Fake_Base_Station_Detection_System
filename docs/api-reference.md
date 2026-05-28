# API Reference

Base URL: `http://localhost:8000/api/`

All endpoints return JSON. Authentication via `Authorization: Token <token>` header.

---

## Authentication (`/api/accounts/`)

### POST `/accounts/register/`
Create a new user account.
```json
{ "username": "analyst1", "email": "a@fbs.local", "password": "SecurePass123!", "password_confirm": "SecurePass123!" }
```
Response `201`: `{ "token": "abc123...", "user": { "id": 1, "username": "analyst1", "profile": { "role": "analyst" } } }`

### POST `/accounts/login/`
```json
{ "username": "admin", "password": "admin123" }
```
Response `200`: `{ "token": "abc123...", "user": { ... } }`

### POST `/accounts/logout/`
Deletes the current token. Requires auth.

### GET `/accounts/me/`
Returns current user profile. Requires auth.

### POST `/accounts/change-password/`
```json
{ "old_password": "current", "new_password": "NewSecure456!" }
```

---

## Detection (`/api/detection/`)

### GET `/detection/runs/`
List all detection runs. Paginated (50 per page).

### GET `/detection/runs/{id}/`
Retrieve detection run detail including anomaly count, alert count, duration.

### POST `/detection/runs/`
Trigger a new detection run.
```json
{ "check_file": "/path/to/data.csv", "threshold_mult": 1.0, "z_threshold": 2.0, "min_anomaly_score": 4.0 }
```

### GET `/detection/training/`
List training runs.

### POST `/detection/training/`
Trigger a new training run.
```json
{ "train_file": "/path/to/train.csv", "num_trees": 150, "tree_size": 1024, "min_samples": 50 }
```

### GET `/detection/cells/`
List all trained cell models with K, CoDisp stats, training rows.

### GET `/detection/cells/{serving_cell_id}/`
Retrieve specific cell model including neighbor_stats and neighbor_order.

### GET `/detection/cells/{serving_cell_id}/profile/`
Cell health profile with anomaly count, threshold calculations.

### GET `/detection/anomalies/`
List anomalies. Supports query params: `?run_id=`, `?cell_id=`, `?page=`

### GET `/detection/anomalies/{id}/`
Retrieve anomaly detail.

### GET `/detection/anomalies/{id}/explain/`
XAI explanation including RRCF score breakdown, neighbor Z-scores, risk assessment.

### GET `/detection/model-status/`
Returns model status (loaded/demo), total cells, model size.

### GET `/detection/neighbors/{neighbor_id}/risk-profile/`
Cross-run risk profile for a specific neighbor cell.

### POST `/detection/upload/`
Upload CSV file. Multipart form data with `file` field.
Response: `{ "file_path": "...", "file_name": "...", "row_count": 1000, "headers_valid": true }`

---

## Alerts (`/api/alerts/`)

### GET `/alerts/`
List alerts. Supports `?status=new|acknowledged|resolved|false_positive`

### GET `/alerts/{id}/`
Retrieve alert with full audit history.

### POST `/alerts/{id}/acknowledge/`
Transition alert to "acknowledged" status. Creates audit trail entry.

### POST `/alerts/{id}/resolve/`
Transition alert to "resolved" status. Records resolver and timestamp.

### POST `/alerts/{id}/false-positive/`
Mark alert as false positive.

---

## Analytics (`/api/analytics/`)

### GET `/analytics/dashboard/`
Overview stats: total runs, anomalies, active alerts, cells trained, latest run.

### GET `/analytics/trends/`
Time-series anomaly data by date. Returns `[{ "date": "2026-05-20", "total": 35, "rrcf_count": 20, ... }]`

### GET `/analytics/cell-risk/?top=20`
Top N suspicious neighbors ranked by cumulative anomaly score.

### GET `/analytics/method-breakdown/?run_id=`
Detection method distribution: rrcf_only, zscore_only, both_layers counts.

### GET `/analytics/recent-activity/`
Last 10 detection runs with anomaly counts and durations.

### GET `/analytics/geographic/?run_id=`
Cell locations with anomaly counts, suspicion scores, and risk levels for map visualization.

### GET `/analytics/cell-anomaly-map/?run_id=`
Individual anomaly events with lat/lon for detailed map markers.

---

## PowerBI Export (`/api/analytics/powerbi/`)

All PowerBI endpoints support `?output=csv` for CSV download.

### GET `/analytics/powerbi/anomalies/`
Flat denormalized anomaly data with neighbor details (16 columns).

### GET `/analytics/powerbi/alerts/`
Alert data with resolution timeline including `resolution_hours`.

### GET `/analytics/powerbi/cell-risk/`
Cross-run cell risk aggregation with `is_unknown_operator` flag.

### GET `/analytics/powerbi/geographic/`
Cell locations with anomaly overlay for PowerBI map visual.
