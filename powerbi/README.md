# PowerBI Dashboard — FBS Detection System

## Quick Start

1. Open PowerBI Desktop
2. Use **Get Data → Blank Query** for each data source below
3. In the Advanced Editor, paste the corresponding M query from the `.pq` files
4. Set up relationships as described in `../docs/powerbi-setup.md`
5. Design dashboard pages using the recommended visuals

## Data Source Files

| File | PowerBI Table | Description |
|------|--------------|-------------|
| `queries/Anomalies.pq` | Anomalies | Denormalized anomaly + neighbor detail data |
| `queries/Alerts.pq` | Alerts | Alert lifecycle with resolution metrics |
| `queries/CellRisk.pq` | CellRisk | Cross-run neighbor risk ranking |
| `queries/Geographic.pq` | Geographic | Cell tower locations for map visual |

## How to Import M Queries

1. In PowerBI Desktop, click **Transform Data** (Power Query Editor)
2. Click **New Source → Blank Query**
3. Click **Advanced Editor**
4. Paste the contents of the `.pq` file
5. Click **Done**, then rename the query to match the table name
6. Repeat for each `.pq` file
7. Click **Close & Apply**

## Changing the Server URL

Each `.pq` file references `http://localhost:8000`. To change:
- Edit the `BaseUrl` variable in each query
- Or use a PowerBI Parameter for the base URL
