import React from 'react';
import { RefreshCw, Bell, Clock, Sun, Moon, Zap, WifiOff } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useWebSocket } from '../../context/WebSocketContext';

export default function Header({ onSync, lastSyncTime, isSyncing }) {
  const { theme, toggleTheme } = useTheme();
  const { isConnected } = useWebSocket();

  const formatSyncTime = (date) => {
    if (!date) return 'Ще не синхронізовано';
    return date.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/50 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Route title & live WebSocket badge */}
      <div className="flex items-center gap-3">
        {isConnected ? (
          <>
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20 flex items-center gap-1.5 shadow-sm">
              <Zap size={13} className="text-emerald-400 fill-emerald-400" />
              <span>WS LIVE • РЕАЛЬНИЙ ЧАС</span>
            </span>
          </>
        ) : (
          <>
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
            </span>
            <span className="text-xs font-mono font-bold text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-lg border border-amber-500/20 flex items-center gap-1.5 shadow-sm">
              <WifiOff size={13} className="text-amber-400" />
              <span>ПЕРЕПІДКЛЮЧЕННЯ WS...</span>
            </span>
          </>
        )}
      </div>

      {/* Header controls & theme toggle */}
      <div className="flex items-center gap-3">
        {/* Sync status */}
        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 bg-slate-800/40 px-3 py-1.5 rounded-lg border border-slate-800">
          <Clock size={14} className="text-slate-500" />
          <span>Синхронізація: <span className="text-slate-200 font-mono">{formatSyncTime(lastSyncTime)}</span></span>
        </div>

        {/* Sync Action Button */}
        <button
          onClick={onSync}
          disabled={isSyncing}
          className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-lg font-medium border border-slate-700 transition-colors cursor-pointer disabled:opacity-50"
        >
          <RefreshCw size={14} className={isSyncing ? 'animate-spin text-yellow-400' : ''} />
          <span>Оновити</span>
        </button>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-yellow-400 text-xs px-3 py-1.5 rounded-lg font-bold border border-slate-700 transition-all cursor-pointer shadow-sm"
          title={theme === 'dark' ? 'Увімкнути світлу тему' : 'Увімкнути темну тему'}
        >
          {theme === 'dark' ? (
            <>
              <Sun size={15} className="text-yellow-400" />
              <span className="hidden md:inline text-slate-200">Світла</span>
            </>
          ) : (
            <>
              <Moon size={15} className="text-sky-400" />
              <span className="hidden md:inline text-slate-200">Темна</span>
            </>
          )}
        </button>

        {/* Quick Notifications */}
        <div className="flex items-center gap-1 text-slate-400 hover:text-slate-200 p-2 rounded-lg hover:bg-slate-800 cursor-pointer transition-colors">
          <Bell size={18} />
        </div>
      </div>
    </header>
  );
}
