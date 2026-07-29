import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { DollarSign, RefreshCw, AlertCircle, PieChart, ArrowUpRight } from 'lucide-react';

export default function FinancePage() {
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchFinanceSummary = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get('/finance/summary');
      setSummary(data);
    } catch (err) {
      console.error('Failed to fetch finance summary:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFinanceSummary();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <DollarSign className="text-yellow-400" size={28} />
            <span>Фінанси та Звіти</span>
          </h1>
          <p className="text-sm text-slate-400">
            Реальні фінансові показники та звітність з бази даних PostgreSQL
          </p>
        </div>

        <button
          onClick={fetchFinanceSummary}
          disabled={isLoading}
          className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-400 hover:text-slate-200 transition-colors"
          title="Оновити дані з БД"
        >
          <RefreshCw size={18} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
        </button>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <RefreshCw className="animate-spin text-yellow-400" size={32} />
          <span>Завантаження фінансового звіту з бази даних...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
          <AlertCircle size={18} className="shrink-0" />
          <span>Помилка: {error} (Доступно тільки користувачам з роллю Власник / Admin)</span>
        </div>
      )}

      {!isLoading && !error && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="text-xs text-slate-400 font-medium">Загальна выручка</div>
              <div className="text-2xl font-bold font-mono text-yellow-400">
                {summary?.total_revenue !== undefined ? `${summary.total_revenue} ₴` : '0 ₴'}
              </div>
              <div className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                <ArrowUpRight size={14} /> Реальний підрахунок з БД
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="text-xs text-slate-400 font-medium">Завершені рейси</div>
              <div className="text-2xl font-bold font-mono text-slate-100">
                {summary?.total_trips || summary?.trips_count || 0}
              </div>
              <div className="text-xs text-slate-500 font-medium">За вибраний період</div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="text-xs text-slate-400 font-medium">Кількість заброньованих квитків</div>
              <div className="text-2xl font-bold font-mono text-slate-100">
                {summary?.total_bookings || summary?.bookings_count || 0}
              </div>
              <div className="text-xs text-slate-500 font-medium">Пасажирів перевезено</div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="text-xs text-slate-400 font-medium">Касові здачі від водіїв</div>
              <div className="text-2xl font-bold font-mono text-emerald-400">
                {summary?.total_submitted !== undefined ? `${summary.total_submitted} ₴` : '0 ₴'}
              </div>
              <div className="text-xs text-emerald-400 font-medium">Здано в касу</div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center text-slate-400 text-sm py-10">
            <PieChart size={36} className="mx-auto mb-2 text-yellow-400/70" />
            <p className="font-semibold text-slate-200">Фінансовий модуль звітів</p>
            <p className="text-xs text-slate-500 mt-1">
              Управління глобальними тарифами та шаблонами винесено в окрему вкладку "Налаштування та Тарифи"
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
