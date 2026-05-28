let
    BaseUrl = "http://localhost:8000/api/analytics/powerbi/alerts/",
    Source = Json.Document(Web.Contents(BaseUrl)),
    AsTable = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    Expanded = Table.ExpandRecordColumn(AsTable, "Column1", {
        "alert_id", "run_id", "neighbor_id", "severity", "status",
        "title", "affected_cells_count", "peak_anomaly_score",
        "created_at", "resolved_at", "resolution_hours", "resolved_by"
    }),
    TypedColumns = Table.TransformColumnTypes(Expanded, {
        {"alert_id", Int64.Type},
        {"run_id", type text},
        {"neighbor_id", type text},
        {"severity", type text},
        {"status", type text},
        {"title", type text},
        {"affected_cells_count", Int64.Type},
        {"peak_anomaly_score", type number},
        {"created_at", type datetimezone},
        {"resolved_at", type datetimezone},
        {"resolution_hours", type number},
        {"resolved_by", type text}
    })
in
    TypedColumns
