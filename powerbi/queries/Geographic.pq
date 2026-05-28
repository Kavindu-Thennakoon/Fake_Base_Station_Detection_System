let
    BaseUrl = "http://localhost:8000/api/analytics/powerbi/geographic/",
    Source = Json.Document(Web.Contents(BaseUrl)),
    AsTable = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    Expanded = Table.ExpandRecordColumn(AsTable, "Column1", {
        "cell_id", "cell_name", "latitude", "longitude", "technology",
        "band", "anomaly_count", "suspicion_score", "is_unknown_operator",
        "risk_level"
    }),
    TypedColumns = Table.TransformColumnTypes(Expanded, {
        {"cell_id", type text},
        {"cell_name", type text},
        {"latitude", type number},
        {"longitude", type number},
        {"technology", type text},
        {"band", type text},
        {"anomaly_count", Int64.Type},
        {"suspicion_score", type number},
        {"is_unknown_operator", type logical},
        {"risk_level", type text}
    })
in
    TypedColumns
