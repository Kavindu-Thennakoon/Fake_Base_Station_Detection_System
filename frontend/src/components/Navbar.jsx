import { Link, useLocation } from 'react-router-dom';
import { Shield, Upload, History, LayoutDashboard } from 'lucide-react';

const links = [
  { to: '/',       label: 'Dashboard', icon: LayoutDashboard },
  { to: '/upload', label: 'Run Detection', icon: Upload },
  { to: '/runs',   label: 'History', icon: History },
];

export default function Navbar() {
  const { pathname } = useLocation();

  return (
    <nav className="bg-gray-900 border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4 flex items-center h-16 gap-8">
        <Link to="/" className="flex items-center gap-2 text-red-500 font-bold text-lg">
          <Shield size={24} />
          FBS Detector
        </Link>

        <div className="flex gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition
                ${pathname === to
                  ? 'bg-red-600/20 text-red-400'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}