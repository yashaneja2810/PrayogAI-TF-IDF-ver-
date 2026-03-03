import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Plus, LayoutGrid, LogOut, LayoutDashboard, Zap } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Navigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/create-bot', label: 'Create Bot', icon: Plus },
    { path: '/bots', label: 'My Bots', icon: LayoutGrid },
  ];

  return (
    <aside className="w-[232px] h-screen bg-white border-r border-gray-200 flex flex-col flex-shrink-0">
      {/* Logo */}
      <div className="px-5 h-14 flex items-center border-b border-gray-100">
        <button onClick={() => navigate('/dashboard')} className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-gray-900 rounded-md flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-gray-900 font-semibold text-sm tracking-tight">PrayogAI</span>
        </button>
      </div>

      {/* Section label */}
      <div className="px-5 pt-5 pb-2">
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Menu</span>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 px-3 space-y-0.5">
        {navItems.map(({ path, label, icon: Icon }) => {
          const isActive = location.pathname === path;
          return (
            <button
              key={path}
              onClick={() => navigate(path)}
              className={`w-full flex items-center gap-2.5 px-3 h-9 rounded-md text-[13px] font-medium transition-colors duration-100 ${isActive
                  ? 'bg-gray-100 text-gray-900'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
            >
              <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-gray-700' : ''}`} strokeWidth={isActive ? 2 : 1.5} />
              {label}
              {isActive && <div className="ml-auto w-1 h-4 bg-gray-900 rounded-full" />}
            </button>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="px-3 py-3 border-t border-gray-100 space-y-1">
        <div className="flex items-center gap-2 px-3 py-1">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
          <span className="text-[11px] text-gray-400">Operational</span>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2.5 px-3 h-9 rounded-md text-[13px] font-medium text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-colors duration-100"
        >
          <LogOut className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
          Sign Out
        </button>
      </div>
    </aside>
  );
};
