import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      const msg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        "Login failed. Check your credentials.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)] px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-[var(--accent-blue)] rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-blue-500/25">
            <Shield size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">FBS Detector</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Fake Base Station Detection System
          </p>
        </div>

        {/* Card */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-white mb-6">Sign in to your account</h2>

          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                className="w-full px-4 py-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)] focus:border-transparent transition"
                placeholder="Enter your username"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full px-4 py-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)] focus:border-transparent transition pr-11"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] hover:text-white transition"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg bg-[var(--accent-blue)] text-white font-medium hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)] focus:ring-offset-2 focus:ring-offset-[var(--bg-card)] disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-[var(--text-secondary)] mt-6">
          Detection of Fake Base Stations Using Machine Learning
        </p>
      </div>
    </div>
  );
}
