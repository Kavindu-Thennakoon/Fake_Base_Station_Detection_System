import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload as UploadIcon, Loader, CheckCircle, AlertCircle } from 'lucide-react';
import { runDetection } from '../api/api';

export default function Upload() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle');   // idle | uploading | success | error
  const [result, setResult] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setStatus('uploading');

    try {
      const res = await runDetection(file);
      setResult(res.data);
      setStatus('success');
    } catch (err) {
      setResult({ message: err.message });
      setStatus('error');
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">📡 Run FBS Detection</h1>

      <form onSubmit={handleSubmit}
        className="bg-gray-900 border border-gray-800 rounded-xl p-8">

        {/* ── File Drop Zone ── */}
        <label className="block border-2 border-dashed border-gray-700 rounded-xl p-12
          text-center cursor-pointer hover:border-red-500/50 transition">
          <UploadIcon size={40} className="mx-auto mb-3 text-gray-500" />
          <p className="text-gray-400 mb-1">
            {file ? file.name : 'Click to select MR CSV file'}
          </p>
          <p className="text-xs text-gray-600">Measurement Report data (.csv)</p>
          <input type="file" accept=".csv" className="hidden"
            onChange={e => { setFile(e.target.files[0]); setStatus('idle'); }} />
        </label>

        {/* ── Submit Button ── */}
        <button type="submit"
          disabled={!file || status === 'uploading'}
          className={`mt-6 w-full py-3 rounded-lg font-semibold text-sm transition
            ${!file || status === 'uploading'
              ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
              : 'bg-red-600 hover:bg-red-700 text-white'}`}>
          {status === 'uploading' ? (
            <span className="flex items-center justify-center gap-2">
              <Loader size={16} className="animate-spin" /> Running Detection...
            </span>
          ) : 'Run Detection'}
        </button>
      </form>

      {/* ── Result Card ── */}
      {status === 'success' && result && (
        <div className="mt-6 bg-green-900/20 border border-green-800 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle size={20} className="text-green-400" />
            <h3 className="font-semibold text-green-400">Detection Complete</h3>
          </div>
          <p className="text-sm text-gray-300 mb-1">
            Run ID: <span className="font-mono text-white">#{result.run_id}</span>
          </p>
          <p className="text-sm text-gray-300 mb-4">
            Total Anomalies: <span className="font-bold text-red-400">{result.total_anomalies}</span>
          </p>
          <button onClick={() => navigate(`/runs/${result.run_id}`)}
            className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm transition">
            View Results →
          </button>
        </div>
      )}

      {status === 'error' && (
        <div className="mt-6 bg-red-900/20 border border-red-800 rounded-xl p-6">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} className="text-red-400" />
            <p className="text-red-400 text-sm">{result?.message || 'Detection failed'}</p>
          </div>
        </div>
      )}
    </div>
  );
}