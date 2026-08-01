import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  Bus,
  Plus,
  RefreshCw,
  AlertCircle,
  Search,
  Pencil,
  Trash2,
  X,
  Users,
  CheckCircle2,
  XCircle,
  Armchair,
  UserCheck,
} from 'lucide-react';

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Search & Filter
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Modal State (Create / Edit)
  const [showModal, setShowModal] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(null); // null if creating, vehicle object if editing
  const [formData, setFormData] = useState({
    plate_number: '',
    model: '',
    total_seats: 18,
    total_standing: 0,
    is_active: true,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      alert(`Помилка зміни статусу: ${err.message}`);
    }
  };

  const handleOpenAddModal = () => {
    setEditingVehicle(null);
    setFormData({
      plate_number: '',
      model: '',
      total_seats: 18,
      total_standing: 0,
      is_active: true,
    });
    setShowModal(true);
  };

  const handleOpenEditModal = (vehicle) => {
    setEditingVehicle(vehicle);
    setFormData({
      plate_number: vehicle.plate_number || vehicle.plate || '',
      model: vehicle.model || '',
      total_seats: vehicle.total_seats ?? 18,
      total_standing: vehicle.total_standing ?? 0,
      is_active: vehicle.is_active ?? true,
    });
    setShowModal(true);
  };

  const handleDeleteVehicle = async (vehicle) => {
    const plate = vehicle.plate_number || vehicle.plate;
    if (!confirm(`⚠️ Ви дійсно бажаєте видалити автомобіль ${plate}?`)) {
      return;
    }
    try {
      await api.delete(`/vehicles/${vehicle.id}`);
      fetchVehicles();
    } catch (err) {
      alert(`Помилка видалення: ${err.message}`);
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!formData.plate_number.trim()) {
      alert('Будь ласка, вкажіть державний номерний знак авто');
      return;
    }
    if (!formData.model.trim()) {
      alert('Будь ласка, вкажіть марку та модель авто');
      return;
    }
    if (formData.total_seats <= 0) {
      alert('Кількість сидячих місць повинна бути більшою за 0');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        plate_number: formData.plate_number.trim().toUpperCase(),
        model: formData.model.trim(),
        total_seats: Number(formData.total_seats),
        total_standing: Number(formData.total_standing),
        is_active: Boolean(formData.is_active),
      };

      if (editingVehicle) {
        await api.put(`/vehicles/${editingVehicle.id}`, payload);
      } else {
        await api.post('/vehicles', payload);
      }
      setShowModal(false);
      fetchVehicles();
    } catch (err) {
      alert(`Помилка збереження даних: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredVehicles = vehicles.filter((v) => {
    const query = search.toLowerCase();
    const plate = (v.plate_number || v.plate || '').toLowerCase();
    const model = (v.model || '').toLowerCase();
    const matchesQuery = plate.includes(query) || model.includes(query);

    if (statusFilter !== 'all') {
      if (statusFilter === 'active' && !v.is_active) return false;
      if (statusFilter === 'inactive' && v.is_active) return false;
    }

    return matchesQuery;
  });

  return (
    <div className="space-y-6 w-full">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <Bus className="text-yellow-400" size={28} />
            <span>Управління автопарком</span>
          </h1>
          <p className="text-sm text-slate-400">
            Реєстр мікроавтобусів, місткості пасажиромісць та статуси готовності до рейсів
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={fetchVehicles}
            disabled={isLoading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
            title="Оновити список"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
          </button>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-semibold text-emerald-400 outline-none focus:border-yellow-400 cursor-pointer"
          >
            <option value="all">Усі авто</option>
            <option value="active">🟢 Тільки активні</option>
            <option value="inactive">🔴 Тільки неактивні</option>
          </select>

          {/* Search Input */}
          <div className="relative min-w-[240px]">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Пошук за номером чи моделлю..."
              className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl py-2 pl-10 pr-4 text-xs text-slate-100 placeholder-slate-500 outline-none transition-colors"
            />
          </div>

          {/* Add Vehicle Button */}
          <button
            onClick={handleOpenAddModal}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-yellow-500/10 text-xs uppercase tracking-wider transition-all cursor-pointer"
          >
            <Plus size={18} />
            <span>Додати авто</span>
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <RefreshCw className="animate-spin text-yellow-400" size={32} />
          <span>Завантаження автопарку з бази даних...</span>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
          <AlertCircle size={18} className="shrink-0" />
          <span>Помилка: {error}</span>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && filteredVehicles.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
          <Bus size={40} className="mx-auto mb-3 text-slate-600" />
          <p className="font-semibold text-slate-200">Автомобілів не знайдено</p>
          <p className="text-xs text-slate-500 mt-1">Змініть параметри пошуку або додайте перше авто у базу</p>
        </div>
      )}

      {/* Vehicles Grid Cards */}
      {!isLoading && !error && filteredVehicles.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredVehicles.map((v) => {
            const plate = v.plate_number || v.plate;
            return (
              <div
                key={v.id}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 space-y-4 shadow-xl transition-all relative group"
              >
                {/* Header: Plate & Status */}
                <div className="flex items-center justify-between">
                  <span className="font-mono text-base font-extrabold text-yellow-400 bg-slate-950 px-3.5 py-1.5 rounded-xl border border-slate-800 tracking-wider shadow-inner">
                    {plate}
                  </span>
                  <button
                    onClick={() => handleToggleStatus(v.id)}
                    className={`text-xs px-3 py-1 rounded-full font-bold cursor-pointer transition-all border ${
                      v.is_active
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30'
                        : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-emerald-500/10 hover:text-emerald-400'
                    }`}
                    title="Натисніть для зміни статусу"
                  >
                    {v.is_active ? '🟢 Активний' : '🔴 Неактивний'}
                  </button>
                </div>

                {/* Body: Model & Seats */}
                <div className="space-y-2">
                  <h3 className="font-bold text-slate-100 text-lg group-hover:text-yellow-400 transition-colors">
                    {v.model || 'Автомобіль'}
                  </h3>

                  <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                    <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center gap-2">
                      <Armchair size={16} className="text-yellow-400 shrink-0" />
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase">Сидячі:</span>
                        <span className="font-mono font-bold text-slate-200">{v.total_seats} місць</span>
                      </div>
                    </div>

                    <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center gap-2">
                      <Users size={16} className="text-sky-400 shrink-0" />
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase">Стоячі:</span>
                        <span className="font-mono font-bold text-slate-200">{v.total_standing ?? 0} місць</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Footer: Actions */}
                <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
                  <span className="text-[11px] font-mono text-slate-500">ID: #{v.id}</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleOpenEditModal(v)}
                      className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-yellow-400 transition-colors cursor-pointer"
                      title="Редагувати авто"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => handleDeleteVehicle(v)}
                      className="p-2 rounded-lg bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
                      title="Видалити авто"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CREATE / EDIT VEHICLE MODAL */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 font-bold text-slate-100 text-base">
                <Bus size={20} className="text-yellow-400" />
                <span>{editingVehicle ? 'Редагувати автомобіль' : 'Додати новий автомобіль'}</span>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className="space-y-4">
              {/* Plate Number */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Державний номерний знак *
                </label>
                <input
                  type="text"
                  value={formData.plate_number}
                  onChange={(e) => setFormData({ ...formData, plate_number: e.target.value })}
                  placeholder="BC 1234 AB"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs font-mono font-bold text-yellow-400 uppercase outline-none"
                  required
                />
              </div>

              {/* Model Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Марка та Модель *
                </label>
                <input
                  type="text"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  placeholder="Mercedes Sprinter 319"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-100 outline-none"
                  required
                />
              </div>

              {/* Seats & Standing */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Сидячих місць *
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={formData.total_seats}
                    onChange={(e) => setFormData({ ...formData, total_seats: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs font-mono text-slate-100 outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Стоячих місць
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={formData.total_standing}
                    onChange={(e) => setFormData({ ...formData, total_standing: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs font-mono text-slate-100 outline-none"
                  />
                </div>
              </div>

              {/* Status Select */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Статус у системі *
                </label>
                <select
                  value={formData.is_active ? 'active' : 'inactive'}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.value === 'active' })}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-100 font-semibold outline-none cursor-pointer"
                >
                  <option value="active">🟢 Активний (готов на рейс)</option>
                  <option value="inactive">🔴 Неактивний</option>
                </select>
              </div>

              {/* Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200 font-bold text-xs cursor-pointer"
                >
                  Скасувати
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-yellow-500/10 cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? 'Збереження...' : editingVehicle ? 'Зберегти зміни' : 'Створити автомобіль'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
