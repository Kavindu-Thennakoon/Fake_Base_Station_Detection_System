from fbs_service.detection_service import run_detection

result = run_detection(
    model_dir="model/v4_model",
    input_file="data/detect_30_filtered.csv",
    cell_details_file="data/Cell_Details.csv"
)

print(result)

if result["status"] == "success":
    print("Total anomalies:", result["total_anomalies"])
else:
    print("ERROR:", result["message"])