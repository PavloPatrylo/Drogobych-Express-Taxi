import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Users, Search, RefreshCw, AlertCircle, Star } from 'lucide-react';

export default function CrmPage() {
  const [passengers, setPassengers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  const fetchPassengers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get('/passengers');
      setPassengers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch passengers:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPassengers();
  }, []);

  const handleToggleBlock = async (user) => {
    try {
      const endpoint = user.is_active ? `/passengers/${user.id}/block` : `/passengers/${user.id}/unblock`;
      await api.post(endpoint);
      fetchPassengers();
    } catch (err) {
      alert(`Помилка зміни статусу: ${err.message}`);
    }
  };

  const filteredPassengers = passengers.filter((p) => {
    const query = search.toLowerCase();
    const name = (p.full_name || p.name || '').toLowerCase();
    const phone = (p.phone || '').toLowerCase();
    return name.includes(query) || phone.includes(query);
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <Users className="text-yellow-400" size={28} />
            <span>База клієнтів (CRM)</span>
          </h1>
          <p className="text-sm text-slate-400">
            Реальна база пасажирів з вашої бази даних PostgreSQL
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchPassengers}
            disabled={isLoading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-400 hover:text-slate-200 transition-colors"
            title="Оновити список"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
          </button>

          {/* Search Input */}
          <div className="relative min-w-[280px]">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Пошук за ім'ям або телефоном..."
              className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl py-2 pl-10 pr-4 text-xs text-slate-100 placeholder-slate-500 outline-none transition-colors"
            />
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <RefreshCw className="animate-spin text-yellow-400" size={32} />
          <span>Завантаження пасажирів з бази даних...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
          <AlertCircle size={18} className="shrink-0" />
          <span>Помилка: {error}</span>
        </div>
      )}

      {!isLoading && !error && filteredPassengers.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
          <Users size={40} className="mx-auto mb-3 text-slate-600" />
          <p className="font-semibold text-slate-200">Пасажирів не знайдено</p>
          <p className="text-xs text-slate-500 mt-1">База даних поки порожня або немає збігів за пошуком</p>
        </div>
      )}

      {/* Passengers Table */}
      {!isLoading && !error && filteredPassengers.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase font-semibold">
                <tr>
                  <th className="p-4">Клієнт</th>
                  <th className="p-4">Телефон</th>
                  <th className="p-4 text-center">Поїздок</th>
                  <th className="p-4 text-center">Пропущено</th>
                  <th className="p-4 text-center">Рейтинг довіри</th>
                  <th className="p-4 text-right">Статус</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredPassengers.map((p) => {
                  const displayName = p.full_name || p.name || 'Пасажир';
                  return (
                    <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="p-4 font-semibold text-slate-100 flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-yellow-400 text-xs">
                          {displayName[0]?.toUpperCase()}
                        </div>
                        <span>{displayName}</span>
                      </td>
                      <td className="p-4 font-mono text-slate-300">{p.phone || '—'}</td>
                      <td className="p-4 text-center font-bold text-slate-200">{p.total_trips || 0}</td>
                      <td className="p-4 text-center font-bold text-red-400">{p.total_noshows || 0}</td>
                      <td className="p-4 text-center">
                        <span className={`inline-flex items-center gap-1 font-mono font-bold px-2 py-0.5 rounded-full ${
                          (p.trust_score ?? 100) >= 80 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                        }`}>
                          <Star size={12} fill="currentColor" /> {p.trust_score ?? 100}%
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <button
                          onClick={() => handleToggleBlock(p)}
                          className={`px-3 py-1 rounded-lg border font-medium text-xs transition-colors ${
                            p.is_active
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30'
                              : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-emerald-500/10 hover:text-emerald-400'
                          }`}
                        >
                          {p.is_active ? 'Активний (Заблокувати)' : 'Заблокований (Розблокувати)'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
