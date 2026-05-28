let
    BaseUrl = "http://localhost:8000/api/analytics/powerbi/cell-risk/",
    Source = Json.Document(Web.Contents(BaseUrl)),
    AsTable = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    Expanded = Table.ExpandRecordColumn(AsTable, "Column1", {
        "neighbor_id", "total_score", "total_occurrences", "runs_appeared",
        "affected_cells_count", "affected_cells", "is_unknown_operator",
        "risk_category"
    }),
    TypedColumns = Table.TransformColumnTypes(Expanded, {
        {"neighbor_id", type text},
        {"total_score", type number},
        {"total_occurrences", Int64.Type},
        {"runs_appeared", Int64.Type},
        {"affected_cells_count", Int64.Type},
        {"affected_cells", type text},
        {"is_unknown_operator", type logical},
        {"risk_category", type text}
    })
in
    TypedColumns
