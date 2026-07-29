import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { X, Plus, Trash2, Calendar, Clock, Bus, UserCheck, Zap, AlertCircle, CheckCircle } from 'lucide-react';

const getKyivToday = () => new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Kyiv' });

export default function CreateTripModal({ isOpen, onClose, onSuccess }) {
  const [activeTab, setActiveTab] = useState('manual'); // 'manual' | 'template'

  // Common data
  const [drivers, setDrivers] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [isDataLoading, setIsDataLoading] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Manual Form State
  const [manualForm, setManualForm] = useState({
    date: getKyivToday(),
    route: 'drohobych-lviv',
    departure_time: '08:00',
    driver_id: '',
    vehicle_id: '',
  });

  // Template Form State
  const [templateDate, setTemplateDate] = useState(getKyivToday());
  const [templateRoute, setTemplateRoute] = useState('drohobych-lviv');
  const [draftTrips, setDraftTrips] = useState([]);
  const [newAdhocTime, setNewAdhocTime] = useState('12:00');

  const [locations, setLocations] = useState([]);

  useEffect(() => {
    if (isOpen) {
      loadDependencies();
    }
  }, [isOpen]);

  useEffect(() => {
    if (activeTab === 'template' && locations.length > 0) {
      handleLoadTemplates(templateRoute);
    }
  }, [templateRoute, activeTab, locations]);

  const loadDependencies = async () => {
    setIsDataLoading(true);
    try {
      const [staffData, vehiclesData, locationsData] = await Promise.all([
        api.get('/auth/staff').catch(() => []),
        api.get('/vehicles').catch(() => []),
        api.get('/locations').catch(() => []),
      ]);

      const driverList = (staffData || []).filter((s) => s.role === 'driver' || s.is_driver);
      const vehicleList = (vehiclesData || []).filter((v) => v.is_active);

      setDrivers(driverList);
      setVehicles(vehicleList);
      setLocations(locationsData || []);

      if (driverList.length > 0) {
        setManualForm((prev) => ({ ...prev, driver_id: driverList[0].id }));
      }
      if (vehicleList.length > 0) {
        setManualForm((prev) => ({ ...prev, vehicle_id: vehicleList[0].id }));
      }
    } catch (err) {
      console.error('Failed to load modal dependencies:', err);
    } finally {
      setIsDataLoading(false);
    }
  };

  const handleLoadTemplates = async (routeKey = templateRoute) => {
    setSubmitError(null);
    try {
      const templates = await api.get('/templates');
      const filtered = (templates || []).filter((t) => {
        const fromLoc = locations.find((l) => Number(l.id) === Number(t.from_location_id));
        const toLoc = locations.find((l) => Number(l.id) === Number(t.to_location_id));

        const fromName = fromLoc ? fromLoc.name.toLowerCase() : '';
        const toName = toLoc ? toLoc.name.toLowerCase() : '';

        if (routeKey === 'drohobych-lviv') {
          const isFromDrohobych = fromName.includes('drohobych') || fromName.includes('дрогобич');
          const isToLviv = toName.includes('lviv') || toName.includes('львів');
          return isFromDrohobych && isToLviv;
        } else if (routeKey === 'lviv-drohobych') {
          const isFromLviv = fromName.includes('lviv') || fromName.includes('львів');
          const isToDrohobych = toName.includes('drohobych') || toName.includes('дрогобич');
          return isFromLviv && isToDrohobych;
        }
        return true;
      });

      const formattedDrafts = filtered.map((t, idx) => ({
        id: `tpl-${t.id}-${idx}`,
        departure_time: t.departure_time,
        driver_id: drivers[0]?.id || '',
        vehicle_id: vehicles[0]?.id || '',
        selected: true,
        isAdhoc: false,
      }));

      setDraftTrips(formattedDrafts);
    } catch (err) {
      setSubmitError(`Не вдалося завантажити шаблони: ${err.message}`);
    }
  };

  const handleAddAdhocSlot = () => {
    if (!newAdhocTime) return;
    const newSlot = {
      id: `adhoc-${Date.now()}`,
      departure_time: newAdhocTime,
      driver_id: drivers[0]?.id || '',
      vehicle_id: vehicles[0]?.id || '',
      selected: true,
      isAdhoc: true,
    };
    setDraftTrips((prev) => [...prev, newSlot].sort((a, b) => a.departure_time.localeCompare(b.departure_time)));
  };

  const handleRemoveDraftSlot = (id) => {
    setDraftTrips((prev) => prev.filter((item) => item.id !== id));
  };

  const handleDraftChange = (id, field, value) => {
    setDraftTrips((prev) =>
      prev.map((item) => (item.id === id ? { ...item, [field]: value } : item))
    );
  };

  // Submit Manual Trip
  const handleManualSubmit = async (e) => {
    e.preventDefault();
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      if (!manualForm.driver_id || !manualForm.vehicle_id) {
        throw new Error('Обов\'язково виберіть водія та авто');
      }

      await api.post('/trips', {
        date: manualForm.date,
        route: manualForm.route,
        departure_time: manualForm.departure_time,
        driver_id: Number(manualForm.driver_id),
        vehicle_id: Number(manualForm.vehicle_id),
      });

      setSubmitSuccess(true);
      setTimeout(() => {
        setSubmitSuccess(false);
        onSuccess?.();
        onClose();
      }, 1200);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit Template Batch Trips
  const handleBatchSubmit = async (e) => {
    e.preventDefault();
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      const selectedTrips = draftTrips.filter((item) => item.selected);
      if (selectedTrips.length === 0) {
        throw new Error('Виберіть хоча б один рейс для створення');
      }

      const batchPayload = {
        trips: selectedTrips.map((item) => ({
          date: templateDate,
          route: templateRoute,
          departure_time: item.departure_time,
          driver_id: Number(item.driver_id),
          vehicle_id: Number(item.vehicle_id),
        })),
      };

      await api.post('/trips/batch', batchPayload);

      setSubmitSuccess(true);
      setTimeout(() => {
        setSubmitSuccess(false);
        onSuccess?.();
        onClose();
      }, 1200);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-3xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div>
            <h2 className="font-display text-2xl tracking-wide uppercase text-slate-100 flex items-center gap-2">
              <Plus className="text-yellow-400" size={24} />
              <span>Майстер створення рейсів</span>
            </h2>
            <p className="text-xs text-slate-400">
              Ціна квитка виставляється автоматично з глобальних тарифів системи
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-950/80 px-6">
          <button
            onClick={() => setActiveTab('manual')}
            className={`py-3 px-5 text-xs font-bold transition-all border-b-2 ${
              activeTab === 'manual'
                ? 'border-yellow-400 text-yellow-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Вручну (Одноразовий рейс)
          </button>
          <button
            onClick={() => {
              setActiveTab('template');
              if (draftTrips.length === 0) handleLoadTemplates();
            }}
            className={`py-3 px-5 text-xs font-bold transition-all border-b-2 ${
              activeTab === 'template'
                ? 'border-yellow-400 text-yellow-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            За шаблоном (Сітка рейсів)
          </button>
        </div>

        {/* Error / Success Notifications */}
        {submitError && (
          <div className="m-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-xs">
            <AlertCircle size={18} className="shrink-0" />
            <span>{submitError}</span>
          </div>
        )}

        {submitSuccess && (
          <div className="m-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-3 text-emerald-400 text-xs">
            <CheckCircle size={18} className="shrink-0" />
            <span>Рейс(и) успішно створено та збережено в БД!</span>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* TAB 1: MANUAL TRIP CREATION */}
          {activeTab === 'manual' && (
            <form onSubmit={handleManualSubmit} className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Дата рейсу
                  </label>
                  <input
                    type="date"
                    value={manualForm.date}
                    onChange={(e) => setManualForm({ ...manualForm, date: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Напрямок
                  </label>
                  <select
                    value={manualForm.route}
                    onChange={(e) => setManualForm({ ...manualForm, route: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none"
                  >
                    <option value="drohobych-lviv">Дрогобич → Львів</option>
                    <option value="lviv-drohobych">Львів → Дрогобич</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Час відправлення
                </label>
                <input
                  type="time"
                  value={manualForm.departure_time}
                  onChange={(e) => setManualForm({ ...manualForm, departure_time: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none font-mono"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Призначити Водія
                  </label>
                  <select
                    value={manualForm.driver_id}
                    onChange={(e) => setManualForm({ ...manualForm, driver_id: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none"
                    required
                  >
                    {drivers.length === 0 && <option value="">Немає доступних водіїв</option>}
                    {drivers.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.full_name || d.name || `Водій #${d.id}`} ({d.phone || ''})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Призначити Автобус
                  </label>
                  <select
                    value={manualForm.vehicle_id}
                    onChange={(e) => setManualForm({ ...manualForm, vehicle_id: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none"
                    required
                  >
                    {vehicles.length === 0 && <option value="">Немає доступних авто</option>}
                    {vehicles.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.plate_number || v.plate} — {v.model} ({v.total_seats} місць)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-5 py-2.5 rounded-xl border border-slate-800 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Скасувати
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-yellow-500/10 transition-all disabled:opacity-50"
                >
                  {isSubmitting ? 'Створення...' : 'Створити рейс'}
                </button>
              </div>
            </form>
          )}

          {/* TAB 2: TEMPLATE-BASED BATCH CREATION */}
          {activeTab === 'template' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end bg-slate-950/60 p-4 rounded-2xl border border-slate-800">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Дата розкладу
                  </label>
                  <input
                    type="date"
                    value={templateDate}
                    onChange={(e) => setTemplateDate(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl p-2.5 text-xs text-slate-200 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Напрямок
                  </label>
                  <select
                    value={templateRoute}
                    onChange={(e) => setTemplateRoute(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl p-2.5 text-xs text-slate-200 outline-none"
                  >
                    <option value="drohobych-lviv">Дрогобич → Львів</option>
                    <option value="lviv-drohobych">Львів → Дрогобич</option>
                  </select>
                </div>

                <button
                  type="button"
                  onClick={handleLoadTemplates}
                  className="w-full bg-slate-800 hover:bg-slate-700 text-yellow-400 border border-slate-700 font-bold p-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition-colors"
                >
                  <Zap size={16} />
                  <span>Завантажити шаблони</span>
                </button>
              </div>

              {/* Draft Time Slots Preview Table */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  <span>Сітка рейсів на вибрану дату ({draftTrips.length})</span>
                  <span>Призначення водія та авто</span>
                </div>

                {draftTrips.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 bg-slate-950/40 rounded-2xl border border-slate-800 text-xs">
                    Натисніть "Завантажити шаблони" для формування сітки
                  </div>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                    {draftTrips.map((item) => (
                      <div
                        key={item.id}
                        className={`flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-xl border transition-all ${
                          item.selected
                            ? 'bg-slate-950 border-slate-800'
                            : 'bg-slate-950/30 border-slate-900 opacity-50'
                        }`}
                      >
                        <div className="flex items-center gap-3 w-full sm:w-auto">
                          <input
                            type="checkbox"
                            checked={item.selected}
                            onChange={(e) => handleDraftChange(item.id, 'selected', e.target.checked)}
                            className="w-4 h-4 accent-yellow-400 rounded cursor-pointer"
                          />
                          <span className="font-mono font-bold text-sm text-yellow-400 min-w-[50px]">
                            {item.departure_time}
                          </span>
                          {item.isAdhoc && (
                            <span className="text-[10px] bg-amber-500/10 text-amber-400 px-1.5 py-0.5 rounded border border-amber-500/20 font-mono">
                              Тимчасовий
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2 w-full sm:w-auto">
                          <select
                            value={item.driver_id}
                            onChange={(e) => handleDraftChange(item.id, 'driver_id', e.target.value)}
                            className="bg-slate-900 border border-slate-800 text-xs rounded-lg p-2 text-slate-200 outline-none w-1/2 sm:w-40"
                          >
                            {drivers.map((d) => (
                              <option key={d.id} value={d.id}>
                                {d.full_name || d.name || `Водій #${d.id}`}
                              </option>
                            ))}
                          </select>

                          <select
                            value={item.vehicle_id}
                            onChange={(e) => handleDraftChange(item.id, 'vehicle_id', e.target.value)}
                            className="bg-slate-900 border border-slate-800 text-xs rounded-lg p-2 text-slate-200 outline-none w-1/2 sm:w-40"
                          >
                            {vehicles.map((v) => (
                              <option key={v.id} value={v.id}>
                                {v.plate_number || v.plate}
                              </option>
                            ))}
                          </select>

                          <button
                            type="button"
                            onClick={() => handleRemoveDraftSlot(item.id)}
                            className="p-2 text-slate-500 hover:text-red-400 rounded-lg hover:bg-red-500/10 transition-colors"
                            title="Видалити з розкладу на сьогодні"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Add temporary time slot row (Does NOT alter database schedule_templates!) */}
              <div className="flex items-center gap-3 pt-2 border-t border-slate-800">
                <input
                  type="time"
                  value={newAdhocTime}
                  onChange={(e) => setNewAdhocTime(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs font-mono text-slate-200 outline-none"
                />
                <button
                  type="button"
                  onClick={handleAddAdhocSlot}
                  className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold px-4 py-2 rounded-xl border border-slate-700 transition-colors flex items-center gap-1.5"
                >
                  <Plus size={14} />
                  <span>Додати тимчасовий рейс на цю дату</span>
                </button>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 flex justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-5 py-2.5 rounded-xl border border-slate-800 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Скасувати
                </button>
                <button
                  type="button"
                  onClick={handleBatchSubmit}
                  disabled={isSubmitting || draftTrips.filter((i) => i.selected).length === 0}
                  className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-yellow-500/10 transition-all disabled:opacity-50"
                >
                  {isSubmitting
                    ? 'Створення...'
                    : `Створити розклад (${draftTrips.filter((i) => i.selected).length} рейсів)`}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
