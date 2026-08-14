import React, { useState } from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import { useAuth } from '../../context/AuthContext';

export default function AdminLayout() {
  const { isAuthenticated } = useAuth();
  const [lastSyncTime, setLastSyncTime] = useState(new Date());
  const [isSyncing, setIsSyncing] = useState(false);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      // Simulate sync or dispatch global state update event
      await new Promise((resolve) => setTimeout(resolve, 600));
      setLastSyncTime(new Date());
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header onSync={handleSync} lastSyncTime={lastSyncTime} isSyncing={isSyncing} />
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
