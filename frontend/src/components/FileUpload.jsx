import { useState, useRef } from "react";
import { Upload, FileText, X, CheckCircle, AlertCircle } from "lucide-react";
import { uploadCSV } from "../services/api";

export default function FileUpload({ onUploaded, accentColor = "var(--accent-blue)" }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const handleFile = async (file) => {
    if (!file) return;
    if (!file.name.endsWith(".csv")) {
      setError("Only CSV files are accepted.");
      return;
    }
    setError("");
    setResult(null);
    setUploading(true);
    try {
      const { data } = await uploadCSV(file);
      setResult(data);
      onUploaded?.(data);
    } catch (err) {
      const msg =
        err.response?.data?.file?.[0] ||
        err.response?.data?.detail ||
        "Upload failed.";
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const clear = () => {
    setResult(null);
    setError("");
    if (inputRef.current) inputRef.current.value = "";
    onUploaded?.(null);
  };

  if (result) {
    return (
      <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ background: `${accentColor}20` }}
            >
              <FileText size={20} style={{ color: accentColor }} />
            </div>
            <div>
              <p className="text-sm font-medium text-white">{result.file_name}</p>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                {result.row_count.toLocaleString()} rows
              </p>
            </div>
          </div>
          <button onClick={clear} className="text-[var(--text-secondary)] hover:text-white transition">
            <X size={16} />
          </button>
        </div>

        {result.headers_valid ? (
          <div className="flex items-center gap-2 mt-3 text-xs text-[var(--accent-green)]">
            <CheckCircle size={14} />
            Headers validated — ready for processing
          </div>
        ) : (
          <div className="mt-3 text-xs">
            <div className="flex items-center gap-2 text-[var(--accent-yellow)]">
              <AlertCircle size={14} />
              Some expected headers missing (file may still work)
            </div>
            {result.missing_headers.length > 0 && (
              <p className="text-[var(--text-secondary)] mt-1 ml-5">
                Missing: {result.missing_headers.join(", ")}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={() => setDragging(false)}
        onClick={() => inputRef.current?.click()}
        className={`relative rounded-lg border-2 border-dashed p-6 text-center cursor-pointer transition-all ${
          dragging
            ? "border-[var(--accent-blue)] bg-blue-500/5"
            : "border-[var(--border-color)] hover:border-[var(--accent-blue)]/50 hover:bg-[var(--bg-card-hover)]"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-[var(--text-secondary)]">Uploading...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload size={24} className="text-[var(--text-secondary)]" />
            <p className="text-sm text-white">
              Drop a CSV file here or <span style={{ color: accentColor }}>browse</span>
            </p>
            <p className="text-xs text-[var(--text-secondary)]">
              MR measurement report data (.csv, max 500 MB)
            </p>
          </div>
        )}
      </div>
      {error && (
        <p className="mt-2 text-xs text-[var(--accent-red)]">{error}</p>
      )}
    </div>
  );
}
