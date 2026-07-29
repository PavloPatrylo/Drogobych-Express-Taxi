import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  Calendar as CalendarIcon,
  Plus,
  MapPin,
  Clock,
  Users,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  Pencil,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

import CreateTripModal from '../components/CreateTripModal';
import TripManifestModal from '../components/TripManifestModal';

export default function SchedulePage() {
  const [trips, setTrips] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedManifestTrip, setSelectedManifestTrip] = useState(null);
  const [manifestMode, setManifestMode] = useState(null);

  // Date Filtering State (Default: Today offset 0)
  const [dayOffset, setDayOffset] = useState(0); // 0 = Сьогодні за Київським часом
  const [customDate, setCustomDate] = useState(''); // Якщо обрано з календаря

  const [routeFilter, setRouteFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  const fetchTrips = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get('/trips');
      setTrips(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch trips:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTrips();
  }, []);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'BOARDING':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse';
      case 'ACTIVE':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'COMPLETED':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'CANCELLED':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'CLOSED':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const translateStatus = (status) => {
    switch (status) {
      case 'BOARDING': return 'Посадка';
      case 'ACTIVE': return 'В дорозі';
      case 'COMPLETED': return 'Завершено';
      case 'CANCELLED': return 'Скасовано';
      case 'SCHEDULED': return 'Заплановано';
      case 'CLOSED': return 'Закрито';
      default: return status;
    }
  };

  const getKyivDateString = (offsetDays = 0) => {
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    return d.toLocaleDateString('sv-SE', { timeZone: 'Europe/Kyiv' });
  };

  const getFormattedKyivDateLabel = (offsetDays = 0, custom = '') => {
    if (custom) {
      const parts = custom.split('-');
      if (parts.length === 3) {
        const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
        return d.toLocaleDateString('uk-UA', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
      }
      return custom;
    }
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    return d.toLocaleDateString('uk-UA', { timeZone: 'Europe/Kyiv', weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  };

  const selectedDateStr = customDate || getKyivDateString(dayOffset);

  // Filter logic
  const filteredTrips = trips.filter((trip) => {
    if (routeFilter !== 'all' && trip.route !== routeFilter) return false;
    if (statusFilter !== 'all' && trip.status !== statusFilter) return false;

    if (trip.date) {
      if (trip.date !== selectedDateStr) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <CalendarIcon className="text-yellow-400" size={28} />
            <span>Розклад рейсів</span>
          </h1>
          <p className="text-sm text-slate-400">
            Керування рейсами, маніфестами пасажирів та оперативними станами за Київським часом
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchTrips}
            disabled={isLoading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-400 hover:text-slate-200 transition-colors"
            title="Оновити список"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
          </button>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-yellow-500/10 transition-all text-sm cursor-pointer"
          >
            <Plus size={18} />
            <span>Створити рейс</span>
          </button>
        </div>
      </div>

      <CreateTripModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={fetchTrips}
      />

      {/* Filters & Date Navigator Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4">
        
        {/* Day Navigator Controls */}
        <div className="flex flex-wrap items-center gap-3">
          
          {/* Quick Day Switcher with Arrow Buttons */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => {
                setCustomDate('');
                setDayOffset((prev) => prev - 1);
              }}
              className="px-2 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 transition-all flex items-center gap-1 cursor-pointer"
              title="Попередній день"
            >
              <ChevronLeft size={14} />
            </button>

            <button
              onClick={() => {
                setCustomDate('');
                setDayOffset(-1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                !customDate && dayOffset === -1 ? 'bg-slate-800 text-yellow-400 shadow-sm font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Вчора
            </button>

            <button
              onClick={() => {
                setCustomDate('');
                setDayOffset(0);
              }}
              className={`px-4 py-1.5 rounded-lg text-xs transition-all cursor-pointer ${
                !customDate && dayOffset === 0 ? 'bg-yellow-400 text-slate-950 font-black shadow-md' : 'text-slate-400 hover:text-slate-200 font-semibold'
              }`}
            >
              Сьогодні
            </button>

            <button
              onClick={() => {
                setCustomDate('');
                setDayOffset(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                !customDate && dayOffset === 1 ? 'bg-slate-800 text-yellow-400 shadow-sm font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Завтра
            </button>

            <button
              onClick={() => {
                setCustomDate('');
                setDayOffset((prev) => prev + 1);
              }}
              className="px-2 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 transition-all flex items-center gap-1 cursor-pointer"
              title="Наступний день"
            >
              <ChevronRight size={14} />
            </button>
          </div>

          {/* Custom Date Selector Input */}
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
            <CalendarIcon size={14} className="text-yellow-400" />
            <input
              type="date"
              value={selectedDateStr}
              onChange={(e) => {
                setCustomDate(e.target.value);
              }}
              className="bg-transparent text-xs font-mono font-bold text-slate-200 outline-none cursor-pointer"
            />
          </div>

          {/* Current Date Label */}
          <span className="text-xs font-semibold text-yellow-400 bg-yellow-400/10 px-3 py-1 rounded-lg border border-yellow-400/20 capitalize hidden sm:inline-block">
            📅 {getFormattedKyivDateLabel(dayOffset, customDate)}
          </span>
        </div>

        {/* Route & Status Filters */}
        <div className="flex items-center gap-3">
          <select
            value={routeFilter}
            onChange={(e) => setRouteFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-medium text-slate-200 outline-none focus:border-yellow-400"
          >
            <option value="all">📍 Усі напрямки</option>
            <option value="drohobych-lviv">Дрогобич → Львів</option>
            <option value="lviv-drohobych">Львів → Дрогобич</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-medium text-slate-200 outline-none focus:border-yellow-400"
          >
            <option value="all">Усі статуси</option>
            <option value="SCHEDULED">Заплановано</option>
            <option value="BOARDING">Посадка</option>
            <option value="ACTIVE">В дорозі</option>
            <option value="COMPLETED">Завершено</option>
            <option value="CLOSED">Закрито</option>
            <option value="CANCELLED">Скасовано</option>
          </select>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
          <RefreshCw className="animate-spin text-yellow-400 mx-auto mb-3" size={32} />
          <p className="text-sm font-medium text-slate-300">Завантаження розкладу рейсів...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6 text-center text-red-400 space-y-3">
          <AlertCircle className="mx-auto" size={32} />
          <p className="font-semibold text-sm">Не вдалося завантажити розклад: {error}</p>
          <button
            onClick={fetchTrips}
            className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-xl text-xs font-bold transition-colors"
          >
            Спробувати знову
          </button>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && filteredTrips.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <CalendarIcon className="text-slate-600 mx-auto" size={40} />
          <h3 className="text-lg font-bold text-slate-200 font-display uppercase tracking-wide">
            На обрану дату немає рейсів ({selectedDateStr})
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Скористайтесь кнопками дня або календарем для вибору іншої дати, або створіть нові рейси.
          </p>
        </div>
      )}

      {/* Trip Cards List Grid */}
      {!isLoading && !error && filteredTrips.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredTrips.map((trip) => (
            <div
              key={trip.id}
              className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 space-y-4 transition-all duration-200 shadow-lg hover:shadow-xl group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-2xl font-bold font-mono text-yellow-400 flex items-center gap-2">
                    <Clock size={20} />
                    <span>{trip.departure_time || '00:00'}</span>
                  </div>
                  <div className="text-sm font-semibold text-slate-200 flex items-center gap-1 mt-1">
                    <MapPin size={14} className="text-slate-400" />
                    <span>{trip.route === 'drohobych-lviv' ? 'Дрогобич → Львів' : trip.route === 'lviv-drohobych' ? 'Львів → Дрогобич' : trip.route}</span>
                  </div>
                </div>
                <span className={`text-xs px-2.5 py-1 rounded-full border font-semibold ${getStatusBadge(trip.status)}`}>
                  {translateStatus(trip.status)}
                </span>
              </div>

              <div className="border-t border-b border-slate-800/80 py-3 space-y-1.5 text-xs text-slate-400">
                <div className="flex justify-between">
                  <span>Дата:</span>
                  <span className="text-slate-200 font-medium font-mono">{trip.date}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span>Водій:</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-200 font-medium">{trip.driver_name || `#${trip.driver_id}`}</span>
                    <button
                      onClick={() => {
                        setSelectedManifestTrip(trip);
                        setManifestMode('driver');
                      }}
                      className="w-5 h-5 rounded bg-red-500/20 hover:bg-red-500/40 text-red-400 border border-red-500/30 flex items-center justify-center cursor-pointer transition-transform hover:scale-110"
                      title="Редагувати водія у маніфесті"
                    >
                      <Pencil size={10} />
                    </button>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span>Транспорт:</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-200 font-medium">{trip.vehicle_model ? `${trip.vehicle_model} (${trip.vehicle_plate})` : `#${trip.vehicle_id}`}</span>
                    <button
                      onClick={() => {
                        setSelectedManifestTrip(trip);
                        setManifestMode('vehicle');
                      }}
                      className="w-5 h-5 rounded bg-red-500/20 hover:bg-red-500/40 text-red-400 border border-red-500/30 flex items-center justify-center cursor-pointer transition-transform hover:scale-110"
                      title="Редагувати транспорт у маніфесті"
                    >
                      <Pencil size={10} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Capacity indicators */}
              <div className="flex items-center justify-between text-xs pt-1">
                <div className="flex items-center gap-3">
                  <span className="text-slate-300 font-medium flex items-center gap-1">
                    <Users size={14} className="text-yellow-400" />
                    <span>{trip.seats_limit_snapshot} місць</span>
                  </span>
                  <span className="text-slate-400 font-medium">🧍 {trip.standing_limit_snapshot} ст.</span>
                </div>

                <button
                  onClick={() => {
                    setSelectedManifestTrip(trip);
                    setManifestMode(null);
                  }}
                  className="text-xs text-yellow-400 hover:text-yellow-300 font-bold flex items-center gap-1 group-hover:translate-x-1 transition-transform cursor-pointer"
                >
                  <span>Маніфест</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Trip Manifest Modal */}
      <TripManifestModal
        isOpen={!!selectedManifestTrip}
        onClose={() => {
          setSelectedManifestTrip(null);
          setManifestMode(null);
        }}
        trip={selectedManifestTrip}
        initialMode={manifestMode}
        onUpdate={() => {
          fetchTrips();
        }}
      />
    </div>
  );
}
