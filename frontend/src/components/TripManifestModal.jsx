import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useWebSocket } from '../context/WebSocketContext';
import {
  X,
  Calendar,
  Clock,
  Bus,
  User,
  Phone,
  DollarSign,
  Users,
  MapPin,
  ArrowRight,
  ShieldCheck,
  CheckCircle,
  AlertCircle,
  Pencil,
  Check,
  Plus,
  Package,
  Instagram,
  Smartphone,
  UserCheck,
  UserX,
  MessageSquare,
  RefreshCw,
  Search,
  CreditCard,
  Lock,
} from 'lucide-react';

export default function TripManifestModal({ isOpen, onClose, trip: initialTrip, initialMode = null, onUpdate }) {
  const [currentTrip, setCurrentTrip] = useState(initialTrip);
  const [manifestData, setManifestData] = useState(null);
  const [isLoadingManifest, setIsLoadingManifest] = useState(true);
  const [manifestError, setManifestError] = useState(null);

  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  // Edit states for Vehicle and Driver
  const [isEditingVehicle, setIsEditingVehicle] = useState(false);
  const [isEditingDriver, setIsEditingDriver] = useState(false);

  const [availableVehicles, setAvailableVehicles] = useState([]);
  const [availableDrivers, setAvailableDrivers] = useState([]);

  const [selectedVehicleId, setSelectedVehicleId] = useState('');
  const [selectedDriverId, setSelectedDriverId] = useState('');

  const [isSavingVehicle, setIsSavingVehicle] = useState(false);
  const [isSavingDriver, setIsSavingDriver] = useState(false);

  // Edit states for Prices
  const [isEditingPrices, setIsEditingPrices] = useState(false);
  const [priceForm, setPriceForm] = useState({
    price_seated: '',
    price_standing: '',
    price_parcel: '',
  });
  const [isSavingPrices, setIsSavingPrices] = useState(false);

  // Financial Closure Modal State
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closeForm, setCloseForm] = useState({
    submitted_cash: '',
    submitted_card: '',
    comment: '',
  });
  const [isClosingTrip, setIsClosingTrip] = useState(false);

  // Quick Add Booking Form State
  const [showAddForm, setShowAddForm] = useState(false);
  const [newBooking, setNewBooking] = useState({
    booking_type: 'SEATED',
    source: 'PHONE',
    phone: '',
    full_name: '',
    seats: 1,
    comment: '',
  });
  const [isAddingBooking, setIsAddingBooking] = useState(false);

  // Filter passengers in manifest table
  const [searchQuery, setSearchQuery] = useState('');

  const fetchManifest = async (tripId) => {
    setIsLoadingManifest(true);
    setManifestError(null);
    try {
      const data = await api.get(`/trips/${tripId}/manifest`);
      setManifestData(data);
      if (data.trip) {
        setCurrentTrip(data.trip);
      }
    } catch (err) {
      console.error('Failed to fetch manifest:', err);
      setManifestError(err.message);
    } finally {
      setIsLoadingManifest(false);
    }
  };

  const { lastEvent } = useWebSocket();

  useEffect(() => {
    if (isOpen && currentTrip && lastEvent) {
      if (['BOOKING_MUTATED', 'TRIP_MUTATED'].includes(lastEvent.event)) {
        fetchManifest(currentTrip.id);
      }
    }
  }, [lastEvent, isOpen]);

  useEffect(() => {
    if (isOpen && initialTrip) {
      setCurrentTrip(initialTrip);
      setSelectedVehicleId(initialTrip.vehicle_id);
      setSelectedDriverId(initialTrip.driver_id);
      setIsEditingVehicle(initialMode === 'vehicle');
      setIsEditingDriver(initialMode === 'driver');
      fetchManifest(initialTrip.id);
      loadOptions();
    }
  }, [isOpen, initialTrip, initialMode]);

  const loadOptions = async () => {
    try {
      const [vehiclesData, staffData] = await Promise.all([
        api.get('/vehicles').catch(() => []),
        api.get('/auth/staff').catch(() => []),
      ]);
      setAvailableVehicles(vehiclesData || []);
      const driverList = (staffData || []).filter((s) => s.role === 'driver' || s.is_driver);
      setAvailableDrivers(driverList);
    } catch (err) {
      console.error('Failed to load edit options:', err);
    }
  };

  if (!isOpen || !currentTrip) return null;

  const handleSaveVehicle = async () => {
    if (!selectedVehicleId) return;
    setIsSavingVehicle(true);
    try {
      const updated = await api.patch(`/trips/${currentTrip.id}/assign`, {
        vehicle_id: Number(selectedVehicleId),
      });
      setCurrentTrip(updated);
      setIsEditingVehicle(false);
      fetchManifest(currentTrip.id);
      if (onUpdate) onUpdate();
    } catch (err) {
      alert(`Помилка зміни автомобіля: ${err.message}`);
    } finally {
      setIsSavingVehicle(false);
    }
  };

  const handleSaveDriver = async () => {
    if (!selectedDriverId) return;
    setIsSavingDriver(true);
    try {
      const updated = await api.patch(`/trips/${currentTrip.id}/assign`, {
        driver_id: Number(selectedDriverId),
      });
      setCurrentTrip(updated);
      setIsEditingDriver(false);
      fetchManifest(currentTrip.id);
      if (onUpdate) onUpdate();
    } catch (err) {
      alert(`Помилка призначення водія: ${err.message}`);
    } finally {
      setIsSavingDriver(false);
    }
  };

  const handleSavePrices = async () => {
    setIsSavingPrices(true);
    try {
      const updated = await api.put(`/trips/${currentTrip.id}`, {
        driver_id: Number(currentTrip.driver_id),
        vehicle_id: Number(currentTrip.vehicle_id),
        route: currentTrip.route,
        date: currentTrip.date,
        departure_time: currentTrip.departure_time,
        arrival_time: currentTrip.arrival_time,
        price_seated: Number(priceForm.price_seated),
        price_standing: Number(priceForm.price_standing),
        price_parcel: Number(priceForm.price_parcel),
      });
      setCurrentTrip(updated);
      setIsEditingPrices(false);
      fetchManifest(currentTrip.id);
      if (onUpdate) onUpdate();
    } catch (err) {
      alert(`Помилка збереження тарифів рейсу: ${err.message}`);
    } finally {
      setIsSavingPrices(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    if (newStatus === 'CANCELLED') {
      if (!confirm(`⚠️ Ви дійсно бажаєте скасувати рейс #${currentTrip.id}? Всім заброньованим пасажирам буде автоматично надіслано сповіщення про скасування у Telegram!`)) {
        return;
      }
    }

    if (newStatus === 'CLOSED') {
      if (currentTrip.status !== 'COMPLETED') {
        alert("⚠️ Закрити рейс (фінансове закриття) можна лише після його завершення (коли оперативний стан 'Завершено').");
        return;
      }
      setCloseForm({
        submitted_cash: manifestData?.total_revenue || '',
        submitted_card: 0,
        comment: '',
      });
      setShowCloseModal(true);
      return;
    }

    setIsUpdatingStatus(true);
    try {
      const updated = await api.put(`/trips/${currentTrip.id}/status`, { status: newStatus });
      setCurrentTrip(updated);
      fetchManifest(currentTrip.id);
      if (onUpdate) onUpdate();
    } catch (err) {
      alert(`Помилка зміни статусу рейсу: ${err.message}`);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleFinancialCloseSubmit = async (e) => {
    e.preventDefault();
    setIsClosingTrip(true);
    try {
      const cashVal = Number(closeForm.submitted_cash) || 0;
      const cardVal = Number(closeForm.submitted_card) || 0;
      const updated = await api.post(`/trips/${currentTrip.id}/close`, {
        submitted_cash: cashVal,
        submitted_card: cardVal,
        submitted_amount: cashVal + cardVal,
        comment: closeForm.comment,
      });
      setCurrentTrip(updated);
      setShowCloseModal(false);
      fetchManifest(currentTrip.id);
      if (onUpdate) onUpdate();
    } catch (err) {
      alert(`Помилка фінансового закриття рейсу: ${err.message}`);
    } finally {
      setIsClosingTrip(false);
    }
  };

  const handleBookingStatusChange = async (bookingId, newStatus) => {
    try {
      await api.patch(`/bookings/${bookingId}/status`, { status: newStatus });
      fetchManifest(currentTrip.id);
    } catch (err) {
      alert(`Помилка зміни статусу бронювання: ${err.message}`);
    }
  };

  const handleAddBookingSubmit = async (e) => {
    e.preventDefault();
    if (!newBooking.phone) {
      alert('Будь ласка, вкажіть телефон пасажира');
      return;
    }
    let digits = newBooking.phone.replace(/\D/g, '');
    if (digits.startsWith('380') && digits.length === 12) {
      digits = digits.slice(2);
    }
    if (digits.length !== 10 || !digits.startsWith('0')) {
      alert('⚠️ Номер телефону повинен містити рівно 10 цифр (наприклад: 0971234567 або +380971234567)!');
      return;
    }
    setIsAddingBooking(true);
    try {
      await api.post(`/trips/${currentTrip.id}/manifest/booking`, {
        booking_type: newBooking.booking_type,
        source: newBooking.source,
        phone: newBooking.phone,
        full_name: newBooking.full_name || newBooking.phone,
        seats: Number(newBooking.seats),
        comment: newBooking.comment,
      });
      setShowAddForm(false);
      setNewBooking({
        booking_type: 'SEATED',
        source: 'PHONE',
        phone: '',
        full_name: '',
        seats: 1,
        comment: '',
      });
      fetchManifest(currentTrip.id);
      if (onUpdate) onUpdate();
    } catch (err) {
      alert(`Помилка додавання запису в маніфест: ${err.message}`);
    } finally {
      setIsAddingBooking(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'BOARDING':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse';
      case 'ACTIVE':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
      case 'COMPLETED':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
      case 'CANCELLED':
        return 'bg-red-500/20 text-red-300 border-red-500/40';
      case 'CLOSED':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
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

  const getSourceIconAndBadge = (source) => {
    switch (source) {
      case 'PHONE':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
            <Phone size={11} /> По телефону
          </span>
        );
      case 'INSTAGRAM':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-pink-400 bg-pink-500/10 px-2 py-0.5 rounded border border-pink-500/20">
            <Instagram size={11} /> Instagram
          </span>
        );
      case 'BOT':
      case 'WEB':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-yellow-400 bg-yellow-500/10 px-2 py-0.5 rounded border border-yellow-500/20">
            <Smartphone size={11} /> Telegram Mini App
          </span>
        );
      case 'DRIVER':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            <User size={11} /> Водій
          </span>
        );
      default:
        return <span className="text-xs text-slate-400">{source}</span>;
    }
  };

  const getBookingTypeBadge = (bType) => {
    switch (bType) {
      case 'SEATED':
        return (
          <span className="inline-flex items-center gap-1 font-semibold text-slate-200">
            🪑 Сидяче
          </span>
        );
      case 'STANDING':
        return (
          <span className="inline-flex items-center gap-1 font-semibold text-amber-300">
            🧍 Стояче
          </span>
        );
      case 'PARCEL':
        return (
          <span className="inline-flex items-center gap-1 font-semibold text-purple-300">
            📦 Посилка
          </span>
        );
      default:
        return bType;
    }
  };

  const getPassengerStatusBadge = (st) => {
    switch (st) {
      case 'BOARDED':
        return <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-md border border-emerald-500/30">🟢 Посадка здійснена</span>;
      case 'PAID':
        return <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-md border border-emerald-500/30">🟢 Оплачено</span>;
      case 'RESERVED':
        return <span className="text-xs font-bold text-yellow-400 bg-yellow-500/10 px-2.5 py-1 rounded-md border border-yellow-500/30">🟡 Заброньовано</span>;
      case 'NOSHOW':
        return <span className="text-xs font-bold text-red-400 bg-red-500/10 px-2.5 py-1 rounded-md border border-red-500/30">🔴 Не з'явився</span>;
      case 'CANCELLED':
        return <span className="text-xs font-bold text-slate-400 bg-slate-800 px-2.5 py-1 rounded-md border border-slate-700">⚪ Скасовано</span>;
      default:
        return <span className="text-xs text-slate-400">{st}</span>;
    }
  };

  const routeTitle = currentTrip.route === 'drohobych-lviv'
    ? 'Дрогобич → Львів'
    : currentTrip.route === 'lviv-drohobych'
    ? 'Львів → Дрогобич'
    : currentTrip.route;

  const fromCity = currentTrip.route === 'drohobych-lviv' ? 'Дрогобич (АВ)' : 'Львів (Головний вокзал)';
  const toCity = currentTrip.route === 'drohobych-lviv' ? 'Львів (Головний вокзал)' : 'Дрогобич (АВ)';

  // Filter bookings list
  const filteredBookings = (manifestData?.bookings || []).filter((b) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const nameMatch = (b.passenger_name || '').toLowerCase().includes(query);
    const phoneMatch = (b.passenger_phone || '').includes(query);
    const commentMatch = (b.comment || '').toLowerCase().includes(query);
    return nameMatch || phoneMatch || commentMatch;
  });

  const totalSubmitted = (Number(closeForm.submitted_cash) || 0) + (Number(closeForm.submitted_card) || 0);
  const expectedRevenue = manifestData?.total_revenue || 0;
  const difference = totalSubmitted - expectedRevenue;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto animate-fade-in">
      <div className="relative w-full max-w-5xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden my-6">
        
        {/* Header Bar */}
        <div className="p-6 border-b border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-yellow-400/10 border border-yellow-400/20 flex items-center justify-center text-yellow-400 font-mono font-bold text-lg">
              #{currentTrip.id}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="font-display text-xl uppercase tracking-wider text-slate-100">
                  Пасажирський Маніфест Рейсу #{currentTrip.id}
                </h2>
                <span className={`text-xs px-3 py-1 rounded-full border font-semibold ${getStatusBadge(currentTrip.status)}`}>
                  {translateStatus(currentTrip.status)}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Оперативне керування пасажирами, посадкою та фінансовим закриттям за Київським часом
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchManifest(currentTrip.id)}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              title="Оновити маніфест з БД"
            >
              <RefreshCw size={18} className={isLoadingManifest ? 'animate-spin text-yellow-400' : ''} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          
          {/* 🚌 ІНФОРМАЦІЙНА ШАПКА РЕЙСУ (MANIFEST HEADER) */}
          <div className="bg-slate-950/90 border border-slate-800 rounded-2xl p-6 shadow-inner space-y-6">
            
            {/* Route Visualizer & Schedule */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center border-b border-slate-800/80 pb-6">
              
              {/* Departure Point */}
              <div className="space-y-1">
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <MapPin size={14} className="text-yellow-400" />
                  <span>Відправлення</span>
                </div>
                <div className="text-lg font-bold text-slate-100">{fromCity}</div>
                <div className="text-xs text-slate-400 flex items-center gap-2">
                  <Calendar size={13} className="text-slate-500" />
                  <span className="font-mono text-slate-300">{currentTrip.date}</span>
                  <Clock size={13} className="text-yellow-400 ml-1" />
                  <span className="font-mono font-bold text-yellow-400 text-sm">{currentTrip.departure_time}</span>
                </div>
              </div>

              {/* Direction Indicator */}
              <div className="flex flex-col items-center justify-center my-2 md:my-0">
                <div className="text-xs font-semibold text-yellow-400 mb-1 flex items-center gap-1">
                  <span>{routeTitle}</span>
                </div>
                <div className="w-full flex items-center justify-center gap-2">
                  <div className="h-0.5 flex-1 bg-gradient-to-r from-yellow-400/20 to-yellow-400"></div>
                  <div className="w-8 h-8 rounded-full bg-yellow-400/10 border border-yellow-400/30 flex items-center justify-center text-yellow-400">
                    <ArrowRight size={16} />
                  </div>
                  <div className="h-0.5 flex-1 bg-gradient-to-r from-yellow-400 to-yellow-400/20"></div>
                </div>
                <div className="text-[10px] text-slate-500 mt-1">Прямий рейс</div>
              </div>

              {/* Arrival Point */}
              <div className="space-y-1 md:text-right">
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 md:justify-end">
                  <MapPin size={14} className="text-emerald-400" />
                  <span>Прибуття</span>
                </div>
                <div className="text-lg font-bold text-slate-100">{toCity}</div>
                <div className="text-xs text-slate-400 flex items-center gap-2 md:justify-end">
                  <Clock size={13} className="text-slate-500" />
                  <span className="font-mono text-slate-300">
                    {currentTrip.arrival_time || 'Очікується'}
                  </span>
                </div>
              </div>
            </div>

            {/* Vehicle, Driver & Tariff Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              
              {/* Vehicle Info Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 relative group">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <Bus size={16} className="text-yellow-400" />
                    <span>Транспортний Засіб</span>
                  </div>

                  {!isEditingVehicle && currentTrip.status !== 'CLOSED' && (
                    <button
                      onClick={() => setIsEditingVehicle(true)}
                      className="w-6 h-6 rounded-md bg-red-500/20 hover:bg-red-500/40 text-red-400 border border-red-500/30 flex items-center justify-center transition-all cursor-pointer shadow-sm hover:scale-105"
                      title="Змінити транспортний засіб"
                    >
                      <Pencil size={12} />
                    </button>
                  )}
                </div>

                {isEditingVehicle ? (
                  <div className="space-y-2 pt-1">
                    <select
                      value={selectedVehicleId}
                      onChange={(e) => setSelectedVehicleId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 text-xs font-medium text-slate-200 rounded-lg p-2 outline-none focus:border-yellow-400"
                    >
                      {availableVehicles.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.model} ({v.plate_number || v.plate})
                        </option>
                      ))}
                    </select>

                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setIsEditingVehicle(false)}
                        className="px-2 py-1 rounded bg-slate-800 text-slate-400 hover:text-slate-200 text-xs cursor-pointer"
                      >
                        <X size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={handleSaveVehicle}
                        disabled={isSavingVehicle}
                        className="px-3 py-1 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs flex items-center gap-1 cursor-pointer"
                      >
                        <Check size={14} />
                        <span>Зберегти</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="font-bold text-slate-100 text-sm">
                      {currentTrip.vehicle_model || `Авто #${currentTrip.vehicle_id}`}
                    </div>
                    <div className="inline-flex items-center gap-2 bg-slate-950 px-2.5 py-1 rounded-md border border-slate-700 text-xs font-mono font-bold text-slate-200">
                      <span className="text-blue-400 text-[10px]">UA</span>
                      <span>{currentTrip.vehicle_plate || `BC ${currentTrip.vehicle_id} AB`}</span>
                    </div>
                  </>
                )}
              </div>

              {/* Driver Info Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 relative group">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <User size={16} className="text-yellow-400" />
                    <span>Призначений Водій</span>
                  </div>

                  {!isEditingDriver && currentTrip.status !== 'CLOSED' && (
                    <button
                      onClick={() => setIsEditingDriver(true)}
                      className="w-6 h-6 rounded-md bg-red-500/20 hover:bg-red-500/40 text-red-400 border border-red-500/30 flex items-center justify-center transition-all cursor-pointer shadow-sm hover:scale-105"
                      title="Змінити призначеного водія"
                    >
                      <Pencil size={12} />
                    </button>
                  )}
                </div>

                {isEditingDriver ? (
                  <div className="space-y-2 pt-1">
                    <select
                      value={selectedDriverId}
                      onChange={(e) => setSelectedDriverId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 text-xs font-medium text-slate-200 rounded-lg p-2 outline-none focus:border-yellow-400"
                    >
                      {availableDrivers.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.full_name || d.name} ({d.phone || 'Без тел.'})
                        </option>
                      ))}
                    </select>

                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setIsEditingDriver(false)}
                        className="px-2 py-1 rounded bg-slate-800 text-slate-400 hover:text-slate-200 text-xs cursor-pointer"
                      >
                        <X size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={handleSaveDriver}
                        disabled={isSavingDriver}
                        className="px-3 py-1 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs flex items-center gap-1 cursor-pointer"
                      >
                        <Check size={14} />
                        <span>Зберегти</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="font-bold text-slate-100 text-sm">
                      {currentTrip.driver_name || `Водій #${currentTrip.driver_id}`}
                    </div>
                    {currentTrip.driver_phone ? (
                      <a
                        href={`tel:${currentTrip.driver_phone}`}
                        className="inline-flex items-center gap-1.5 text-xs text-yellow-400 hover:text-yellow-300 font-mono transition-colors"
                      >
                        <Phone size={12} />
                        <span>{currentTrip.driver_phone}</span>
                      </a>
                    ) : (
                      <span className="text-xs text-slate-500">Телефон відсутній</span>
                    )}
                  </>
                )}
              </div>

              {/* Tariffs & Capacity Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 relative group">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <DollarSign size={16} className="text-emerald-400" />
                    <span>Тариф та Місткість</span>
                  </div>

                  {!isEditingPrices && currentTrip.status !== 'CLOSED' && (
                    <button
                      onClick={() => {
                        setPriceForm({
                          price_seated: currentTrip.price_seated || 120,
                          price_standing: currentTrip.price_standing || 80,
                          price_parcel: currentTrip.price_parcel || 100,
                        });
                        setIsEditingPrices(true);
                      }}
                      className="w-6 h-6 rounded-md bg-emerald-500/20 hover:bg-emerald-500/40 text-emerald-400 border border-emerald-500/30 flex items-center justify-center transition-all cursor-pointer shadow-sm hover:scale-105"
                      title="Редагувати тарифи рейсу"
                    >
                      <Pencil size={12} />
                    </button>
                  )}
                </div>

                {isEditingPrices ? (
                  <div className="space-y-2 pt-1">
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1 font-semibold">Сидяче (₴)</label>
                        <input
                          type="number"
                          value={priceForm.price_seated}
                          onChange={(e) => setPriceForm({ ...priceForm, price_seated: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-700 text-xs font-bold text-yellow-400 rounded-lg p-1.5 outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1 font-semibold">Стояче (₴)</label>
                        <input
                          type="number"
                          value={priceForm.price_standing}
                          onChange={(e) => setPriceForm({ ...priceForm, price_standing: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-700 text-xs font-bold text-slate-200 rounded-lg p-1.5 outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1 font-semibold">Коробка (₴)</label>
                        <input
                          type="number"
                          value={priceForm.price_parcel}
                          onChange={(e) => setPriceForm({ ...priceForm, price_parcel: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-700 text-xs font-bold text-emerald-400 rounded-lg p-1.5 outline-none"
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => setIsEditingPrices(false)}
                        className="px-2 py-1 rounded bg-slate-800 text-slate-400 hover:text-slate-200 text-xs cursor-pointer"
                      >
                        <X size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={handleSavePrices}
                        disabled={isSavingPrices}
                        className="px-3 py-1 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs flex items-center gap-1 cursor-pointer"
                      >
                        <Check size={14} />
                        <span>Зберегти</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Сидяче:</span>
                      <span className="font-mono font-bold text-yellow-400">{currentTrip.price_seated} ₴</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Стояче:</span>
                      <span className="font-mono font-bold text-slate-200">{currentTrip.price_standing} ₴</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Коробка / Посилка:</span>
                      <span className="font-mono font-bold text-emerald-400">{currentTrip.price_parcel || 100} ₴</span>
                    </div>
                    <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-800 flex justify-between">
                      <span>Місткість:</span>
                      <span className="text-slate-300 font-semibold">{currentTrip.seats_limit_snapshot} сид. / {currentTrip.standing_limit_snapshot} ст.</span>
                    </div>
                  </>
                )}
              </div>

            </div>

            {/* If Trip is CLOSED: Display Financial Summary Badge */}
            {currentTrip.status === 'CLOSED' ? (
              <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-bold text-purple-300 uppercase tracking-wider flex items-center gap-2">
                    <Lock size={16} />
                    <span>Фінансово закритий рейс (Прийнято Диспетчером: {currentTrip.closed_by || 'Диспетчер'})</span>
                  </div>
                  <span className="text-xs font-mono font-bold text-purple-400 bg-purple-500/20 px-3 py-1 rounded-full border border-purple-500/30">
                    ЗАКРИТО
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs pt-1">
                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">Здано водієм Готівкою:</span>
                    <span className="font-mono font-bold text-emerald-400 text-sm">{currentTrip.submitted_cash ?? 0} ₴</span>
                  </div>

                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">Здано водієм Карткою:</span>
                    <span className="font-mono font-bold text-sky-400 text-sm">{currentTrip.submitted_card ?? 0} ₴</span>
                  </div>

                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">Загалом здано в касу:</span>
                    <span className="font-mono font-bold text-yellow-400 text-sm">{(currentTrip.submitted_amount ?? 0)} ₴</span>
                  </div>
                </div>

                {currentTrip.close_comment && (
                  <div className="text-xs text-slate-300 bg-slate-900/80 p-2.5 rounded-lg border border-purple-500/20 flex items-center gap-2">
                    <MessageSquare size={14} className="text-purple-400 shrink-0" />
                    <span><strong>Примітка диспетчера:</strong> {currentTrip.close_comment}</span>
                  </div>
                )}
              </div>
            ) : (
              /* Change Status Controls */
              <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck size={16} className="text-yellow-400" />
                  <span>Оперативний стан рейсу:</span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {['SCHEDULED', 'BOARDING', 'ACTIVE', 'COMPLETED', 'CLOSED', 'CANCELLED'].map((st) => {
                    const isClosedOption = st === 'CLOSED';
                    const isCancelledOption = st === 'CANCELLED';
                    const isClosingDisabled = isClosedOption && currentTrip.status !== 'COMPLETED';

                    return (
                      <button
                        key={st}
                        disabled={isUpdatingStatus || currentTrip.status === st || isClosingDisabled}
                        onClick={() => handleStatusChange(st)}
                        title={isClosingDisabled ? "Закрити рейс можна лише після його завершення (стан 'Завершено')" : ''}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                          currentTrip.status === st
                            ? 'bg-yellow-400 text-slate-950 shadow-md cursor-default'
                            : isCancelledOption
                            ? 'bg-red-500/20 text-red-300 border border-red-500/40 hover:bg-red-500/40 cursor-pointer'
                            : isClosedOption
                            ? isClosingDisabled
                              ? 'bg-purple-500/10 text-purple-400/40 border border-purple-500/20 cursor-not-allowed opacity-50'
                              : 'bg-purple-500/20 text-purple-300 border border-purple-500/40 hover:bg-purple-500/40 cursor-pointer'
                            : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 cursor-pointer'
                        }`}
                      >
                        {translateStatus(st)}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

          </div>

          {/* 💰 ФІНАНСОВЕ ЗАКРИТТЯ РЕЙСУ (CLOSING MODAL DIALOG) */}
          {showCloseModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-md animate-fade-in">
              <form onSubmit={handleFinancialCloseSubmit} className="relative w-full max-w-lg bg-slate-900 border border-purple-500/40 rounded-3xl p-6 shadow-2xl space-y-5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2 text-purple-300 font-bold text-base">
                    <DollarSign className="text-purple-400" size={20} />
                    <span>Фінансове закриття рейсу #{currentTrip.id}</span>
                  </div>
                  <button type="button" onClick={() => setShowCloseModal(false)} className="text-slate-400 hover:text-slate-200">
                    <X size={18} />
                  </button>
                </div>

                {/* Calculated expected revenue */}
                <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex items-center justify-between">
                  <span className="text-xs text-slate-400">Розрахункова каса з квитків маніфесту:</span>
                  <span className="font-mono font-bold text-yellow-400 text-lg">{expectedRevenue} ₴</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Здано водієм Готівкою (₴) *</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={closeForm.submitted_cash}
                      onChange={(e) => setCloseForm({ ...closeForm, submitted_cash: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-emerald-400 font-mono font-bold outline-none focus:border-purple-400 text-sm"
                      placeholder="0.00"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Здано водієм Карткою (₴) *</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={closeForm.submitted_card}
                      onChange={(e) => setCloseForm({ ...closeForm, submitted_card: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sky-400 font-mono font-bold outline-none focus:border-purple-400 text-sm"
                      placeholder="0.00"
                      required
                    />
                  </div>
                </div>

                {/* Calculation breakdown */}
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Всього здано в касу:</span>
                    <span className="font-mono font-bold text-slate-100 text-sm">{totalSubmitted} ₴</span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-slate-900">
                    <span className="text-slate-400">Різниця від розрахункової каси:</span>
                    <span className={`font-mono font-bold ${difference >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {difference >= 0 ? `+${difference} ₴` : `${difference} ₴`}
                    </span>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-400 text-xs font-semibold mb-1">Примітка Диспетчера</label>
                  <input
                    type="text"
                    placeholder="Коментар про передачу готівки водієм..."
                    value={closeForm.comment}
                    onChange={(e) => setCloseForm({ ...closeForm, comment: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 outline-none focus:border-purple-400"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCloseModal(false)}
                    className="px-4 py-2 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200 text-xs cursor-pointer"
                  >
                    Скасувати
                  </button>
                  <button
                    type="submit"
                    disabled={isClosingTrip}
                    className="px-5 py-2 rounded-xl bg-purple-500 hover:bg-purple-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 shadow-lg cursor-pointer disabled:opacity-50"
                  >
                    <Check size={16} />
                    <span>{isClosingTrip ? 'Закриття...' : 'Фінансово закрити рейс'}</span>
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* 📊 ЛІЧИЛЬНИКИ ЗАПОВНЕНОСТІ ТА ВИРУЧКИ (CAPACITY METRICS) */}
          {manifestData && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              
              {/* Seated Seats Counter */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2">
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                  <span>🪑 Сидячі місця</span>
                  <span className="font-mono text-yellow-400">
                    {Math.round((manifestData.seated_count / Math.max(manifestData.seated_limit, 1)) * 100)}%
                  </span>
                </div>
                <div className="text-2xl font-bold font-mono text-slate-100">
                  {manifestData.seated_count} <span className="text-xs text-slate-500 font-normal">/ {manifestData.seated_limit}</span>
                </div>
                <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                  <div
                    className="h-full bg-yellow-400 transition-all duration-300"
                    style={{ width: `${Math.min(100, (manifestData.seated_count / Math.max(manifestData.seated_limit, 1)) * 100)}%` }}
                  ></div>
                </div>
              </div>

              {/* Standing Seats Counter */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2">
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                  <span>🧍 Стоячі місця</span>
                  <span className="font-mono text-amber-300">
                    {Math.round((manifestData.standing_count / Math.max(manifestData.standing_limit, 1)) * 100)}%
                  </span>
                </div>
                <div className="text-2xl font-bold font-mono text-slate-100">
                  {manifestData.standing_count} <span className="text-xs text-slate-500 font-normal">/ {manifestData.standing_limit}</span>
                </div>
                <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                  <div
                    className="h-full bg-amber-400 transition-all duration-300"
                    style={{ width: `${Math.min(100, (manifestData.standing_count / Math.max(manifestData.standing_limit, 1)) * 100)}%` }}
                  ></div>
                </div>
              </div>

              {/* Parcels Counter */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2">
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                  <span>📦 Посилки / Вантаж</span>
                  <Package size={16} className="text-purple-400" />
                </div>
                <div className="text-2xl font-bold font-mono text-purple-300">
                  {manifestData.parcels_count} <span className="text-xs text-slate-500 font-normal">од.</span>
                </div>
                <div className="text-[11px] text-slate-500">
                  Зареєстровано вантажів
                </div>
              </div>

              {/* Total Revenue Counter */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2">
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                  <span>💰 Виручка рейсу</span>
                  <DollarSign size={16} className="text-emerald-400" />
                </div>
                <div className="text-2xl font-bold font-mono text-emerald-400">
                  {manifestData.total_revenue} ₴
                </div>
                <div className="text-[11px] text-emerald-500 font-medium">
                  Розраховано за активними квитками
                </div>
              </div>

            </div>
          )}

          {/* 👥 СПИСОК ПАСАЖИРІВ ТА БАГАЖУ (PASSENGER MANIFEST TABLE) */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
            
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <h3 className="font-display text-lg uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <Users size={20} className="text-yellow-400" />
                  <span>Маніфест Пасажирів та Посилок ({manifestData?.bookings?.length || 0})</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Перелік заброньованих місць, джерел бронювання та оперативна посадка
                </p>
              </div>

              <div className="flex items-center gap-3">
                {/* Search Bar */}
                <div className="relative">
                  <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Пошук пасажира чи тел..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-200 outline-none w-48 font-medium"
                  />
                </div>

                {/* Add Passenger / Parcel Button */}
                {currentTrip.status !== 'CLOSED' && (
                  <button
                    onClick={() => setShowAddForm(!showAddForm)}
                    className="bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
                  >
                    <Plus size={16} />
                    <span>Додати запис</span>
                  </button>
                )}
              </div>
            </div>

            {/* Quick Add Form (Phone / Instagram / Parcel / Seat) */}
            {showAddForm && currentTrip.status !== 'CLOSED' && (
              <form onSubmit={handleAddBookingSubmit} className="bg-slate-950 border border-yellow-400/30 p-4 rounded-xl space-y-4 animate-fade-in">
                <div className="text-xs font-bold uppercase tracking-wider text-yellow-400 flex items-center justify-between">
                  <span>➕ Додати пасажира або посилку в маніфест</span>
                  <button type="button" onClick={() => setShowAddForm(false)} className="text-slate-400 hover:text-slate-200">
                    <X size={16} />
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-6 gap-3 items-end text-xs">
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Тип запису</label>
                    <select
                      value={newBooking.booking_type}
                      onChange={(e) => setNewBooking({ ...newBooking, booking_type: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 outline-none focus:border-yellow-400"
                    >
                      <option value="SEATED">🪑 Сидяче місце</option>
                      <option value="STANDING">🧍 Стояче місце</option>
                      <option value="PARCEL">📦 Посилка / Вантаж</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Джерело</label>
                    <select
                      value={newBooking.source}
                      onChange={(e) => setNewBooking({ ...newBooking, source: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 outline-none focus:border-yellow-400 cursor-pointer"
                    >
                      <option value="PHONE">📞 По телефону</option>
                      <option value="INSTAGRAM">📸 Instagram</option>
                      <option value="WEB">🌐 Диспетчер / Веб</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Телефон *</label>
                    <input
                      type="text"
                      placeholder="+380XXXXXXXXX"
                      value={newBooking.phone}
                      onChange={(e) => setNewBooking({ ...newBooking, phone: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 outline-none focus:border-yellow-400 font-mono"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">ПІБ пасажира</label>
                    <input
                      type="text"
                      placeholder="ПІБ або примітка"
                      value={newBooking.full_name}
                      onChange={(e) => setNewBooking({ ...newBooking, full_name: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 outline-none focus:border-yellow-400"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">К-сть (месць)</label>
                    <input
                      type="number"
                      min="1"
                      value={newBooking.seats}
                      onChange={(e) => setNewBooking({ ...newBooking, seats: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 outline-none focus:border-yellow-400 font-mono"
                      required
                    />
                  </div>

                  <div>
                    <button
                      type="submit"
                      disabled={isAddingBooking}
                      className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold p-2 rounded-lg text-xs flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                    >
                      <Check size={14} />
                      <span>{isAddingBooking ? 'Запис...' : 'Зареєструвати'}</span>
                    </button>
                  </div>
                </div>

                <div>
                  <input
                    type="text"
                    placeholder="Примітка / коментар (наприклад: зупинка біля ринку, 2 посилки)"
                    value={newBooking.comment}
                    onChange={(e) => setNewBooking({ ...newBooking, comment: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 outline-none focus:border-yellow-400"
                  />
                </div>
              </form>
            )}

            {/* Manifest Table */}
            {isLoadingManifest ? (
              <div className="py-8 text-center text-slate-400 flex flex-col items-center gap-2">
                <RefreshCw className="animate-spin text-yellow-400" size={24} />
                <span>Завантаження списку пасажирів...</span>
              </div>
            ) : filteredBookings.length === 0 ? (
              <div className="p-8 text-center text-slate-500 bg-slate-950/40 rounded-xl border border-slate-800 text-xs">
                У маніфесті цього рейсу немає зареєстрованих пасажирів чи посилок.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] font-semibold border-b border-slate-800">
                    <tr>
                      <th className="p-3">№ / Тип</th>
                      <th className="p-3">Пасажир / Телефон</th>
                      <th className="p-3">К-сть</th>
                      <th className="p-3">Джерело</th>
                      <th className="p-3">Статус / Посадка</th>
                      <th className="p-3 font-mono">До сплати</th>
                      <th className="p-3">Примітка</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium">
                    {filteredBookings.map((b, idx) => (
                      <tr key={b.id} className="hover:bg-slate-950/50 transition-colors">
                        
                        {/* Type & Number */}
                        <td className="p-3 font-mono">
                          <div className="flex items-center gap-2">
                            <span className="text-slate-500 font-bold">#{idx + 1}</span>
                            {getBookingTypeBadge(b.booking_type)}
                          </div>
                        </td>

                        {/* Passenger Name & Phone */}
                        <td className="p-3">
                          <div className="font-bold text-slate-100">{b.passenger_name || 'Невідомий'}</div>
                          {b.passenger_phone && (
                            <a
                              href={`tel:${b.passenger_phone}`}
                              className="text-slate-400 hover:text-yellow-400 font-mono text-[11px] flex items-center gap-1 mt-0.5"
                            >
                              <Phone size={11} />
                              <span>{b.passenger_phone}</span>
                            </a>
                          )}
                        </td>

                        {/* Quantity */}
                        <td className="p-3 font-mono font-bold text-yellow-400">
                          {b.passengers_count}
                        </td>

                        {/* Source */}
                        <td className="p-3">
                          {getSourceIconAndBadge(b.source)}
                        </td>

                        {/* Status & Quick Action Buttons */}
                        <td className="p-3 space-y-1">
                          <div>{getPassengerStatusBadge(b.status)}</div>
                          
                          {/* Boarding & Cancellation Actions */}
                          {b.status !== 'CANCELLED' && currentTrip.status !== 'CLOSED' && (
                            <div className="flex flex-wrap items-center gap-1 pt-1">
                              {b.status !== 'BOARDED' && (
                                <button
                                  type="button"
                                  onClick={() => handleBookingStatusChange(b.id, 'BOARDED')}
                                  className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/40 border border-emerald-500/30 text-[10px] font-bold flex items-center gap-1 cursor-pointer"
                                  title="Посадка здійснена"
                                >
                                  <UserCheck size={11} /> Посадка
                                </button>
                              )}

                              {b.status !== 'NOSHOW' && (
                                <button
                                  type="button"
                                  onClick={() => handleBookingStatusChange(b.id, 'NOSHOW')}
                                  className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 hover:bg-amber-500/40 border border-amber-500/30 text-[10px] font-bold flex items-center gap-1 cursor-pointer"
                                  title="Відмітити як не з'явився"
                                >
                                  <UserX size={11} /> No-show
                                </button>
                              )}

                              {/* 📞 Скасувати за дзвінком пасажира */}
                              <button
                                type="button"
                                onClick={() => {
                                  if (confirm(`Скасувати бронювання пасажира ${b.passenger_name || ''}? Слот буде вивільнено.`)) {
                                    handleBookingStatusChange(b.id, 'CANCELLED');
                                  }
                                }}
                                className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 hover:bg-red-500/40 border border-red-500/30 text-[10px] font-bold flex items-center gap-1 cursor-pointer"
                                title="Скасувати за дзвінком пасажира"
                              >
                                <X size={11} /> Скасувати
                              </button>
                            </div>
                          )}
                        </td>

                        {/* Amount */}
                        <td className="p-3 font-mono font-bold text-emerald-400 text-sm">
                          {b.amount_paid} ₴
                        </td>

                        {/* Comment / Note */}
                        <td className="p-3 text-slate-400 text-[11px]">
                          {b.comment ? (
                            <div className="flex items-center gap-1 text-slate-300">
                              <MessageSquare size={12} className="text-yellow-400 shrink-0" />
                              <span>{b.comment}</span>
                            </div>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>

                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
