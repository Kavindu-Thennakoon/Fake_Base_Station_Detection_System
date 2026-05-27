import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  },
);

// ── Detection Runs ──
export const getDetectionRuns = () => api.get("/detection/runs/");
export const getDetectionRun = (id) => api.get(`/detection/runs/${id}/`);
export const getRunSummary = (id) => api.get(`/detection/runs/${id}/summary/`);
export const getRunAnomalies = (id, params) =>
  api.get(`/detection/runs/${id}/anomalies/`, { params });
export const getRunSuspiciousNeighbors = (id) =>
  api.get(`/detection/runs/${id}/suspicious-neighbors/`);
export const getRunWindows = (id) =>
  api.get(`/detection/runs/${id}/windows/`);
export const triggerDetection = (data) =>
  api.post("/detection/runs/trigger/", data);

// ── Training ──
export const getTrainingRuns = () => api.get("/detection/training/");
export const triggerTraining = (data) =>
  api.post("/detection/training/trigger/", data);

// ── Anomalies ──
export const getAnomalies = (params) =>
  api.get("/detection/anomalies/", { params });
export const getAnomaly = (id) => api.get(`/detection/anomalies/${id}/`);
export const getAnomalyExplanation = (id) =>
  api.get(`/detection/anomalies/${id}/explain/`);

// ── Cell Models ──
export const getCellModels = () => api.get("/detection/cells/");
export const getCellProfile = (cellId) =>
  api.get(`/detection/cells/${cellId}/profile/`);
export const getModelStatus = () => api.get("/detection/model-status/");

// ── Alerts ──
export const getAlerts = (params) => api.get("/alerts/", { params });
export const getAlert = (id) => api.get(`/alerts/${id}/`);
export const acknowledgeAlert = (id, data) =>
  api.post(`/alerts/${id}/acknowledge/`, data || {});
export const resolveAlert = (id, data) =>
  api.post(`/alerts/${id}/resolve/`, data || {});
export const markFalsePositive = (id, data) =>
  api.post(`/alerts/${id}/false-positive/`, data || {});

// ── Analytics ──
export const getDashboardStats = () => api.get("/analytics/dashboard/");
export const getAnomalyTrends = () => api.get("/analytics/trends/");
export const getCellRiskRanking = (top) =>
  api.get("/analytics/cell-risk/", { params: { top } });
export const getMethodBreakdown = (runId) =>
  api.get("/analytics/method-breakdown/", { params: { run_id: runId } });
export const getRecentActivity = () => api.get("/analytics/recent-activity/");

// ── Auth ──
export const loginUser = (data) => api.post("/accounts/login/", data);
export const logoutUser = () => api.post("/accounts/logout/");
export const getCurrentUser = () => api.get("/accounts/me/");
export const registerUser = (data) => api.post("/accounts/register/", data);
export const changePassword = (data) => api.post("/accounts/change-password/", data);

// ── Neighbor Risk Profile ──
export const getNeighborRiskProfile = (neighborId) =>
  api.get(`/detection/neighbors/${neighborId}/risk-profile/`);

export default api;