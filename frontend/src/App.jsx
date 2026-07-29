import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AdminLayout from './components/layout/AdminLayout';
import LoginPage from './pages/LoginPage';
import SchedulePage from './pages/SchedulePage';
import CrmPage from './pages/CrmPage';
import BroadcastPage from './pages/BroadcastPage';
import FinancePage from './pages/FinancePage';
import SettingsPage from './pages/SettingsPage';
import VehiclesPage from './pages/VehiclesPage';
import StaffPage from './pages/StaffPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AdminLayout />}>
        <Route index element={<Navigate to="/schedule" replace />} />
        <Route path="schedule" element={<SchedulePage />} />
        <Route path="crm" element={<CrmPage />} />
        <Route path="broadcast" element={<BroadcastPage />} />
        <Route path="finance" element={<FinancePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="vehicles" element={<VehiclesPage />} />
        <Route path="staff" element={<StaffPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/schedule" replace />} />
    </Routes>
  );
}
