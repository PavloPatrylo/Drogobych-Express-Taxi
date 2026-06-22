// ══════════════════════════════════════════════
//  СТАН ДОДАТКУ ТА ХЕЛПЕРИ (state.js)
//  (Дані завантажуються з API в main.js; тут лише
//   оголошення змінних та допоміжні функції)
// ══════════════════════════════════════════════

const TODAY = new Date();
let currentDayOffset = 0;
let currentManifestTripId = null;
let pendingCloseId = null;
let pendingConfirmCb = null;

// ── Глобальний стан (наповнюється з API в main.js) ──
let drivers = [];
let vehicles = [];
let passengers = [];
let bookings = [];
let trips = [];
let auditLog = [];

// ── Хелпери дат ──
const formatDate = (d) => { 
  if (!d) return '—';
  const dd = String(d.getDate()).padStart(2, '0'); 
  const mm = String(d.getMonth() + 1).padStart(2, '0'); 
  return `${dd}.${mm}.${d.getFullYear()}`; 
};
const getDateForOffset = (offset) => { 
  const d = new Date(TODAY); 
  d.setDate(d.getDate() + offset); 
  return d; 
};
const isoDate = (d) => d.toISOString().split('T')[0];

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
  if (!p) return 0;
  return Math.max(0, Math.round(100 - (p.total_noshows / Math.max(p.total_trips, 1)) * 100));
}
