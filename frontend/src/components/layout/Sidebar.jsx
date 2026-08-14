import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { 
  Calendar, 
  Users, 
  Megaphone, 
  DollarSign, 
  Bus, 
  ShieldAlert, 
  Settings,
  LogOut, 
  Sparkles,
  ChevronRight
} from 'lucide-react';

export default function Sidebar() {
  const { user, isOwner, logout } = useAuth();

  const dispatcherNav = [
    { name: 'Розклад рейсів', path: '/schedule', icon: Calendar },
    { name: 'Клієнти (CRM)', path: '/crm', icon: Users },
    { name: 'Сповіщення', path: '/broadcast', icon: Megaphone },
  ];

  const ownerNav = [
    { name: 'Фінанси та Звіти', path: '/finance', icon: DollarSign },
    { name: 'Налаштування та Тарифи', path: '/settings', icon: Settings },
    { name: 'Автопарк', path: '/vehicles', icon: Bus },
    { name: 'Персонал', path: '/staff', icon: ShieldAlert },
  ];

  const getUserInitials = (name) => {
    if (!name) return 'АД';
    const parts = name.split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.substring(0, 2).toUpperCase();
  };

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between h-screen sticky top-0 z-30 select-none">
      {/* Brand Logo Header */}
      <div>
        <div className="p-6 border-b border-slate-800/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-yellow-500 to-amber-300 flex items-center justify-center font-display text-2xl text-slate-950 font-bold shadow-lg shadow-yellow-500/20">
            ET
          </div>
          <div>
            <h1 className="font-display text-xl tracking-wider text-slate-100 uppercase">
              Експрес Таксі
            </h1>
            <p className="text-xs text-yellow-400 font-medium flex items-center gap-1">
              <Sparkles size={12} /> CRM Panel v2.0
            </p>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="p-4 space-y-6">
          {/* Dispatcher Section */}
          <div>
            <div className="px-3 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Диспетчер
            </div>
            <div className="space-y-1">
              {dispatcherNav.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center justify-between px-3 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 ${
                        isActive
                          ? 'bg-yellow-400/10 text-yellow-400 font-semibold border border-yellow-400/20 shadow-sm'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                      }`
                    }
                  >
                    <div className="flex items-center gap-3">
                      <Icon size={18} />
                      <span>{item.name}</span>
                    </div>
                    <ChevronRight size={14} className="opacity-40" />
                  </NavLink>
                );
              })}
            </div>
          </div>

          {/* Owner Section (visible if owner or admin) */}
          {isOwner && (
            <div>
              <div className="px-3 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center justify-between">
                <span>Власник</span>
                <span className="bg-amber-500/20 text-amber-300 text-[10px] px-1.5 py-0.5 rounded font-mono">OWNER</span>
              </div>
              <div className="space-y-1">
                {ownerNav.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={({ isActive }) =>
                        `flex items-center justify-between px-3 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 ${
                          isActive
                            ? 'bg-amber-400/10 text-amber-400 font-semibold border border-amber-400/20 shadow-sm'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                        }`
                      }
                    >
                      <div className="flex items-center gap-3">
                        <Icon size={18} />
                        <span>{item.name}</span>
                      </div>
                      <ChevronRight size={14} className="opacity-40" />
                    </NavLink>
                  );
                })}
              </div>
            </div>
          )}
        </nav>
      </div>

      {/* User Footer Profile & Logout */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-900/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-sm text-yellow-400 shrink-0">
              {getUserInitials(user?.name)}
            </div>
            <div className="truncate">
              <div className="text-sm font-semibold text-slate-200 truncate">
                {user?.name || 'Адміністратор'}
              </div>
              <div className="text-xs text-slate-500 capitalize">
                {user?.role === 'owner' ? 'Власник' : 'Диспетчер'}
              </div>
            </div>
          </div>

          <button
            onClick={logout}
            title="Вийти з системи"
            className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </aside>
  );
}
