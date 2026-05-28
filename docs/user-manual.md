# User Manual

## Getting Started

After logging in at http://localhost:3000, you'll see the main dashboard. The sidebar provides navigation to all system features.

## Dashboard

The dashboard provides an at-a-glance overview:
- **Stat Cards**: Detection runs, total anomalies, active alerts, trained cells
- **System Health Badge**: Shows "System Healthy" when models are loaded
- **Anomaly Trends Chart**: Time-series view of anomaly detections
- **Detection Method Pie Chart**: Breakdown of RRCF-only, Z-Score-only, and both-layer detections
- **Mini Map**: Preview of cell tower locations with risk coloring
- **Active Alerts**: Latest unresolved security alerts

## Detection Runs

### Triggering a Detection
1. Click **New Detection**
2. **Upload** a CSV file using the drag-and-drop zone (or click to browse)
3. The system validates CSV headers and shows row count
4. Adjust detection parameters if needed:
   - **Threshold Mult**: RRCF threshold multiplier (default 1.0)
   - **Z Threshold**: Z-score threshold (default 2.0)
   - **Min Score**: Minimum combined Z-score (default 4.0)
5. Click **Start Detection**

### Viewing Results
- Click any row in the runs table to see full details
- Details include anomaly count, alert count, duration, and linked anomalies

## Anomalies

The anomalies page shows all detected anomalous measurement reports.

### Filters
- **Run Selector**: Filter by specific detection run
- **Cell ID**: Filter by serving cell
- **Detection Method**: All Methods / Both Layers / RRCF Only / Z-Score Only

### Understanding Anomaly Data
- **CoDisp Score**: RRCF anomaly score. Higher = more anomalous
- **Threshold**: Dynamic threshold based on training baseline
- **Method**: Which detection layer(s) triggered

### Explaining an Anomaly
Click **Explain** on any anomaly to see the XAI breakdown:
- **RRCF Explanation**: Score vs threshold, how far above/below
- **Neighbor Breakdown**: Per-neighbor Z-scores showing which neighbors have abnormal signals
- **Risk Assessment**: Overall risk level with summary

## Alerts

### Alert Lifecycle
1. **New**: Automatically generated when suspicious neighbors are detected
2. **Acknowledged**: An analyst has seen and is investigating the alert
3. **Resolved**: Investigation complete, confirmed as legitimate or threat handled
4. **False Positive**: Determined to not be a real threat

### Managing Alerts
- Click the **eye icon** to acknowledge an alert
- Click the **check icon** to resolve
- Click the **X icon** to mark as false positive
- Click the **chevron** to expand details and see audit history

### Alert Severity
- **Critical**: Score ≥ 50 or occurrence count ≥ 100
- **High**: Score ≥ 20 or occurrence count ≥ 50
- **Medium**: Score ≥ 10 or occurrence count ≥ 20
- **Low**: Below medium thresholds

## Cell Models

Shows all trained RRCF models. Each row represents one serving cell.

### Health Status
- **Healthy**: Sufficient training data and stable baseline
- **Low Data**: Fewer than 100 training rows
- **Noisy**: High standard deviation in CoDisp scores

### Cell Detail Page
Click any cell row to see:
- **Baseline Stats**: K (neighbors), Mean/Std CoDisp, training rows
- **Radar Chart**: RSRP/RSRQ signal profile across neighbors
- **Neighbor Baselines**: Expected signal ranges for each neighbor
- **Anomaly History**: All anomalies detected for this cell

## Geographic Map

Interactive map of cell tower locations across the Colombo metro area.

### Risk Color Coding
- **Red**: Critical risk (FBS suspected)
- **Orange**: High risk
- **Yellow**: Medium risk
- **Blue**: Low risk
- **Green**: Normal (no anomalies)

### Features
- **Run Selector**: Filter by detection run
- **Severity Filter**: Show only specific risk levels
- **Cell Detail Panel**: Click any marker to see cell info
- **FBS Warning**: Unknown operator cells show a red warning banner

## Training

### Triggering Training
1. Click **New Training**
2. Upload training CSV data
3. Adjust parameters: Num Trees (150), Tree Size (1024), Min Samples (50)
4. Click **Start Training**

## Analytics

Advanced analytics page with:
- Dashboard statistics
- Anomaly trend charts
- Cell risk rankings
- Detection method breakdown

## PowerBI Integration

For PowerBI dashboards, see `docs/powerbi-setup.md`. Four data export endpoints are available at `/api/analytics/powerbi/` supporting both JSON and CSV output.

## Interpreting FBS Indicators

A cell is likely a Fake Base Station if:
1. **Unknown Operator**: Cell ID doesn't match any known MNO (e.g., starts with 99999 or 88888)
2. **Abnormally Strong Signal**: RSRP much stronger than normal (-50 to -44 dBm vs typical -80 to -90)
3. **Persistent Anomalies**: Appears in multiple time windows across multiple serving cells
4. **High Combined Z-Score**: Both RSRP and RSRQ significantly deviate from training baseline
5. **Multiple Detection Layers**: Flagged by both RRCF (unusual combination) and Z-Score (unusual values)
