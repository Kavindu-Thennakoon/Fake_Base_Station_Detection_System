import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Shield,
  AlertTriangle,
  Search,
  Radio,
  BarChart3,
  Brain,
  LogOut,
  User,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const links = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/detection", icon: Search, label: "Detection Runs" },
  { to: "/alerts", icon: AlertTriangle, label: "Alerts" },
  { to: "/anomalies", icon: Shield, label: "Anomalies" },
  { to: "/cells", icon: Radio, label: "Cell Models" },
  { to: "/analytics", icon: BarChart3, label: "Analytics" },
  { to: "/training", icon: Brain, label: "Training" },
];

export default function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-[var(--bg-secondary)] border-r border-[var(--border-color)] flex flex-col z-50">
      {/* Logo */}
      <div className="p-5 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[var(--accent-blue)] rounded-lg flex items-center justify-center">
            <Shield size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white leading-tight">
              FBS Detector
            </h1>
            <p className="text-xs text-[var(--text-secondary)]">
              Fake Base Station Detection
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-[var(--accent-blue)] text-white shadow-lg shadow-blue-500/20"
                  : "text-[var(--text-secondary)] hover:text-white hover:bg-[var(--bg-card-hover)]"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User & Logout */}
      <div className="p-4 border-t border-[var(--border-color)] space-y-3">
        {user && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[var(--accent-blue)]/20 flex items-center justify-center">
              <User size={16} className="text-[var(--accent-blue)]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{user.username}</p>
              <p className="text-xs text-[var(--text-secondary)] truncate capitalize">
                {user.profile?.role || "analyst"}
              </p>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-[var(--text-secondary)] hover:text-red-400 hover:bg-red-500/10 transition-all duration-200"
        >
          <LogOut size={16} />
          Sign out
        </button>
        <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
          <div className="w-2 h-2 rounded-full bg-[var(--accent-green)] animate-pulse" />
          System Online
        </div>
      </div>
    </aside>
  );
}
