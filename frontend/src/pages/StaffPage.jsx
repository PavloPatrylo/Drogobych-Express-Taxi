import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { ShieldAlert, Plus, RefreshCw, AlertCircle } from 'lucide-react';

export default function StaffPage() {
  const [staff, setStaff] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStaff = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get('/auth/staff');
      setStaff(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch staff:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStaff();
  }, []);

  const translateRole = (role) => {
    switch (role) {
      case 'admin': return 'Власник';
      case 'owner': return 'Власник';
      case 'dispatcher': return 'Диспетчер';
      case 'driver': return 'Водій';
      case 'passenger': return 'Пасажир';
      default: return role;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <ShieldAlert className="text-yellow-400" size={28} />
            <span>Управління персоналом</span>
          </h1>
          <p className="text-sm text-slate-400">
            Список водіїв та диспетчерів з бази даних
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchStaff}
            disabled={isLoading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-400 hover:text-slate-200 transition-colors"
            title="Оновити список"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
          </button>

          <button className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-yellow-500/10 text-sm">
            <Plus size={18} />
            <span>Додати співробітника</span>
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <RefreshCw className="animate-spin text-yellow-400" size={32} />
          <span>Завантаження персоналу з бази даних...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
          <AlertCircle size={18} className="shrink-0" />
          <span>Помилка: {error}</span>
        </div>
      )}

      {!isLoading && !error && staff.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
          <ShieldAlert size={40} className="mx-auto mb-3 text-slate-600" />
          <p className="font-semibold text-slate-200">Персонал не знайдено</p>
          <p className="text-xs text-slate-500 mt-1">Додайте першого співробітника у базу даних</p>
        </div>
      )}

      {!isLoading && !error && staff.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase font-semibold">
              <tr>
                <th className="p-4">Співробітник</th>
                <th className="p-4">Роль</th>
                <th className="p-4">Телефон</th>
                <th className="p-4 text-center">Статус</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {staff.map((member) => (
                <tr key={member.id} className="hover:bg-slate-800/40">
                  <td className="p-4 font-semibold text-slate-100">{member.full_name || member.name || 'Співробітник'}</td>
                  <td className="p-4">
                    <span className="bg-slate-800 text-yellow-400 font-medium px-2.5 py-1 rounded-lg border border-slate-700">
                      {translateRole(member.role)}
                    </span>
                  </td>
                  <td className="p-4 font-mono">{member.phone || '—'}</td>
                  <td className="p-4 text-center">
                    <span className={`px-2 py-0.5 rounded font-mono font-semibold text-[11px] ${
                      member.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                    }`}>
                      {member.is_active ? 'Активний' : 'Заблокований'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
