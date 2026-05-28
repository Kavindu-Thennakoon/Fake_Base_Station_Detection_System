let
    BaseUrl = "http://localhost:8000/api/analytics/powerbi/anomalies/",
    Source = Json.Document(Web.Contents(BaseUrl)),
    AsTable = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    Expanded = Table.ExpandRecordColumn(AsTable, "Column1", {
        "anomaly_id", "run_id", "serving_cell_id", "row_index", "datetime",
        "avg_codisp", "threshold", "rrcf_flagged", "zscore_flagged",
        "detection_method", "neighbor_id", "neighbor_anomaly_score",
        "neighbor_rsrp", "neighbor_rsrq", "neighbor_rsrp_z", "neighbor_rsrq_z"
    }),
    TypedColumns = Table.TransformColumnTypes(Expanded, {
        {"anomaly_id", Int64.Type},
        {"run_id", type text},
        {"serving_cell_id", type text},
        {"row_index", Int64.Type},
        {"datetime", type datetimezone},
        {"avg_codisp", type number},
        {"threshold", type number},
        {"rrcf_flagged", type logical},
        {"zscore_flagged", type logical},
        {"detection_method", type text},
        {"neighbor_id", type text},
        {"neighbor_anomaly_score", type number},
        {"neighbor_rsrp", type number},
        {"neighbor_rsrq", type number},
        {"neighbor_rsrp_z", type number},
        {"neighbor_rsrq_z", type number}
    })
in
    TypedColumns
