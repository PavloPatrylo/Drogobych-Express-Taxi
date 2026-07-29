import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Bus, Plus, RefreshCw, AlertCircle } from 'lucide-react';

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchVehicles = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get('/vehicles');
      setVehicles(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch vehicles:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchVehicles();
  }, []);

  const handleToggleStatus = async (id) => {
    try {
      await api.request(`/vehicles/${id}/toggle-active`, { method: 'PATCH' });
      fetchVehicles();
    } catch (err) {
      alert(`Помилка: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <Bus className="text-yellow-400" size={28} />
            <span>Управління автопарком</span>
          </h1>
          <p className="text-sm text-slate-400">
            Реальний реєстр мікроавтобусів з бази даних PostgreSQL
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchVehicles}
            disabled={isLoading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-400 hover:text-slate-200 transition-colors"
            title="Оновити список"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
          </button>
          <button className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-yellow-500/10 text-sm">
            <Plus size={18} />
            <span>Додати авто</span>
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <RefreshCw className="animate-spin text-yellow-400" size={32} />
          <span>Завантаження автопарку з бази даних...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
          <AlertCircle size={18} className="shrink-0" />
          <span>Помилка: {error}</span>
        </div>
      )}

      {!isLoading && !error && vehicles.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
          <Bus size={40} className="mx-auto mb-3 text-slate-600" />
          <p className="font-semibold text-slate-200">Автомобілів ще не додано</p>
          <p className="text-xs text-slate-500 mt-1">Натисніть "+ Додати авто", щоб внести першу машину у базу</p>
        </div>
      )}

      {!isLoading && !error && vehicles.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {vehicles.map((v) => (
            <div key={v.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-lg font-bold text-yellow-400 bg-slate-950 px-3 py-1 rounded-lg border border-slate-800">
                  {v.plate_number || v.plate}
                </span>
                <button
                  onClick={() => handleToggleStatus(v.id)}
                  className={`text-xs px-2.5 py-1 rounded-full font-semibold cursor-pointer border ${
                    v.is_active
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}
                >
                  {v.is_active ? 'В роботі' : 'Неактивне'}
                </button>
              </div>
              <div className="text-sm font-semibold text-slate-200">{v.model}</div>
              <div className="text-xs text-slate-400">
                Місткість: <span className="text-slate-200 font-bold">{v.total_seats} сид. / {v.total_standing} ст.</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
