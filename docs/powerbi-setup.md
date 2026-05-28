# PowerBI Integration Guide

## Overview

The FBS Detection System exposes four REST API endpoints specifically designed for PowerBI consumption. Each endpoint returns denormalized, analysis-ready data in both JSON and CSV formats.

## API Endpoints

| Endpoint | Description | PowerBI Page |
|----------|-------------|--------------|
| `/api/analytics/powerbi/anomalies/` | Flat anomaly data with neighbor details | Anomaly Trends |
| `/api/analytics/powerbi/alerts/` | Alert lifecycle with resolution timeline | Alert Management |
| `/api/analytics/powerbi/cell-risk/` | Cross-run cell risk aggregation | Cell Risk Analysis |
| `/api/analytics/powerbi/geographic/` | Cell locations + anomaly overlay | Geographic Heatmap |

All endpoints support `?output=csv` query parameter for CSV download.

## Base URL

```
http://localhost:8000/api/analytics/powerbi/
```

## Connecting PowerBI Desktop

### Method 1: Web Connector (Recommended)

1. Open PowerBI Desktop
2. Click **Get Data** → **Web**
3. Enter URL: `http://localhost:8000/api/analytics/powerbi/anomalies/`
4. Select **Anonymous** authentication
5. Click **OK** to load the data
6. Repeat for each endpoint (alerts, cell-risk, geographic)

### Method 2: CSV File Import

1. Download CSV from any endpoint by appending `?output=csv`
   - Example: `http://localhost:8000/api/analytics/powerbi/anomalies/?output=csv`
2. In PowerBI: **Get Data** → **Text/CSV** → Select downloaded file

### Method 3: Python Script (Advanced)

Use for automated refresh:

```python
import pandas as pd
import requests

BASE = "http://localhost:8000/api/analytics/powerbi"
anomalies = pd.DataFrame(requests.get(f"{BASE}/anomalies/").json())
alerts = pd.DataFrame(requests.get(f"{BASE}/alerts/").json())
cell_risk = pd.DataFrame(requests.get(f"{BASE}/cell-risk/").json())
geographic = pd.DataFrame(requests.get(f"{BASE}/geographic/").json())
```

## Data Model

### Table: Anomalies
| Column | Type | Description |
|--------|------|-------------|
| anomaly_id | Integer | Unique anomaly identifier |
| run_id | String | Detection run identifier |
| serving_cell_id | String | Cell being monitored (format: PLMN_CellID) |
| datetime | DateTime | When the anomaly was detected |
| avg_codisp | Decimal | RRCF CoDisp score (higher = more anomalous) |
| threshold | Decimal | Dynamic threshold (mean + mult × std) |
| rrcf_flagged | Boolean | Layer 1 detection triggered |
| zscore_flagged | Boolean | Layer 2 detection triggered |
| detection_method | String | "both", "rrcf_only", or "zscore_only" |
| neighbor_id | String | Neighbor cell involved in anomaly |
| neighbor_anomaly_score | Decimal | Combined Z-score for this neighbor |
| neighbor_rsrp | Decimal | Observed RSRP (dBm) |
| neighbor_rsrq | Decimal | Observed RSRQ (dB) |
| neighbor_rsrp_z | Decimal | RSRP Z-score vs training baseline |
| neighbor_rsrq_z | Decimal | RSRQ Z-score vs training baseline |

### Table: Alerts
| Column | Type | Description |
|--------|------|-------------|
| alert_id | Integer | Unique alert identifier |
| run_id | String | Source detection run |
| neighbor_id | String | Suspicious cell that triggered alert |
| severity | String | "critical", "high", "medium", "low" |
| status | String | "new", "acknowledged", "resolved", "false_positive" |
| affected_cells_count | Integer | Number of serving cells affected |
| peak_anomaly_score | Decimal | Highest cumulative score |
| created_at | DateTime | Alert creation time |
| resolved_at | DateTime | Resolution time (if resolved) |
| resolution_hours | Decimal | Hours from creation to resolution |
| resolved_by | String | Username who resolved |

### Table: Cell Risk
| Column | Type | Description |
|--------|------|-------------|
| neighbor_id | String | Cell ID under investigation |
| total_score | Decimal | Cumulative anomaly score across all runs |
| total_occurrences | Integer | Times flagged across all runs |
| runs_appeared | Integer | Number of detection runs with hits |
| affected_cells_count | Integer | Serving cells impacted |
| affected_cells | String | Semicolon-separated list of affected cells |
| is_unknown_operator | Boolean | True if cell doesn't match known MNO |
| risk_category | String | "critical", "high", "medium", "low" |

### Table: Geographic
| Column | Type | Description |
|--------|------|-------------|
| cell_id | String | Global cell identifier |
| cell_name | String | Human-readable site name |
| latitude | Decimal | WGS84 latitude |
| longitude | Decimal | WGS84 longitude |
| technology | String | "LTE", "5G-NR", "3G" |
| band | String | Frequency band (e.g., "B3 (1800)") |
| anomaly_count | Integer | Total anomalies at this cell |
| suspicion_score | Decimal | Cumulative suspicion score |
| is_unknown_operator | Boolean | Unknown operator flag |
| risk_level | String | "critical", "high", "medium", "low", "normal" |

## Recommended Dashboard Pages

### Page 1: Geographic Heatmap
- **Visual**: Map (Bing Maps or ArcGIS)
- **Data source**: Geographic table
- **Location**: latitude, longitude
- **Size**: anomaly_count
- **Color saturation**: suspicion_score
- **Legend**: risk_level
- **Tooltip**: cell_name, technology, band

### Page 2: Anomaly Trends
- **Visual**: Line chart (X = datetime, Y = count of anomaly_id)
- **Stacked by**: detection_method
- **Filters**: run_id slicer, serving_cell_id slicer
- **Cards**: Total anomalies, RRCF-only count, Z-Score-only count, Both count

### Page 3: Alert Management
- **Visual**: Funnel chart (severity distribution)
- **Visual**: Stacked bar (status by severity)
- **Visual**: KPI card (average resolution_hours)
- **Table**: Alert details with drill-through to anomalies

### Page 4: Cell Risk Analysis
- **Visual**: Treemap (neighbor_id sized by total_score, colored by risk_category)
- **Visual**: Bar chart (top 20 by total_occurrences)
- **Highlight**: Rows where is_unknown_operator = True (potential FBS)
- **Drill-through**: Click neighbor → filtered anomalies table

## Relationships

Set up the following relationships in PowerBI Model view:

```
Anomalies[neighbor_id] → Cell Risk[neighbor_id]  (Many-to-One)
Anomalies[serving_cell_id] → Geographic[cell_id]  (Many-to-One)
Alerts[neighbor_id] → Cell Risk[neighbor_id]  (Many-to-One)
Geographic[cell_id] → Cell Risk[neighbor_id]  (One-to-One, if exists)
```

## Refresh Schedule

For live dashboards during demo:
1. Set PowerBI data source to **Web** connector
2. Configure refresh interval in PowerBI Service (minimum 30 minutes)
3. For real-time: use **DirectQuery** mode with the Web connector

For offline demo:
1. Export CSV files from each endpoint
2. Import as static files in PowerBI
3. No refresh needed
