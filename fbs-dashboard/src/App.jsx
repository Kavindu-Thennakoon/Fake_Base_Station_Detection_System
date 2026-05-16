import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import RunHistory from './pages/RunHistory';
import RunDetail from './pages/RunDetail';
import Explainability from './pages/Explainability';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-white">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/runs" element={<RunHistory />} />
            <Route path="/runs/:id" element={<RunDetail />} />
            <Route path="/runs/:id/explain" element={<Explainability />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;