import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Settings, Save, CheckCircle, Plus, Trash2, RefreshCw, AlertCircle, ShieldCheck, MapPin, Filter } from 'lucide-react';

export default function SettingsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Tariffs State
  const [tariffs, setTariffs] = useState({
    price_seated: 120,
    price_standing: 80,
    price_parcel: 50,
  });
  const [isSavingTariffs, setIsSavingTariffs] = useState(false);
  const [tariffSuccess, setTariffSuccess] = useState(false);

  // Locations & Templates State
  const [locations, setLocations] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [newTime, setNewTime] = useState('08:00');
  const [newFromLoc, setNewFromLoc] = useState('');
  const [newToLoc, setNewToLoc] = useState('');
  const [newDayType, setNewDayType] = useState('weekday');
  const [templateSuccess, setTemplateSuccess] = useState(false);

  // Filter State for Templates list
  const [filterDirection, setFilterDirection] = useState('all'); // 'all' | 'drohobych-lviv' | 'lviv-drohobych'
  const [filterDayType, setFilterDayType] = useState('weekday'); // 'all' | 'weekday' | 'saturday' | 'sunday'

  const handleDayTypeChange = (val) => {
    setNewDayType(val);
    setFilterDayType(val);
  };

  const handleFilterDayTypeChange = (val) => {
    setFilterDayType(val);
    if (val !== 'all') {
      setNewDayType(val);
    }
  };

  const fetchSettingsAndTemplates = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [configData, templatesData, locationsData] = await Promise.all([
        api.get('/system-config'),
        api.get('/templates'),
        api.get('/locations').catch(() => []),
      ]);

      if (configData) {
        setTariffs({
          price_seated: configData.price_seated,
          price_standing: configData.price_standing,
          price_parcel: configData.price_parcel,
        });
      }
      if (Array.isArray(templatesData)) {
        setTemplates(templatesData);
      }
      if (Array.isArray(locationsData) && locationsData.length > 0) {
        setLocations(locationsData);
        const drohobych = locationsData.find((l) => l.name.toLowerCase().includes('drohobych') || l.name.toLowerCase().includes('дрогобич'));
        const lviv = locationsData.find((l) => l.name.toLowerCase().includes('lviv') || l.name.toLowerCase().includes('львів'));

        setNewFromLoc((prev) => {
          if (prev) return prev;
          return drohobych ? drohobych.id : locationsData[0].id;
        });

        setNewToLoc((prev) => {
          if (prev) return prev;
          return lviv ? lviv.id : (locationsData[1]?.id || locationsData[0].id);
        });
      }
    } catch (err) {
      console.error('Failed to fetch settings/templates:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettingsAndTemplates();
  }, []);

  const handleFromLocationChange = (fromId) => {
    setNewFromLoc(fromId);
    // Auto pick different opposite location for to_location
    const opposite = locations.find((l) => Number(l.id) !== Number(fromId));
    if (opposite) {
      setNewToLoc(opposite.id);
    }
  };

  const handleSaveTariffs = async (e) => {
    e.preventDefault();
    setIsSavingTariffs(true);
    try {
      await api.put('/system-config', {
        price_seated: Number(tariffs.price_seated),
        price_standing: Number(tariffs.price_standing),
        price_parcel: Number(tariffs.price_parcel),
      });
      setTariffSuccess(true);
      setTimeout(() => setTariffSuccess(false), 2500);
    } catch (err) {
      alert(`Помилка збереження тарифів: ${err.message}`);
    } finally {
      setIsSavingTariffs(false);
    }
  };

  const handleAddTemplate = async (e) => {
    e.preventDefault();
    if (!newTime || !newFromLoc || !newToLoc) {
      alert('Будь ласка, виберіть пункт відправлення, пункт прибуття та час');
      return;
    }
    if (Number(newFromLoc) === Number(newToLoc)) {
      alert('Пункт відправлення та пункт прибуття не можуть бути однаковими!');
      return;
    }

    try {
      await api.post('/templates', {
        day_type: newDayType,
        from_location_id: Number(newFromLoc),
        to_location_id: Number(newToLoc),
        departure_time: newTime,
      });
      setTemplateSuccess(true);
      setTimeout(() => setTemplateSuccess(false), 2500);
      fetchSettingsAndTemplates();
    } catch (err) {
      alert(`Помилка створення шаблону: ${err.message}`);
    }
  };

  const handleDeleteTemplate = async (id) => {
    if (!confirm('Видалити цей час із шаблонів?')) return;
    try {
      await api.delete(`/templates/${id}`);
      fetchSettingsAndTemplates();
    } catch (err) {
      alert(`Помилка видалення: ${err.message}`);
    }
  };

  const getLocationName = (id) => {
    const loc = locations.find((l) => Number(l.id) === Number(id));
    return loc ? loc.name : `Локація #${id}`;
  };

  // Filter templates list directly by selected day type and departure location
  const filteredTemplates = templates.filter((t) => {
    const matchDay = t.day_type === newDayType;
    const matchFrom = !newFromLoc || Number(t.from_location_id) === Number(newFromLoc);
    return matchDay && matchFrom;
  });

  return (
    <div className="space-y-8 w-full">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <Settings className="text-yellow-400" size={28} />
            <span>Налаштування Тарифів та Шаблонів</span>
          </h1>
          <p className="text-sm text-slate-400">
            Окремий модуль Адміністратора у реальній БД PostgreSQL
          </p>
        </div>

        <button
          onClick={fetchSettingsAndTemplates}
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
          <span>Завантаження налаштувань з бази даних...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
          <AlertCircle size={18} className="shrink-0" />
          <span>Помилка: {error} (Доступно тільки Адміністратору/Власнику)</span>
        </div>
      )}

      {!isLoading && !error && (
        <>
          {/* CARD 1: GLOBAL SYSTEM TARIFFS */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-yellow-400/10 text-yellow-400 border border-yellow-400/20">
                  <ShieldCheck size={20} />
                </div>
                <div>
                  <h2 className="font-display text-xl uppercase tracking-wider text-slate-100">
                    Єдині Тарифи Системи (База Даних PostgreSQL)
                  </h2>
                  <p className="text-xs text-slate-400">
                    Визначають ціну для нових рейсів. Минулі рейси зберігають свій історичний тариф.
                  </p>
                </div>
              </div>

              {tariffSuccess && (
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                  <CheckCircle size={16} /> Збережено у БД!
                </div>
              )}
            </div>

            <form onSubmit={handleSaveTariffs} className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Сидяче місце (₴)
                </label>
                <input
                  type="number"
                  value={tariffs.price_seated}
                  onChange={(e) => setTariffs({ ...tariffs, price_seated: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 font-mono text-sm font-bold text-yellow-400 outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Стояче місце (₴)
                </label>
                <input
                  type="number"
                  value={tariffs.price_standing}
                  onChange={(e) => setTariffs({ ...tariffs, price_standing: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 font-mono text-sm font-bold text-slate-200 outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Коробка / Посилка (₴)
                </label>
                <input
                  type="number"
                  value={tariffs.price_parcel}
                  onChange={(e) => setTariffs({ ...tariffs, price_parcel: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 font-mono text-sm font-bold text-emerald-400 outline-none"
                  required
                />
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isSavingTariffs}
                  className="w-full bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold p-3 rounded-xl shadow-lg shadow-yellow-500/10 text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                >
                  <Save size={16} />
                  <span>{isSavingTariffs ? 'Збереження...' : 'Зберегти нові тарифи'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* CARD 2: SCHEDULE TEMPLATES MANAGER */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
              <div>
                <h2 className="font-display text-xl uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <MapPin className="text-yellow-400" size={22} />
                  <span>Конструктор Еталонних Шаблонів Розкладу</span>
                </h2>
                <p className="text-xs text-slate-400">
                  Додавайте відправлення за напрямками та днями тижня (без цін і без водіїв)
                </p>
              </div>

              {templateSuccess && (
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                  <CheckCircle size={16} /> Шаблон збережено в БД!
                </div>
              )}
            </div>

            {/* Form to Save New Template */}
            <form onSubmit={handleAddTemplate} className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end bg-slate-950/80 p-5 rounded-2xl border border-slate-800">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Тип дня
                </label>
                <select
                  value={newDayType}
                  onChange={(e) => handleDayTypeChange(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none font-medium cursor-pointer"
                >
                  <option value="weekday">Будній день</option>
                  <option value="saturday">Субота</option>
                  <option value="sunday">Неділя</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Пункт відправлення
                </label>
                <select
                  value={newFromLoc}
                  onChange={(e) => handleFromLocationChange(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none font-medium"
                  required
                >
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Пункт прибуття
                </label>
                <select
                  value={newToLoc}
                  onChange={(e) => setNewToLoc(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none font-medium"
                  required
                >
                  {locations
                    .filter((loc) => Number(loc.id) !== Number(newFromLoc))
                    .map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.name}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Час відправлення
                </label>
                <input
                  type="time"
                  value={newTime}
                  onChange={(e) => setNewTime(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs font-mono text-slate-200 outline-none"
                  required
                />
              </div>

              <div className="sm:col-span-4 flex justify-end">
                <button
                  type="submit"
                  className="bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold px-6 py-3 rounded-xl shadow-lg shadow-yellow-500/10 text-xs flex items-center gap-2 transition-all cursor-pointer"
                >
                  <Plus size={16} />
                  <span>Зберегти новий шаблон розкладу</span>
                </button>
              </div>
            </form>

            {/* Templates Grid in Database */}
            {filteredTemplates.length === 0 ? (
              <div className="p-8 text-center bg-slate-950/60 rounded-2xl border border-slate-800 space-y-2">
                <p className="font-bold text-slate-200 text-sm">
                  На {newDayType === 'weekday' ? 'Будній день' : newDayType === 'saturday' ? 'Суботу' : 'Неділю'}{newFromLoc ? ` (${getLocationName(newFromLoc)})` : ''} шаблону ще не створено 📭
                </p>
                <p className="text-xs text-slate-400">
                  Заповніть форму вище та натисніть «Зберегти новий шаблон розкладу», щоб додати перші рейси для цього напрямку.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Шаблони у базі даних ({filteredTemplates.length}):
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {filteredTemplates.map((t) => (
                    <div
                      key={t.id}
                      className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 flex items-center justify-between group hover:border-slate-700 transition-colors"
                    >
                      <div>
                        <div className="font-mono font-bold text-base text-yellow-400">{t.departure_time}</div>
                        <div className="text-[11px] text-slate-400 font-medium">
                          {getLocationName(t.from_location_id)} → {getLocationName(t.to_location_id)}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono capitalize">
                          {t.day_type === 'weekday' ? 'Будній' : t.day_type === 'saturday' ? 'Субота' : 'Неділя'}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleDeleteTemplate(t.id)}
                        className="p-1.5 text-slate-500 hover:text-red-400 rounded-lg hover:bg-red-500/10 transition-all cursor-pointer"
                        title="Видалити шаблон з БД"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
