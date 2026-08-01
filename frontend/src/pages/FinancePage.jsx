import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useWebSocket } from '../context/WebSocketContext';
import {
  DollarSign,
  RefreshCw,
  AlertCircle,
  Calendar,
  User,
  Phone,
  CheckCircle2,
  Clock,
  Handshake,
  TrendingUp,
  TrendingDown,
  CreditCard,
  Banknote,
  Search,
  MessageSquare,
  Bus,
  X,
  ShieldCheck,
  Check,
  PieChart,
  Users,
  Percent,
  Printer,
  Download,
  FileSpreadsheet,
  Layers,
} from 'lucide-react';

const getKyivToday = () => new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Kyiv' });

function RevenueTimelineChart({ chartData }) {
  if (!chartData || chartData.length === 0) return null;

  const maxRevenue = Math.max(...chartData.map((d) => d.revenue), 100);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 className="font-display text-xl uppercase tracking-wider text-slate-100 flex items-center gap-2">
            <TrendingUp size={22} className="text-yellow-400" />
            <span>Графік Динаміки Виторгу</span>
          </h3>
          <p className="text-xs text-slate-400">
            Візуальний виторг рейсів у розрізі часу за обраний період (по днях або годинах пік)
          </p>
        </div>
      </div>

      <div className="h-52 flex items-end justify-between gap-1.5 pt-8 pb-2 px-2 border-b border-slate-800">
        {chartData.map((item, idx) => {
          const heightPct = Math.max(6, Math.round((item.revenue / maxRevenue) * 100));
          return (
            <div
              key={idx}
              className="flex-1 flex flex-col items-center h-full justify-end group relative"
            >
              {/* Floating Tooltip */}
              <div className="absolute -top-14 z-30 hidden group-hover:flex flex-col items-center bg-slate-950 border border-slate-700 text-[11px] text-slate-200 px-3 py-1.5 rounded-xl shadow-2xl pointer-events-none whitespace-nowrap animate-fade-in">
                <span className="font-mono font-bold text-yellow-400 text-xs">{item.revenue} ₴</span>
                <span className="text-[10px] text-slate-400">
                  {item.trips} рейсів • {item.passengers} пас.
                </span>
              </div>

              {/* Bar */}
              <div
                style={{ height: `${heightPct}%` }}
                className={`w-full rounded-t-lg transition-all duration-300 ${
                  item.revenue > 0
                    ? 'bg-gradient-to-t from-amber-500/40 via-yellow-400/80 to-yellow-400 group-hover:from-amber-400 group-hover:to-yellow-300 shadow-lg shadow-yellow-500/10'
                    : 'bg-slate-800/40'
                }`}
              />

              {/* Label */}
              <span className="text-[10px] font-mono text-slate-400 mt-2 truncate max-w-[42px]">
                {item.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RouteProfitabilitySection({ analytics }) {
  if (!analytics) return null;

  const routes = analytics.routes_comparison || [];
  const topTrips = analytics.top_trips || [];
  const weakTrips = analytics.weak_trips || [];

  const totalRev = routes.reduce((sum, r) => sum + r.revenue, 0) || 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl uppercase tracking-wider text-slate-100 flex items-center gap-2">
          <Bus className="text-yellow-400" size={22} />
          <span>🛣️ Аналітика Напрямків та Годин Пік</span>
        </h2>
        <span className="text-xs text-slate-400 font-mono">Дохідність та заповнюваність рейсів</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. PORTION: ROUTE COMPARISON */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="font-display text-lg uppercase tracking-wider text-slate-100 flex items-center gap-2">
              <span>📍 Порівняння напрямків</span>
            </h3>
            <p className="text-xs text-slate-400">
              Виторг та пасажиропотік напрямків Дрогобич ⇄ Львів
            </p>
          </div>

          {routes.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500 bg-slate-950/40 rounded-xl border border-slate-800">
              Немає даних по напрямках за цей період
            </div>
          ) : (
            <div className="space-y-4">
              {routes.map((r, idx) => {
                const sharePct = Math.round((r.revenue / totalRev) * 100);
                return (
                  <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                    <div className="flex justify-between items-center text-sm font-bold">
                      <span className="text-slate-100">{r.route}</span>
                      <span className="font-mono text-yellow-400">{r.revenue} ₴ ({sharePct}%)</span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${sharePct}%` }}
                        className="h-full bg-gradient-to-r from-yellow-400 to-amber-500 rounded-full"
                      />
                    </div>

                    <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 font-medium pt-1 gap-2">
                      <span>👥 Пасажирів: <strong className="text-slate-200">{r.passengers}</strong></span>
                      <span>🚌 Рейсів: <strong className="text-slate-200">{r.trips}</strong></span>
                      <span>📊 Сер. Заповнюваність: <strong className="text-sky-400">{r.avg_occupancy_rate}%</strong></span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 2. PORTION: TOP PROFITABLE TRIPS */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="font-display text-lg uppercase tracking-wider text-slate-100 flex items-center gap-2">
              <span className="text-amber-400">🔥 ТОП найприбутковіших рейсів</span>
            </h3>
            <p className="text-xs text-slate-400">
              Найкращі години відправлення за валовим виторгом
            </p>
          </div>

          {topTrips.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500 bg-slate-950/40 rounded-xl border border-slate-800">
              Немає даних по рейсах за цей період
            </div>
          ) : (
            <div className="space-y-2.5">
              {topTrips.map((t, idx) => (
                <div
                  key={idx}
                  className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 flex items-center justify-between hover:border-yellow-400/40 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-lg bg-yellow-400/10 border border-yellow-400/30 font-mono font-bold text-yellow-400 text-xs flex items-center justify-center">
                      #{idx + 1}
                    </div>
                    <div>
                      <div className="font-bold text-slate-100 text-xs flex items-center gap-2">
                        <span className="font-mono text-yellow-400">{t.time}</span>
                        <span>{t.route}</span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-medium">
                        {t.driver_name} • {t.passengers} пас.
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="font-mono font-bold text-emerald-400 text-sm">+{t.revenue} ₴</div>
                    <div className="text-[10px] text-sky-400 font-semibold">{t.occupancy_pct}% заповн.</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 3. PORTION: WEAK TRIPS (<30% OCCUPANCY) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
        <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
          <div>
            <h3 className="font-display text-lg uppercase tracking-wider text-slate-100 flex items-center gap-2">
              <span className="text-red-400">⚠️ «Слабкі» рейси (Заповнюваність &lt; 30%)</span>
            </h3>
            <p className="text-xs text-slate-400">
              Рейси з низьким завантаженням, які варто скоригувати в розкладі або змінити авто
            </p>
          </div>
          <span className="bg-red-500/10 text-red-400 border border-red-500/20 text-xs px-2.5 py-1 rounded-full font-bold">
            {weakTrips.length} рейсів
          </span>
        </div>

        {weakTrips.length === 0 ? (
          <div className="p-6 text-center text-xs text-emerald-400 bg-emerald-500/10 rounded-xl border border-emerald-500/20 font-semibold">
            👌 Чудово! Усі рейси за обраний період мають заповнюваність понад 30%
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {weakTrips.map((t, idx) => (
              <div
                key={idx}
                className="bg-slate-950 p-4 rounded-xl border border-red-500/20 space-y-2 relative"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-bold text-slate-100 text-sm flex items-center gap-2">
                      <span className="font-mono text-red-400 font-bold">{t.time}</span>
                      <span>{t.route}</span>
                    </div>
                    <div className="text-xs text-slate-400">{t.driver_name} ({t.date})</div>
                  </div>
                  <span className="font-mono font-bold text-red-400 text-xs bg-red-500/10 px-2 py-0.5 rounded-md border border-red-500/30">
                    {t.occupancy_pct}%
                  </span>
                </div>

                <div className="text-xs text-slate-400 flex justify-between pt-1 border-t border-slate-800/60">
                  <span>Перевезено: <strong className="text-slate-200">{t.passengers} / {t.capacity} місць</strong></span>
                  <span>Виторг: <strong className="text-yellow-400">{t.revenue} ₴</strong></span>
                </div>

                <div className="text-[11px] text-amber-400/90 font-medium bg-amber-500/10 p-2 rounded-lg border border-amber-500/20">
                  💡 <strong>Рекомендація:</strong> Заповнюваність менше 30%. Розгляньте об'єднання або скасування цієї години в Конструкторі Розкладу.
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AccountingExportSection({ dateFrom, dateTo, dateStr }) {
  const handleExport = async (type) => {
    try {
      const token = api.getToken();
      if (!token) {
        alert('Необхідно авторизуватися в CRM');
        return;
      }

      const url = `/api/admin/finance/export/${type}?date_from=${dateFrom}&date_to=${dateTo}`;
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Помилка сервера HTTP ${response.status}`);
      }

      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `${type}_${dateFrom}_to_${dateTo}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      alert(`Помилка експорту звіту: ${err.message}`);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <h3 className="font-display text-xl uppercase tracking-wider text-slate-100 flex items-center gap-2">
            <Printer size={22} className="text-yellow-400" />
            <span>🖨️ Експорт Звітів для Бухгалтерії (Excel / PDF)</span>
          </h3>
          <p className="text-xs text-slate-400">
            Формування та вивантаження офіційних фінансових відомостей за {dateStr} у 1 клік
          </p>
        </div>

        <button
          onClick={() => window.print()}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs rounded-xl border border-slate-700 flex items-center gap-2 transition-all cursor-pointer shadow-md"
        >
          <Printer size={16} className="text-yellow-400" />
          <span>Друкувати / Зберегти в PDF</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Report 1: Drivers Cash */}
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 font-bold text-slate-100 text-sm">
              <FileSpreadsheet size={18} className="text-emerald-400" />
              <span>Звіт по касі та рейсів водіїв</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Підсумкова відомість кількості рейсів, зданої готівки, безготівки та відхилень по кожному водію.
            </p>
          </div>
          <button
            onClick={() => handleExport('drivers-csv')}
            className="w-full bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold text-xs py-2 rounded-xl flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <Download size={15} />
            <span>Завантажити Excel (CSV)</span>
          </button>
        </div>

        {/* Report 2: Detailed Trips Register */}
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 font-bold text-slate-100 text-sm">
              <FileSpreadsheet size={18} className="text-sky-400" />
              <span>Деталізована відомість рейсів</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Реєстр кожного рейсу, автобусів, пасажирів, посилок та касових підсумків.
            </p>
          </div>
          <button
            onClick={() => handleExport('trips-csv')}
            className="w-full bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/30 font-bold text-xs py-2 rounded-xl flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <Download size={15} />
            <span>Завантажити Excel (CSV)</span>
          </button>
        </div>

        {/* Report 3: Parcels & Cargo Register */}
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 font-bold text-slate-100 text-sm">
              <FileSpreadsheet size={18} className="text-amber-400" />
              <span>Звіт по посилках та вантажах</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Реєстр переданих посилок, відправників, вартості та статусу доставки.
            </p>
          </div>
          <button
            onClick={() => handleExport('parcels-csv')}
            className="w-full bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 font-bold text-xs py-2 rounded-xl flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <Download size={15} />
            <span>Завантажити Excel (CSV)</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function FinancialClosuresAuditHistory() {
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const res = await api.get('/finance/closures-history?limit=50');
      setHistory(res || []);
    } catch (err) {
      console.error('Failed to fetch closures history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <h3 className="font-display text-xl uppercase tracking-wider text-slate-100 flex items-center gap-2">
            <Clock size={22} className="text-yellow-400" />
            <span>📜 Історія та Аудит Фінансових Закриттів</span>
          </h3>
          <p className="text-xs text-slate-400">
            Хронологічний журнал усіх підтверджень каси водіїв та фінансових закриттів рейсів
          </p>
        </div>

        <button
          onClick={fetchHistory}
          disabled={isLoading}
          className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded-xl border border-slate-700 flex items-center gap-1.5 transition-all cursor-pointer"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
          <span>Оновити аудит</span>
        </button>
      </div>

      {history.length === 0 ? (
        <div className="p-8 text-center text-slate-500 bg-slate-950/40 rounded-2xl border border-slate-800 text-xs">
          Журнал аудиту закриттів порожній. Закриті рейси та підтвердження каси відображатимуться тут.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[11px] tracking-wider">
                <th className="py-3 px-3">Дата / Час проведення</th>
                <th className="py-3 px-3">Диспетчер / Касир (Хто прийняв)</th>
                <th className="py-3 px-3">Деталі фінансової операції</th>
                <th className="py-3 px-3 text-right">Статус запису</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {history.map((item) => (
                <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 px-3 whitespace-nowrap font-mono text-slate-300 text-xs">
                    {item.created_at}
                  </td>
                  <td className="py-3.5 px-3 whitespace-nowrap">
                    <div className="font-bold text-slate-100">{item.actor_name}</div>
                    <span className="text-[10px] font-mono text-yellow-400 bg-yellow-400/10 px-1.5 py-0.5 rounded border border-yellow-400/20">
                      {item.actor_role}
                    </span>
                  </td>
                  <td className="py-3.5 px-3 text-slate-300">
                    {item.message}
                  </td>
                  <td className="py-3.5 px-3 text-right whitespace-nowrap">
                    <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded-full text-[10px] font-bold">
                      <ShieldCheck size={12} /> Зафіксовано в системі
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

export default function FinancePage() {
  const today = getKyivToday();
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [activePreset, setActivePreset] = useState('today');

  // Sub-navigation contextual menu group
  const [activeGroupTab, setActiveGroupTab] = useState('reconciliation');

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Search and Driver Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [driverFilter, setDriverFilter] = useState('all');

  // Confirm Modal State
  const [selectedDriver, setSelectedDriver] = useState(null);
  const [detailDriver, setDetailDriver] = useState(null);
  const [confirmForm, setConfirmForm] = useState({
    received_cash: 0,
    received_card: 0,
    comment: '',
  });
  const [isSubmittingConfirm, setIsSubmittingConfirm] = useState(false);

  const fetchReconciliation = async (from = dateFrom, to = dateTo) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.get(`/finance/reconciliation?date_from=${from}&date_to=${to}`);
      setData(res);
    } catch (err) {
      console.error('Failed to fetch finance reconciliation:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const { lastEvent } = useWebSocket();

  useEffect(() => {
    if (lastEvent) {
      if (['CASH_CONFIRMED', 'BOOKING_MUTATED', 'TRIP_MUTATED'].includes(lastEvent.event)) {
        fetchReconciliation(dateFrom, dateTo);
      }
    }
  }, [lastEvent]);

  useEffect(() => {
    fetchReconciliation(dateFrom, dateTo);
  }, []);

  const setQuickRange = (preset) => {
    const now = new Date();
    const kyivDateStr = (d) => d.toLocaleDateString('sv-SE', { timeZone: 'Europe/Kyiv' });

    if (preset === 'today') {
      const t = kyivDateStr(now);
      setDateFrom(t);
      setDateTo(t);
      setActivePreset('today');
      fetchReconciliation(t, t);
    } else if (preset === 'yesterday') {
      const d = new Date(now);
      d.setDate(d.getDate() - 1);
      const y = kyivDateStr(d);
      setDateFrom(y);
      setDateTo(y);
      setActivePreset('yesterday');
      fetchReconciliation(y, y);
    } else if (preset === '7days') {
      const d = new Date(now);
      d.setDate(d.getDate() - 6);
      const from = kyivDateStr(d);
      const to = kyivDateStr(now);
      setDateFrom(from);
      setDateTo(to);
      setActivePreset('7days');
      fetchReconciliation(from, to);
    } else if (preset === 'month') {
      const d = new Date(now.getFullYear(), now.getMonth(), 1);
      const from = kyivDateStr(d);
      const to = kyivDateStr(now);
      setDateFrom(from);
      setDateTo(to);
      setActivePreset('month');
      fetchReconciliation(from, to);
    } else {
      setActivePreset('custom');
    }
    setShowDatePicker(false);
  };

  const handleCustomApply = () => {
    setActivePreset('custom');
    fetchReconciliation(dateFrom, dateTo);
    setShowDatePicker(false);
  };

  const handleOpenConfirmModal = (driver) => {
    setSelectedDriver(driver);
    setConfirmForm({
      received_cash: driver.submitted_cash ?? driver.expected_total,
      received_card: driver.submitted_card ?? 0,
      comment: '',
    });
  };

  const handleConfirmSubmit = async (e) => {
    e.preventDefault();
    if (!selectedDriver) return;

    setIsSubmittingConfirm(true);
    try {
      const payload = {
        driver_id: selectedDriver.driver_id,
        target_date: data?.raw_date || dateFrom,
        received_cash: Number(confirmForm.received_cash) || 0,
        received_card: Number(confirmForm.received_card) || 0,
        comment: confirmForm.comment.trim() || null,
      };

      const updated = await api.post('/finance/confirm-driver-cash', payload);
      setData(updated);
      setSelectedDriver(null);
    } catch (err) {
      alert(`Помилка підтвердження каси: ${err.message}`);
    } finally {
      setIsSubmittingConfirm(false);
    }
  };

  const filteredDrivers = (data?.drivers || []).filter((d) => {
    if (driverFilter !== 'all' && String(d.driver_id) !== String(driverFilter)) {
      return false;
    }
    const q = searchQuery.toLowerCase();
    return d.driver_name.toLowerCase().includes(q) || d.driver_phone.toLowerCase().includes(q);
  });

  const activeKpi = (() => {
    if (!data?.drivers) return data?.global || {};
    if (driverFilter === 'all') return data.global || {};
    const d = data.drivers.find((dr) => String(dr.driver_id) === String(driverFilter));
    if (!d) return data.global || {};
    return {
      expected_revenue: d.expected_total,
      submitted_cash: d.submitted_cash,
      submitted_card: d.submitted_card,
      discrepancy: d.discrepancy,
    };
  })();

  return (
    <div className="space-y-6 w-full">
      {/* Page Header & Control Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <DollarSign className="text-yellow-400" size={28} />
            <span>Фінанси та Звіти</span>
          </h1>
          <p className="text-sm text-slate-400">
            Зведена фінансова аналітика, дохідність напрямків, експорт та приймання каси водіїв
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Driver Selector Filter */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5">
            <User size={16} className="text-yellow-400" />
            <select
              value={driverFilter}
              onChange={(e) => setDriverFilter(e.target.value)}
              className="bg-transparent text-xs font-semibold text-slate-200 outline-none cursor-pointer"
            >
              <option value="all" className="bg-slate-900 text-slate-200">
                👨‍✈️ Усі водії ({data?.drivers?.length || 0})
              </option>
              {(data?.drivers || []).map((d) => (
                <option key={d.driver_id} value={d.driver_id} className="bg-slate-900 text-slate-200">
                  {d.driver_name} ({d.driver_phone})
                </option>
              ))}
            </select>
          </div>

          {/* Interactive Date Range Picker */}
          <div className="relative">
            <button
              onClick={() => setShowDatePicker(!showDatePicker)}
              className="flex items-center gap-2 bg-slate-900 border border-slate-800 hover:border-yellow-400/50 rounded-xl px-3.5 py-2 text-xs font-semibold text-slate-100 shadow-md transition-all cursor-pointer"
            >
              <Calendar size={16} className="text-yellow-400" />
              <span>
                {dateFrom === dateTo
                  ? `📅 ${dateFrom === today ? 'Сьогодні' : dateFrom}`
                  : `🗓️ ${dateFrom} — ${dateTo}`}
              </span>
            </button>

            {showDatePicker && (
              <div className="absolute right-0 top-12 z-50 w-80 bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-2xl space-y-4 animate-fade-in">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    🗓️ Вибір періоду звітності
                  </span>
                  <button onClick={() => setShowDatePicker(false)} className="text-slate-400 hover:text-slate-200 cursor-pointer">
                    <X size={16} />
                  </button>
                </div>

                {/* Quick Presets */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <button
                    onClick={() => setQuickRange('today')}
                    className={`p-2 rounded-xl border text-left font-bold transition-all cursor-pointer ${
                      activePreset === 'today'
                        ? 'bg-yellow-400/10 border-yellow-400 text-yellow-400'
                        : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    📅 Сьогодні
                  </button>
                  <button
                    onClick={() => setQuickRange('yesterday')}
                    className={`p-2 rounded-xl border text-left font-bold transition-all cursor-pointer ${
                      activePreset === 'yesterday'
                        ? 'bg-yellow-400/10 border-yellow-400 text-yellow-400'
                        : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    📅 Вчора
                  </button>
                  <button
                    onClick={() => setQuickRange('7days')}
                    className={`p-2 rounded-xl border text-left font-bold transition-all cursor-pointer ${
                      activePreset === '7days'
                        ? 'bg-yellow-400/10 border-yellow-400 text-yellow-400'
                        : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    🗓️ 7 Днів
                  </button>
                  <button
                    onClick={() => setQuickRange('month')}
                    className={`p-2 rounded-xl border text-left font-bold transition-all cursor-pointer ${
                      activePreset === 'month'
                        ? 'bg-yellow-400/10 border-yellow-400 text-yellow-400'
                        : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    🗓️ Цей місяць
                  </button>
                </div>

                {/* Interactive Custom Range Inputs */}
                <div className="space-y-3 pt-2 border-t border-slate-800">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase">
                    ⚙️ Довільний період (З ... По)
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <label className="block text-[10px] text-slate-500 mb-1">З дати:</label>
                      <input
                        type="date"
                        value={dateFrom}
                        onChange={(e) => {
                          setDateFrom(e.target.value);
                          setActivePreset('custom');
                        }}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-500 mb-1">По дату:</label>
                      <input
                        type="date"
                        value={dateTo}
                        onChange={(e) => {
                          setDateTo(e.target.value);
                          setActivePreset('custom');
                        }}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200 outline-none"
                      />
                    </div>
                  </div>

                  <button
                    onClick={handleCustomApply}
                    className="w-full bg-gradient-to-r from-yellow-400 to-amber-500 text-slate-950 font-bold py-2 rounded-xl text-xs uppercase tracking-wider shadow-md hover:from-yellow-300 hover:to-amber-400 transition-all cursor-pointer"
                  >
                    Застосувати період
                  </button>
                </div>
              </div>
            )}
          </div>

          <button
            onClick={() => fetchReconciliation(dateFrom, dateTo)}
            disabled={isLoading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
            title="Оновити дані"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
          </button>
        </div>
      </div>

      {/* CONTEXTUAL MENU GROUP NAVIGATION TABS */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-800 scrollbar-none">
        <button
          onClick={() => setActiveGroupTab('reconciliation')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all cursor-pointer whitespace-nowrap ${
            activeGroupTab === 'reconciliation'
              ? 'bg-gradient-to-r from-yellow-400 to-amber-500 text-slate-950 shadow-lg shadow-yellow-500/10'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800'
          }`}
        >
          <Handshake size={16} />
          <span>💵 Контроль та Приймання Каси Водіїв</span>
        </button>

        <button
          onClick={() => setActiveGroupTab('analytics')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all cursor-pointer whitespace-nowrap ${
            activeGroupTab === 'analytics'
              ? 'bg-gradient-to-r from-yellow-400 to-amber-500 text-slate-950 shadow-lg shadow-yellow-500/10'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800'
          }`}
        >
          <PieChart size={16} />
          <span>📊 Зведена Фінансова Аналітика & KPI</span>
        </button>

        <button
          onClick={() => setActiveGroupTab('routes')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all cursor-pointer whitespace-nowrap ${
            activeGroupTab === 'routes'
              ? 'bg-gradient-to-r from-yellow-400 to-amber-500 text-slate-950 shadow-lg shadow-yellow-500/10'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800'
          }`}
        >
          <Bus size={16} />
          <span>🛣️ Аналітика Напрямків та Годин Пік</span>
        </button>

        <button
          onClick={() => setActiveGroupTab('export')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all cursor-pointer whitespace-nowrap ${
            activeGroupTab === 'export'
              ? 'bg-gradient-to-r from-yellow-400 to-amber-500 text-slate-950 shadow-lg shadow-yellow-500/10'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800'
          }`}
        >
          <Printer size={16} />
          <span>🖨️ Експорт Звітів для Бухгалтерії</span>
        </button>

        <button
          onClick={() => setActiveGroupTab('audit')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all cursor-pointer whitespace-nowrap ${
            activeGroupTab === 'audit'
              ? 'bg-gradient-to-r from-yellow-400 to-amber-500 text-slate-950 shadow-lg shadow-yellow-500/10'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800'
          }`}
        >
          <Clock size={16} />
          <span>📜 Історія та Аудит Фінансових Закриттів</span>
        </button>

        <button
          onClick={() => setActiveGroupTab('all')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all cursor-pointer whitespace-nowrap ${
            activeGroupTab === 'all'
              ? 'bg-gradient-to-r from-yellow-400 to-amber-500 text-slate-950 shadow-lg shadow-yellow-500/10'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800'
          }`}
        >
          <Layers size={16} />
          <span>🌐 Усі розділи (Зводний вигляд)</span>
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <RefreshCw className="animate-spin text-yellow-400" size={32} />
          <span>Формування аналітики та розрахунку каси за {dateFrom === dateTo ? dateFrom : `${dateFrom} — ${dateTo}`}...</span>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
          <AlertCircle size={18} className="shrink-0" />
          <span>Помилка: {error} (Доступно тільки Диспетчерам та Адміністраторам)</span>
        </div>
      )}

      {!isLoading && !error && data && (
        <div className="space-y-8 animate-fade-in">
          {/* SECTION 1: DRIVER CASH RECONCILIATION */}
          {(activeGroupTab === 'reconciliation' || activeGroupTab === 'all') && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-xl uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <Handshake className="text-yellow-400" size={22} />
                  <span>💵 Контроль та Приймання Каси Водіїв</span>
                </h2>
                <span className="text-xs text-slate-400 font-mono">Здача грошей за період: {data.date}</span>
              </div>

              {/* CASH KPI CARDS */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-xl">
                  <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                    <span>Розрахункова каса</span>
                    <DollarSign size={16} className="text-yellow-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-yellow-400">
                    {activeKpi?.expected_revenue ?? 0} ₴
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    {driverFilter === 'all' ? 'Очікувана сума по всіх водіях' : 'Очікувана каса вибраного водія'}
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-xl">
                  <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                    <span>Прийнято Готівки</span>
                    <Banknote size={16} className="text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-emerald-400">
                    {activeKpi?.submitted_cash ?? 0} ₴
                  </div>
                  <div className="text-[11px] text-emerald-500 font-medium">
                    Фактично здана готівка в касу
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-xl">
                  <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                    <span>Оплачено на Картку</span>
                    <CreditCard size={16} className="text-sky-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-sky-400">
                    {activeKpi?.submitted_card ?? 0} ₴
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    Перераховано водіям на картку
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-xl">
                  <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                    <span>Сумарна Різниця</span>
                    <ShieldCheck size={16} className="text-amber-400" />
                  </div>
                  <div
                    className={`text-2xl font-bold font-mono ${
                      (activeKpi?.discrepancy ?? 0) < 0
                        ? 'text-red-400'
                        : (activeKpi?.discrepancy ?? 0) > 0
                        ? 'text-emerald-400'
                        : 'text-slate-100'
                    }`}
                  >
                    {activeKpi?.discrepancy > 0 ? `+${activeKpi.discrepancy}` : activeKpi?.discrepancy ?? 0} ₴
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    {(activeKpi?.discrepancy ?? 0) < 0
                      ? '🔴 Сумарна недостача по касі'
                      : (activeKpi?.discrepancy ?? 0) > 0
                      ? '🟢 Сумарна перездача'
                      : '⚪ Баланс повністю сходиться'}
                  </div>
                </div>
              </div>

              {/* DRIVER CASH RECONCILIATION TABLE */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                  <div>
                    <h3 className="font-display text-xl uppercase tracking-wider text-slate-100 flex items-center gap-2">
                      <Handshake size={22} className="text-yellow-400" />
                      <span>Зведена таблиця контролю та приймання каси водіїв ({data.drivers?.length || 0})</span>
                    </h3>
                    <p className="text-xs text-slate-400">
                      Здача готівки за період {data.date}. Підтверджуйте розрахунки у 1 клік
                    </p>
                  </div>

                  <div className="relative min-w-[220px]">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Пошук водія чи тел..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl pl-8 pr-3 py-2 text-xs text-slate-200 outline-none"
                    />
                  </div>
                </div>

                {filteredDrivers.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 bg-slate-950/40 rounded-2xl border border-slate-800 text-xs">
                    За період {data.date} рейсів у водіїв не знайдено
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[11px] tracking-wider">
                          <th className="py-3 px-3">Водій</th>
                          <th className="py-3 px-3">Рейси (Завершено)</th>
                          <th className="py-3 px-3">Розрахункова каса</th>
                          <th className="py-3 px-3">Готівка / Картка</th>
                          <th className="py-3 px-3">Всього Здано</th>
                          <th className="py-3 px-3">Різниця</th>
                          <th className="py-3 px-3">Статус зведення</th>
                          <th className="py-3 px-3 text-right">Дія</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-medium">
                        {filteredDrivers.map((d) => {
                          const isClosed = d.status === 'CLOSED';
                          const isPending = d.status === 'PENDING';

                          return (
                            <tr key={d.driver_id} className="hover:bg-slate-800/30 transition-colors">
                              {/* Driver Info */}
                              <td className="py-3.5 px-3">
                                <div
                                  onClick={() => setDetailDriver(d)}
                                  className="font-bold text-slate-100 text-sm hover:text-yellow-400 cursor-pointer flex items-center gap-1.5"
                                  title="Натисніть для перегляду деталізації по кожному рейсу"
                                >
                                  <span>{d.driver_name}</span>
                                  <span className="text-[10px] text-yellow-400/80 bg-yellow-400/10 px-1.5 py-0.5 rounded border border-yellow-400/20">
                                    🔍 Рейси ({d.trips?.length || 0})
                                  </span>
                                </div>
                                <div className="text-[11px] font-mono text-slate-400 flex items-center gap-2 mt-0.5">
                                  <span>{d.driver_phone}</span>
                                  {d.telegram_id && (
                                    <a
                                      href={`tg://user?id=${d.telegram_id}`}
                                      className="text-sky-400 hover:underline"
                                      title="Відкрити чат у Telegram"
                                    >
                                      Telegram
                                    </a>
                                  )}
                                </div>
                              </td>

                              {/* Trips count */}
                              <td className="py-3.5 px-3">
                                <div className="font-mono font-bold text-slate-200">
                                  {d.completed_trips} / {d.total_trips}
                                </div>
                                <div className="text-[10px] text-slate-500">
                                  {d.closed_trips === d.completed_trips && d.completed_trips > 0
                                    ? 'Всі закриті'
                                    : `${d.closed_trips} закритих`}
                                </div>
                              </td>

                              {/* Expected Total */}
                              <td className="py-3.5 px-3">
                                <span className="font-mono font-bold text-yellow-400 text-sm">
                                  {d.expected_total} ₴
                                </span>
                              </td>

                              {/* Cash / Card breakdown */}
                              <td className="py-3.5 px-3 space-y-0.5">
                                <div className="font-mono text-emerald-400">💵 {d.submitted_cash} ₴</div>
                                <div className="font-mono text-sky-400">💳 {d.submitted_card} ₴</div>
                              </td>

                              {/* Total Submitted */}
                              <td className="py-3.5 px-3">
                                <span className="font-mono font-bold text-slate-100 text-sm">
                                  {d.total_submitted} ₴
                                </span>
                              </td>

                              {/* Discrepancy */}
                              <td className="py-3.5 px-3">
                                {d.discrepancy < 0 ? (
                                  <span className="font-mono font-bold text-red-400 bg-red-500/10 px-2 py-1 rounded-lg border border-red-500/20">
                                    🔴 {d.discrepancy} ₴
                                  </span>
                                ) : d.discrepancy > 0 ? (
                                  <span className="font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-lg border border-emerald-500/20">
                                    🟢 +{d.discrepancy} ₴
                                  </span>
                                ) : (
                                  <span className="font-mono text-slate-400">⚪ 0 ₴</span>
                                )}
                              </td>

                              {/* Reconciliation Status */}
                              <td className="py-3.5 px-3">
                                {isClosed ? (
                                  <div className="space-y-0.5">
                                    <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded-full text-[10px] font-bold">
                                      <CheckCircle2 size={12} /> Здано касиру
                                    </span>
                                    {d.closed_by && (
                                      <div className="text-[10px] text-slate-500">Прийняв: {d.closed_by}</div>
                                    )}
                                  </div>
                                ) : isPending ? (
                                  <span className="inline-flex items-center gap-1 bg-amber-500/10 text-amber-400 border border-amber-500/30 px-2.5 py-1 rounded-full text-[10px] font-bold">
                                    <Clock size={12} /> Очікує здачі
                                  </span>
                                ) : (
                                  <span className="text-slate-500 text-[11px]">Немає закритих рейсів</span>
                                )}
                              </td>

                              {/* Action button */}
                              <td className="py-3.5 px-3 text-right space-x-1.5">
                                <button
                                  onClick={() => setDetailDriver(d)}
                                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-bold text-xs inline-flex items-center gap-1 transition-all cursor-pointer"
                                  title="Деталізація каси по кожному рейсу водія"
                                >
                                  <span>🔍 Деталі</span>
                                </button>

                                {d.completed_trips > 0 && (
                                  <button
                                    onClick={() => handleOpenConfirmModal(d)}
                                    className={`px-3 py-1.5 rounded-xl font-bold text-xs inline-flex items-center gap-1.5 transition-all cursor-pointer shadow-md ${
                                      isClosed
                                        ? 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                                        : 'bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950'
                                    }`}
                                  >
                                    <Handshake size={14} />
                                    <span>{isClosed ? 'Редагувати' : 'Прийняти касу'}</span>
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* SECTION 2: FINANCIAL ANALYTICS & BUSINESS KPI DASHBOARD */}
          {(activeGroupTab === 'analytics' || activeGroupTab === 'all') && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-xl uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <PieChart className="text-yellow-400" size={22} />
                  <span>📊 Зведена Фінансова Аналітика & KPI</span>
                </h2>
                <span className="text-xs text-slate-400 font-mono">Період: {data.date}</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Gross Revenue */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-xl">
                  <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                    <span>Загальний Валовий Виторг</span>
                    <DollarSign size={18} className="text-yellow-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-yellow-400">
                    {data.analytics?.gross_revenue ?? 0} ₴
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    Валовий виторг за квитками рейсів
                  </div>
                </div>

                {/* Avg Revenue Per Trip */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-xl">
                  <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                    <span>Середній виторг з 1 рейсу</span>
                    <Bus size={18} className="text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-emerald-400">
                    {data.analytics?.avg_revenue_per_trip ?? 0} ₴
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    Здійснено рейсів: {data.analytics?.completed_trips ?? 0}
                  </div>
                </div>

                {/* Avg Occupancy Rate */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-xl">
                  <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                    <span>Середня заповнюваність</span>
                    <Percent size={18} className="text-sky-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-sky-400">
                    {data.analytics?.avg_occupancy_rate ?? 0}%
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    Заповнення місць у машинах
                  </div>
                </div>

                {/* Passengers Count */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-xl">
                  <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                    <span>Перевезено Пасажирів</span>
                    <Users size={18} className="text-purple-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-purple-400">
                    {data.analytics?.total_passengers ?? 0}
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    Пасажиропотік за період
                  </div>
                </div>
              </div>

              {/* REVENUE TIMELINE CHART */}
              <RevenueTimelineChart chartData={data.analytics?.chart} />
            </div>
          )}

          {/* SECTION 3: ROUTE PROFITABILITY & PEAK HOURS ANALYTICS */}
          {(activeGroupTab === 'routes' || activeGroupTab === 'all') && (
            <RouteProfitabilitySection analytics={data.analytics} />
          )}

          {/* SECTION 4: ACCOUNTING REPORTS EXPORT (EXCEL / PDF) */}
          {(activeGroupTab === 'export' || activeGroupTab === 'all') && (
            <AccountingExportSection dateFrom={dateFrom} dateTo={dateTo} dateStr={data.date} />
          )}

          {/* SECTION 5: FINANCIAL CLOSURES AUDIT HISTORY */}
          {(activeGroupTab === 'audit' || activeGroupTab === 'all') && (
            <FinancialClosuresAuditHistory />
          )}
        </div>
      )}

      {/* CONFIRM DRIVER CASH MODAL */}
      {selectedDriver && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 font-bold text-slate-100 text-base">
                <Handshake size={20} className="text-yellow-400" />
                <span>Приймання каси у водія</span>
              </div>
              <button
                onClick={() => setSelectedDriver(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-100 text-sm">{selectedDriver.driver_name}</span>
                <span className="text-xs font-mono text-slate-400">{data?.date}</span>
              </div>
              <div className="text-xs text-slate-400 flex justify-between">
                <span>Розрахункова каса (Очікується):</span>
                <span className="font-mono font-bold text-yellow-400">{selectedDriver.expected_total} ₴</span>
              </div>
            </div>

            <form onSubmit={handleConfirmSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Фактично прийнято Готівкою (₴) *
                </label>
                <input
                  type="number"
                  step="any"
                  value={confirmForm.received_cash}
                  onChange={(e) => setConfirmForm({ ...confirmForm, received_cash: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs font-mono font-bold text-emerald-400 outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Отримано на Картку водія (₴)
                </label>
                <input
                  type="number"
                  step="any"
                  value={confirmForm.received_card}
                  onChange={(e) => setConfirmForm({ ...confirmForm, received_card: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs font-mono font-bold text-sky-400 outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Примітка касира / Диспетчера
                </label>
                <input
                  type="text"
                  placeholder="Наприклад: Готівка прийнята в повному обсязі"
                  value={confirmForm.comment}
                  onChange={(e) => setConfirmForm({ ...confirmForm, comment: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-100 outline-none"
                />
              </div>

              {/* Difference preview badge */}
              {(() => {
                const diff = (Number(confirmForm.received_cash) || 0) + (Number(confirmForm.received_card) || 0) - selectedDriver.expected_total;
                return (
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex justify-between items-center text-xs font-semibold">
                    <span className="text-slate-400">Розрахункове відхилення:</span>
                    <span
                      className={`font-mono font-bold ${
                        diff < 0 ? 'text-red-400' : diff > 0 ? 'text-emerald-400' : 'text-slate-200'
                      }`}
                    >
                      {diff < 0 ? `🔴 Недостача: ${diff} ₴` : diff > 0 ? `🟢 Перездача: +${diff} ₴` : '⚪ 0 ₴ (Внуль)'}
                    </span>
                  </div>
                );
              })()}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setSelectedDriver(null)}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200 font-bold text-xs cursor-pointer"
                >
                  Скасувати
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingConfirm}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-yellow-500/10 cursor-pointer disabled:opacity-50 flex items-center gap-2"
                >
                  <Handshake size={16} />
                  <span>{isSubmittingConfirm ? 'Підтвердження...' : 'Підтвердити приймання каси'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DRIVER TRIPS DETAIL MODAL */}
      {detailDriver && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="font-display text-lg uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <Bus size={20} className="text-yellow-400" />
                  <span>🔍 Деталізація каси по рейсах: {detailDriver.driver_name}</span>
                </h3>
                <p className="text-xs text-slate-400">{detailDriver.driver_phone} • Звітний період: {data?.date}</p>
              </div>
              <button
                onClick={() => setDetailDriver(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Summary KPI Strip */}
            <div className="grid grid-cols-3 gap-3 bg-slate-950 p-4 rounded-2xl border border-slate-800 text-xs">
              <div>
                <div className="text-slate-400 font-medium">Розрахункова каса:</div>
                <div className="font-mono font-bold text-yellow-400 text-sm">{detailDriver.expected_total} ₴</div>
              </div>
              <div>
                <div className="text-slate-400 font-medium">Фактично здано:</div>
                <div className="font-mono font-bold text-emerald-400 text-sm">{detailDriver.total_submitted} ₴</div>
              </div>
              <div>
                <div className="text-slate-400 font-medium">Сумарне відхилення:</div>
                <div className={`font-mono font-bold text-sm ${detailDriver.discrepancy < 0 ? 'text-red-400' : detailDriver.discrepancy > 0 ? 'text-emerald-400' : 'text-slate-200'}`}>
                  {detailDriver.discrepancy < 0 ? `🔴 ${detailDriver.discrepancy} ₴` : detailDriver.discrepancy > 0 ? `🟢 +${detailDriver.discrepancy} ₴` : '⚪ 0 ₴'}
                </div>
              </div>
            </div>

            {/* Per-trip breakdown table */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase text-slate-300 tracking-wider">
                📋 Перелік закритих / завершених рейсів ({detailDriver.trips?.length || 0}):
              </h4>

              {(!detailDriver.trips || detailDriver.trips.length === 0) ? (
                <div className="p-4 text-center text-xs text-slate-500 bg-slate-950 rounded-xl border border-slate-800">
                  Завершених рейсів за цей період не знайдено
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px] tracking-wider bg-slate-950">
                        <th className="py-2.5 px-3">Час / Маршрут</th>
                        <th className="py-2.5 px-3">Статус</th>
                        <th className="py-2.5 px-3">Очікувано</th>
                        <th className="py-2.5 px-3">Здано</th>
                        <th className="py-2.5 px-3 text-right">Різниця / Недостача</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-medium">
                      {detailDriver.trips.map((t, idx) => {
                        const tSubmitted = (t.submitted_cash || 0) + (t.submitted_card || 0);
                        const tDiff = t.discrepancy !== undefined ? t.discrepancy : (tSubmitted - t.expected_revenue);

                        return (
                          <tr key={idx} className="hover:bg-slate-800/30">
                            <td className="py-3 px-3">
                              <div className="font-bold text-slate-100 flex items-center gap-1.5">
                                <span className="font-mono text-yellow-400">{t.time}</span>
                                <span>{t.route}</span>
                              </div>
                              <div className="text-[10px] text-slate-500">{t.date}</div>
                            </td>
                            <td className="py-3 px-3">
                              {t.status === 'CLOSED' ? (
                                <span className="bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">
                                  🔒 Закрито
                                </span>
                              ) : (
                                <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">
                                  ✅ Завершено
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-3 font-mono font-bold text-yellow-400">
                              {t.expected_revenue} ₴
                            </td>
                            <td className="py-3 px-3 font-mono text-slate-200">
                              <div>💵 {t.submitted_cash || 0} ₴</div>
                              {t.submitted_card > 0 && <div className="text-sky-400 text-[10px]">💳 {t.submitted_card} ₴</div>}
                            </td>
                            <td className="py-3 px-3 text-right">
                              {tDiff < 0 ? (
                                <span className="font-mono font-bold text-red-400 bg-red-500/10 px-2 py-1 rounded-md border border-red-500/20">
                                  🔴 {tDiff} ₴ (Недостача)
                                </span>
                              ) : tDiff > 0 ? (
                                <span className="font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-md border border-emerald-500/20">
                                  🟢 +{tDiff} ₴ (Перездача)
                                </span>
                              ) : (
                                <span className="font-mono text-slate-400">⚪ 0 ₴</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                onClick={() => setDetailDriver(null)}
                className="px-4 py-2.5 rounded-xl bg-slate-800 text-slate-300 font-bold text-xs cursor-pointer hover:bg-slate-700 transition-colors"
              >
                Закрити
              </button>
              <button
                onClick={() => {
                  const dr = detailDriver;
                  setDetailDriver(null);
                  handleOpenConfirmModal(dr);
                }}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-md cursor-pointer flex items-center gap-2"
              >
                <Handshake size={16} />
                <span>Прийняти касу у цього водія</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
