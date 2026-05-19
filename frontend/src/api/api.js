import axios from 'axios';

const API = axios.create({
  baseURL: '/api',
});

// ── Detection ──
export const runDetection = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return API.post('/run-detection/', formData);
};

// ── Runs ──
export const getRunSummary     = (id) => API.get(`/runs/${id}/`);
export const getRunAnomalies   = (id) => API.get(`/runs/${id}/anomalies/`);
export const getNeighborDetail = (id) => API.get(`/runs/${id}/neighbor-details/`);
export const getNeighborRanked = (id) => API.get(`/runs/${id}/neighbor-ranked/`);
export const getAllRuns         = ()   => API.get('/runs/');

export default API;