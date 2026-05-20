import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import DetectionRuns from "./pages/DetectionRuns";
import RunDetail from "./pages/RunDetail";
import Alerts from "./pages/Alerts";
import Anomalies from "./pages/Anomalies";
import AnomalyExplain from "./pages/AnomalyExplain";
import CellModels from "./pages/CellModels";
import Analytics from "./pages/Analytics";
import Training from "./pages/Training";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="ml-64 flex-1 p-6 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/detection" element={<DetectionRuns />} />
            <Route path="/detection/:id" element={<RunDetail />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/anomalies" element={<Anomalies />} />
            <Route path="/anomalies/:id" element={<AnomalyExplain />} />
            <Route path="/cells" element={<CellModels />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/training" element={<Training />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}