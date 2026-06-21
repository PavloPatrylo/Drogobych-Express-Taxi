// ══════════════════════════════════════════════
//  ДАНІ ТА СТАН ДОДАТКУ
//  (Mock-дані; у проді тут будуть запити до API)
// ══════════════════════════════════════════════

const TODAY = new Date();
let currentDayOffset = 0;
let currentManifestTripId = null;
let pendingCloseId = null;
let pendingConfirmCb = null;

// ── Водії ──
const drivers = [
  { id: 1, name: 'Pablo Водій', phone: '+380991234567' },
  { id: 2, name: 'Олексій Мороз', phone: '+380671112233' },
  { id: 3, name: 'Тарас Іванців', phone: '+380501234567' },
];

// ── Автопарк ──
let vehicles = [
  { id: 1, plate: 'ВС0000ТЕ', model: 'Еталон', total_seats: 18, total_standing: 5, is_active: true },
  { id: 2, plate: 'АА1234ВВ', model: 'Volkswagen Crafter', total_seats: 15, total_standing: 3, is_active: true },
  { id: 3, plate: 'ВС9999КК', model: 'Mercedes Sprinter', total_seats: 20, total_standing: 6, is_active: false },
];

// ── Пасажири (CRM) ──
let passengers = [
  { id: 1, full_name: 'Іван Іванов', phone: '+380501112233', telegram_id: 12345, is_active: true, created_at: '2026-01-10', total_trips: 12, total_noshows: 0 },
  { id: 2, full_name: 'Марія Коваль', phone: '+380671112233', telegram_id: 23456, is_active: true, created_at: '2026-01-15', total_trips: 8, total_noshows: 1 },
  { id: 3, full_name: 'Олег Петренко', phone: '+380631112233', telegram_id: null, is_active: true, created_at: '2026-02-01', total_trips: 3, total_noshows: 0 },
  { id: 4, full_name: 'Наталія Шевченко', phone: '+380991112233', telegram_id: 34567, is_active: true, created_at: '2026-02-10', total_trips: 20, total_noshows: 4 },
  { id: 5, full_name: 'Роман Бойко', phone: '+380681112233', telegram_id: 45678, is_active: false, created_at: '2025-12-05', total_trips: 5, total_noshows: 3 },
  { id: 6, full_name: 'Тетяна Лисенко', phone: '+380711112233', telegram_id: 56789, is_active: true, created_at: '2026-03-01', total_trips: 1, total_noshows: 0 },
];

// ── Бронювання ──
let bookings = [
  { id: 1, trip_id: 1, passenger_id: 1, created_by_id: 1, booking_type: 'SEATED', source: 'BOT', status: 'BOARDED', passengers_count: 1, amount_paid: 120, created_at: '2026-06-08 07:10', validated_by_id: 1, validated_at: '2026-06-08 14:35', comment: null },
  { id: 2, trip_id: 1, passenger_id: 2, created_by_id: 10, booking_type: 'SEATED', source: 'PHONE', status: 'RESERVED', passengers_count: 1, amount_paid: 120, created_at: '2026-06-08 08:00', validated_by_id: null, validated_at: null, comment: null },
  { id: 3, trip_id: 1, passenger_id: null, created_by_id: 1, booking_type: 'STANDING', source: 'DRIVER', status: 'BOARDED', passengers_count: 1, amount_paid: 80, created_at: '2026-06-08 14:40', validated_by_id: 1, validated_at: '2026-06-08 14:40', comment: null },
  { id: 4, trip_id: 2, passenger_id: 3, created_by_id: 3, booking_type: 'SEATED', source: 'BOT', status: 'RESERVED', passengers_count: 2, amount_paid: 240, created_at: '2026-06-08 09:00', validated_by_id: null, validated_at: null, comment: null },
  { id: 5, trip_id: 3, passenger_id: 4, created_by_id: 4, booking_type: 'SEATED', source: 'BOT', status: 'RESERVED', passengers_count: 1, amount_paid: 120, created_at: '2026-06-08 10:00', validated_by_id: null, validated_at: null, comment: null },
  { id: 6, trip_id: 1, passenger_id: null, created_by_id: 1, booking_type: 'PARCEL', source: 'DRIVER', status: 'BOARDED', passengers_count: 0, amount_paid: 50, created_at: '2026-06-08 14:42', validated_by_id: 1, validated_at: null, comment: 'Пакунок до Стрия' },
  { id: 7, trip_id: 4, passenger_id: 1, created_by_id: 1, booking_type: 'SEATED', source: 'BOT', status: 'BOARDED', passengers_count: 1, amount_paid: 120, created_at: '2026-06-07 11:00', validated_by_id: 2, validated_at: '2026-06-07 17:05', comment: null },
  { id: 8, trip_id: 4, passenger_id: 2, created_by_id: 10, booking_type: 'SEATED', source: 'PHONE', status: 'NOSHOW', passengers_count: 1, amount_paid: 0, created_at: '2026-06-07 12:00', validated_by_id: null, validated_at: null, comment: null },
];

let nextBookingId = 9;
let nextPassengerId = 7;

// ── Хелпери дат ──
const formatDate = (d) => { const dd = String(d.getDate()).padStart(2, '0'); const mm = String(d.getMonth() + 1).padStart(2, '0'); return `${dd}.${mm}.${d.getFullYear()}`; };
const getDateForOffset = (offset) => { const d = new Date(TODAY); d.setDate(d.getDate() + offset); return d; };
const isoDate = (d) => d.toISOString().split('T')[0];

// ── Рейси ──
let trips = [
  { id: 1, driver_id: 1, vehicle_id: 1, route: 'drohobych-lviv', date: isoDate(getDateForOffset(0)), departure_time: '14:30', arrival_time: '17:00', status: 'BOARDING', seats_limit_snapshot: 18, standing_limit_snapshot: 5, price_seated: 120, price_standing: 80, closed_by: null },
  { id: 2, driver_id: 2, vehicle_id: 2, route: 'drohobych-lviv', date: isoDate(getDateForOffset(0)), departure_time: '07:00', arrival_time: '09:30', status: 'ACTIVE', seats_limit_snapshot: 15, standing_limit_snapshot: 3, price_seated: 120, price_standing: 80, closed_by: null },
  { id: 3, driver_id: 3, vehicle_id: 1, route: 'lviv-drohobych', date: isoDate(getDateForOffset(0)), departure_time: '16:00', arrival_time: '18:30', status: 'SCHEDULED', seats_limit_snapshot: 18, standing_limit_snapshot: 5, price_seated: 120, price_standing: 80, closed_by: null },
  { id: 4, driver_id: 1, vehicle_id: 2, route: 'drohobych-lviv', date: isoDate(getDateForOffset(-1)), departure_time: '17:00', arrival_time: '19:30', status: 'COMPLETED', seats_limit_snapshot: 15, standing_limit_snapshot: 3, price_seated: 120, price_standing: 80, closed_by: null },
  { id: 5, driver_id: 2, vehicle_id: 1, route: 'lviv-drohobych', date: isoDate(getDateForOffset(1)), departure_time: '08:00', arrival_time: '10:30', status: 'SCHEDULED', seats_limit_snapshot: 18, standing_limit_snapshot: 5, price_seated: 120, price_standing: 80, closed_by: null },
];
let nextTripId = 6;

// ── Аудит-слід ──
const auditLog = [
  { time: '2026-06-08 08:00', action: 'BOOKING_CREATED', trip: 'Д→Л 14:30', passenger: 'Марія Коваль', source: 'PHONE', by: 'Анна Диспетчер' },
  { time: '2026-06-08 07:10', action: 'BOOKING_CREATED', trip: 'Д→Л 14:30', passenger: 'Іван Іванов', source: 'BOT', by: 'Іван Іванов' },
  { time: '2026-06-08 14:35', action: 'BOARDING_VALIDATED', trip: 'Д→Л 14:30', passenger: 'Іван Іванов', source: 'DRIVER', by: 'Pablo Водій' },
  { time: '2026-06-07 12:00', action: 'BOOKING_CREATED', trip: 'Д→Л 17:00', passenger: 'Марія Коваль', source: 'PHONE', by: 'Анна Диспетчер' },
  { time: '2026-06-07 19:30', action: 'NOSHOW_AUTO', trip: 'Д→Л 17:00', passenger: 'Марія Коваль', source: 'SYSTEM', by: 'Система' },
];

// ── Лейбли та довідники статусів ──
const routeLabel = (r) => r === 'drohobych-lviv' ? 'Дрогобич → Львів' : 'Львів → Дрогобич';
const statusLabel = (s) => ({ SCHEDULED: 'Заплановано', BOARDING: 'Посадка', ACTIVE: 'В дорозі', COMPLETED: 'Завершено', CLOSED: 'Закрито', CANCELLED: 'Скасовано' }[s] || s);
const statusBadge = (s) => `badge-${s.toLowerCase()}`;
const statusNext = { SCHEDULED: 'BOARDING', BOARDING: 'ACTIVE', ACTIVE: 'COMPLETED' };
const statusNextLabel = { SCHEDULED: 'Розпочати посадку', BOARDING: 'Вирушити', ACTIVE: 'Завершити рейс' };

// ── Розрахунки ──
function getTripStats(tripId) {
  const b = bookings.filter(x => x.trip_id === tripId && x.status !== 'CANCELLED');
  const seated = b.filter(x => x.booking_type === 'SEATED' && ['RESERVED', 'PAID', 'BOARDED'].includes(x.status)).reduce((a, x) => a + x.passengers_count, 0);
  const standing = b.filter(x => x.booking_type === 'STANDING' && ['RESERVED', 'PAID', 'BOARDED'].includes(x.status)).reduce((a, x) => a + x.passengers_count, 0);
  const parcels = b.filter(x => x.booking_type === 'PARCEL').length;
  const revenue = b.reduce((a, x) => a + (x.amount_paid || 0), 0);
  return { seated, standing, parcels, revenue };
}

function trustScore(p) {
  return Math.max(0, Math.round(100 - (p.total_noshows / Math.max(p.total_trips, 1)) * 100));
}