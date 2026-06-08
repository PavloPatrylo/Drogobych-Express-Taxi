// ══════════════════════════════════════════════
//  STATE
// ══════════════════════════════════════════════
const TODAY = new Date();
let currentDayOffset = 0;
let currentManifestTripId = null;
let pendingCloseId = null;
let pendingConfirmCb = null;
let editingTripId = null;

// ── Mock Data ──
const drivers = [
  { id: 1, name: 'Pablo Водій', phone: '+380991234567' },
  { id: 2, name: 'Олексій Мороз', phone: '+380671112233' },
  { id: 3, name: 'Тарас Іванців', phone: '+380501234567' },
];

let vehicles = [
  { id: 1, plate: 'ВС0000ТЕ', model: 'Еталон', total_seats: 18, total_standing: 5, is_active: true },
  { id: 2, plate: 'АА1234ВВ', model: 'Volkswagen Crafter', total_seats: 15, total_standing: 3, is_active: true },
  { id: 3, plate: 'ВС9999КК', model: 'Mercedes Sprinter', total_seats: 20, total_standing: 6, is_active: false },
];

let passengers = [
  { id: 1, full_name: 'Іван Іванов', phone: '+380501112233', telegram_id: 12345, is_active: true, created_at: '2026-01-10', total_trips: 12, total_noshows: 0 },
  { id: 2, full_name: 'Марія Коваль', phone: '+380671112233', telegram_id: 23456, is_active: true, created_at: '2026-01-15', total_trips: 8, total_noshows: 1 },
  { id: 3, full_name: 'Олег Петренко', phone: '+380631112233', telegram_id: null, is_active: true, created_at: '2026-02-01', total_trips: 3, total_noshows: 0 },
  { id: 4, full_name: 'Наталія Шевченко', phone: '+380991112233', telegram_id: 34567, is_active: true, created_at: '2026-02-10', total_trips: 20, total_noshows: 4 },
  { id: 5, full_name: 'Роман Бойко', phone: '+380681112233', telegram_id: 45678, is_active: false, created_at: '2025-12-05', total_trips: 5, total_noshows: 3 },
  { id: 6, full_name: 'Тетяна Лисенко', phone: '+380711112233', telegram_id: 56789, is_active: true, created_at: '2026-03-01', total_trips: 1, total_noshows: 0 },
];

let bookings = [
  { id: 1, trip_id: 1, passenger_id: 1, created_by_id: 1, booking_type: 'SEATED', source: 'BOT', status: 'BOARDED', passengers_count: 1, amount_paid: 120, created_at: '2026-06-08 07:10', validated_by_id: 1, validated_at: '2026-06-08 14:35', comment: null },
  { id: 2, trip_id: 1, passenger_id: 2, created_by_id: 10, booking_type: 'SEATED', source: 'PHONE', status: 'RESERVED', passengers_count: 1, amount_paid: 120, created_at: '2026-06-08 08:00', validated_by_id: null, validated_at: null, comment: null },
  { id: 3, trip_id: 1, passenger_id: null, created_by_id: 1, booking_type: 'STANDING', source: 'DRIVER', status: 'BOARDED', passengers_count: 1, amount_paid: 80, created_at: '2026-06-08 14:40', validated_by_id: 1, validated_at: '2026-06-08 14:40', comment: null },
  { id: 4, trip_id: 2, passenger_id: 3, created_by_id: 3, booking_type: 'SEATED', source: 'BOT', status: 'RESERVED', passengers_count: 2, amount_paid: 240, created_at: '2026-06-08 09:00', validated_by_id: null, validated_at: null, comment: null },
  { id: 5, trip_id: 3, passenger_id: 4, created_by_id: 4, booking_type: 'SEATED', source: 'BOT', status: 'RESERVED', passengers_count: 1, amount_paid: 120, created_at: '2026-06-08 10:00', validated_by_id: null, validated_at: null, comment: null },
  { id: 6, trip_id: 1, passenger_id: null, created_by_id: 1, booking_type: 'PARCEL', source: 'DRIVER', status: 'BOARDED', passengers_count: 0, amount_paid: 50, created_at: '2026-06-08 14:42', validated_by_id: 1, validated_at: null, comment: 'Пакунок до Стрия' },
  { id: 7, trip_id: 4, passenger_id: 1, created_by_id: 1, booking_type: 'SEATED', source: 'BOT', status: 'BOARDED', passengers_count: 1, amount_paid: 120, created_at: '2026-06-07 11:00', validated_by_id: 2, validated_at: '2026-06-07 17:05', comment: null },
  { id: 8, trip_id: 4, passenger_id: 2, created_by_id: 10, booking_type: 'SEATED', source: 'PHONE', status: 'NOSHOW', passengers_count: 1, amount_paid: 0, created_at: '2026-06-07 12:00', validated_by_id: null, validated_at: null, comment: null },
  // WAITLIST example
  { id: 9, trip_id: 2, passenger_id: 6, created_by_id: 6, booking_type: 'SEATED', source: 'BOT', status: 'WAITLIST', passengers_count: 1, amount_paid: 0, created_at: '2026-06-08 10:30', validated_by_id: null, validated_at: null, comment: null },
];

let nextBookingId = 10;
let nextPassengerId = 7;

const formatDate = (d) => {
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  return `${dd}.${mm}.${d.getFullYear()}`;
};
const getDateForOffset = (offset) => { const d = new Date(TODAY); d.setDate(d.getDate() + offset); return d; };
const isoDate = (d) => d.toISOString().split('T')[0];

let trips = [
  { id: 1, driver_id: 1, vehicle_id: 1, route: 'drohobych-lviv', date: isoDate(getDateForOffset(0)), departure_time: '14:30', arrival_time: '17:00', status: 'BOARDING', seats_limit_snapshot: 18, standing_limit_snapshot: 5, price_seated: 120, price_standing: 80, closed_by: null, cash_submitted: null },
  { id: 2, driver_id: 2, vehicle_id: 2, route: 'drohobych-lviv', date: isoDate(getDateForOffset(0)), departure_time: '07:00', arrival_time: '09:30', status: 'ACTIVE', seats_limit_snapshot: 15, standing_limit_snapshot: 3, price_seated: 120, price_standing: 80, closed_by: null, cash_submitted: null },
  { id: 3, driver_id: 3, vehicle_id: 1, route: 'lviv-drohobych', date: isoDate(getDateForOffset(0)), departure_time: '16:00', arrival_time: '18:30', status: 'SCHEDULED', seats_limit_snapshot: 18, standing_limit_snapshot: 5, price_seated: 120, price_standing: 80, closed_by: null, cash_submitted: null },
  { id: 4, driver_id: 1, vehicle_id: 2, route: 'drohobych-lviv', date: isoDate(getDateForOffset(-1)), departure_time: '17:00', arrival_time: '19:30', status: 'COMPLETED', seats_limit_snapshot: 15, standing_limit_snapshot: 3, price_seated: 120, price_standing: 80, closed_by: null, cash_submitted: null },
  { id: 5, driver_id: 2, vehicle_id: 1, route: 'lviv-drohobych', date: isoDate(getDateForOffset(1)), departure_time: '08:00', arrival_time: '10:30', status: 'SCHEDULED', seats_limit_snapshot: 18, standing_limit_snapshot: 5, price_seated: 120, price_standing: 80, closed_by: null, cash_submitted: null },
];
let nextTripId = 6;

let auditLog = [
  { time: '2026-06-08 08:00', action: 'BOOKING_CREATED', trip: 'Д→Л 14:30', passenger: 'Марія Коваль', source: 'PHONE', by: 'Анна Диспетчер' },
  { time: '2026-06-08 07:10', action: 'BOOKING_CREATED', trip: 'Д→Л 14:30', passenger: 'Іван Іванов', source: 'BOT', by: 'Іван Іванов' },
  { time: '2026-06-08 14:35', action: 'BOARDING_VALIDATED', trip: 'Д→Л 14:30', passenger: 'Іван Іванов', source: 'DRIVER', by: 'Pablo Водій' },
  { time: '2026-06-07 12:00', action: 'BOOKING_CREATED', trip: 'Д→Л 17:00', passenger: 'Марія Коваль', source: 'PHONE', by: 'Анна Диспетчер' },
  { time: '2026-06-07 19:30', action: 'NOSHOW_AUTO', trip: 'Д→Л 17:00', passenger: 'Марія Коваль', source: 'SYSTEM', by: 'Система' },
];

// ── Default schedule template (times per route)
const SCHEDULE_TEMPLATE = {
  'drohobych-lviv': ['06:00', '08:30', '11:00', '14:30', '17:00', '19:30'],
  'lviv-drohobych': ['07:30', '10:00', '13:00', '16:00', '18:30', '21:00'],
};

const routeLabel = (r) => r === 'drohobych-lviv' ? 'Дрогобич → Львів' : 'Львів → Дрогобич';
const statusLabel = (s) => ({
  SCHEDULED: 'Заплановано', BOARDING: 'Посадка', ACTIVE: 'В дорозі',
  COMPLETED: 'Завершено', CLOSED: 'Закрито', CANCELLED: 'Скасовано'
}[s] || s);
const statusBadge = (s) => `badge-${s.toLowerCase()}`;
const statusNext = { SCHEDULED: 'BOARDING', BOARDING: 'ACTIVE', ACTIVE: 'COMPLETED' };
const statusNextLabel = { SCHEDULED: 'Розпочати посадку', BOARDING: 'Вирушити', ACTIVE: 'Завершити рейс' };

function getTripStats(tripId) {
  const b = bookings.filter(x => x.trip_id === tripId && x.status !== 'CANCELLED');
  const seated = b.filter(x => x.booking_type === 'SEATED' && ['RESERVED', 'PAID', 'BOARDED'].includes(x.status)).reduce((a, x) => a + x.passengers_count, 0);
  const standing = b.filter(x => x.booking_type === 'STANDING' && ['RESERVED', 'PAID', 'BOARDED'].includes(x.status)).reduce((a, x) => a + x.passengers_count, 0);
  const parcels = b.filter(x => x.booking_type === 'PARCEL').length;
  const waitlist = b.filter(x => x.status === 'WAITLIST').length;
  const revenue = b.filter(x => x.status !== 'WAITLIST').reduce((a, x) => a + (x.amount_paid || 0), 0);
  return { seated, standing, parcels, waitlist, revenue };
}

function trustScore(p) {
  return Math.max(0, Math.round(100 - (p.total_noshows / Math.max(p.total_trips, 1)) * 100));
}

function addAudit(action, trip, passenger, source) {
  auditLog.unshift({
    time: new Date().toLocaleString('uk'),
    action, trip, passenger, source,
    by: document.getElementById('current-user-name').textContent
  });
}

// ══════════════════════════════════════════════
//  NAV
// ══════════════════════════════════════════════
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    const page = el.dataset.page;
    document.getElementById('page-' + page).classList.add('active');
    if (page === 'schedule') renderSchedule();
    if (page === 'crm') renderCRM();
    if (page === 'finance') renderFinance();
    if (page === 'vehicles') renderVehicles();
    if (page === 'broadcast') renderBroadcast();
  });
});

// ══════════════════════════════════════════════
//  TABS
// ══════════════════════════════════════════════
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const bar = btn.closest('.tab-bar');
    bar.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    const page = btn.closest('.page');
    page.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
  });
});

// Day filter
document.querySelectorAll('[data-day]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-day]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentDayOffset = parseInt(btn.dataset.day);
    renderSchedule();
  });
});
document.getElementById('route-filter').addEventListener('change', renderSchedule);
document.getElementById('status-filter').addEventListener('change', renderSchedule);

// ══════════════════════════════════════════════
//  SCHEDULE
// ══════════════════════════════════════════════
function renderSchedule() {
  const d = getDateForOffset(currentDayOffset);
  document.getElementById('schedule-date-label').textContent = formatDate(d) +
    (currentDayOffset === 0 ? ' — сьогодні' : currentDayOffset === -1 ? ' — вчора' : ' — завтра');
  const dateStr = isoDate(d);
  const routeF = document.getElementById('route-filter').value;
  const statusF = document.getElementById('status-filter').value;
  let filtered = trips.filter(t => t.date === dateStr);
  if (routeF !== 'all') filtered = filtered.filter(t => t.route === routeF);
  if (statusF !== 'all') filtered = filtered.filter(t => t.status === statusF);
  filtered.sort((a, b) => a.departure_time.localeCompare(b.departure_time));
  const container = document.getElementById('trips-container');
  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">🚌</div><p>Рейсів не знайдено. Змініть фільтри або створіть рейс.</p></div>`;
    return;
  }
  container.innerHTML = filtered.map(t => renderTripCard(t)).join('');
}

function renderTripCard(t) {
  const stats = getTripStats(t.id);
  const driver = drivers.find(d => d.id === t.driver_id);
  const vehicle = vehicles.find(v => v.id === t.vehicle_id);
  const pct = t.seats_limit_snapshot > 0 ? Math.round((stats.seated / t.seats_limit_snapshot) * 100) : 0;
  const fillClass = pct >= 90 ? 'danger' : pct >= 70 ? 'warning' : '';
  const canChangeStatus = ['SCHEDULED', 'BOARDING', 'ACTIVE'].includes(t.status);
  const canClose = t.status === 'COMPLETED';
  const canCancel = !['CLOSED', 'CANCELLED'].includes(t.status);
  const canEdit = !['CLOSED', 'CANCELLED', 'COMPLETED'].includes(t.status);

  return `
<div class="trip-card ${t.status.toLowerCase()}" id="trip-card-${t.id}">
  <div class="trip-card-header">
    <div>
      <div style="display:flex;align-items:baseline;gap:10px;">
        <div class="trip-time">${t.departure_time}</div>
        <div class="trip-route">${routeLabel(t.route)}</div>
      </div>
      <div class="trip-meta">
        <span>👨‍✈️ ${driver ? driver.name : '—'}</span>
        <span>🚌 ${vehicle ? vehicle.model + ' [' + vehicle.plate + ']' : '—'}</span>
        <span>💺 ${t.price_seated} грн / 🧍 ${t.price_standing} грн</span>
      </div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;">
      <span class="badge ${statusBadge(t.status)}">${statusLabel(t.status)}</span>
      ${canChangeStatus ? `<button class="btn btn-ghost btn-sm" onclick="changeStatus(${t.id})">${statusNextLabel[t.status]}</button>` : ''}
    </div>
  </div>
  <div class="trip-stats">
    <div class="trip-stats-row">
      <span>Сидячих: <strong>${stats.seated} / ${t.seats_limit_snapshot}</strong>
        ${stats.waitlist > 0 ? `<span class="waitlist-badge">⏳ ${stats.waitlist} у черзі</span>` : ''}
      </span>
      <span style="color:var(--text-muted);font-size:12px;">Стоячі: ${stats.standing}/${t.standing_limit_snapshot} · Посилки: ${stats.parcels} · Виручка: <strong style="color:var(--green)">${stats.revenue} грн</strong></span>
    </div>
    <div class="progress-bar"><div class="progress-fill ${fillClass}" style="width:${pct}%"></div></div>
  </div>
  <div class="trip-actions">
    <button class="btn btn-blue btn-sm" onclick="openManifest(${t.id})">📋 Маніфест</button>
    ${canEdit ? `<button class="btn btn-ghost btn-sm" onclick="openEditTrip(${t.id})">✏️ Редагувати</button>` : ''}
    ${canClose ? `<button class="btn btn-success btn-sm" onclick="openCloseTrip(${t.id})">💰 Закрити рейс</button>` : ''}
    ${canCancel ? `<button class="btn btn-danger btn-sm" onclick="cancelTrip(${t.id})">Скасувати</button>` : ''}
  </div>
</div>`;
}

function changeStatus(tripId) {
  const t = trips.find(x => x.id === tripId);
  if (!t || !statusNext[t.status]) return;
  const next = statusNext[t.status];
  showConfirm('🚦', `Змінити статус рейсу?`,
    `${t.departure_time} ${routeLabel(t.route)}\n${statusLabel(t.status)} → ${statusLabel(next)}`, () => {
      t.status = next;
      if (next === 'COMPLETED') {
        // FIX: increment total_trips for BOARDED passengers, set NOSHOW for RESERVED/PAID
        bookings.filter(b => b.trip_id === tripId && b.status === 'BOARDED').forEach(b => {
          const p = passengers.find(x => x.id === b.passenger_id);
          if (p) p.total_trips++;
        });
        bookings.filter(b => b.trip_id === tripId && ['RESERVED', 'PAID'].includes(b.status)).forEach(b => {
          b.status = 'NOSHOW';
          const p = passengers.find(x => x.id === b.passenger_id);
          if (p) p.total_noshows++;
        });
        // FIX: notify waitlist passengers (mock)
        const waitlisted = bookings.filter(b => b.trip_id === tripId && b.status === 'WAITLIST');
        if (waitlisted.length > 0) {
          toast('info', `${waitlisted.length} пасажирів у черзі — рейс завершено без місць`);
        }
      }
      addAudit('STATUS_CHANGED', `${t.departure_time} ${routeLabel(t.route)}`, '—', 'WEB');
      toast('success', `Статус рейсу змінено: ${statusLabel(next)}`);
      renderSchedule();
    });
}

function cancelTrip(tripId) {
  const t = trips.find(x => x.id === tripId);
  showConfirm('⛔', 'Скасувати рейс?',
    `${t.departure_time} ${routeLabel(t.route)}\nВсі бронювання будуть скасовані. Telegram-сповіщення надіслані пасажирам.`, () => {
      t.status = 'CANCELLED';
      bookings.filter(b => b.trip_id === tripId && !['CANCELLED', 'NOSHOW'].includes(b.status)).forEach(b => b.status = 'CANCELLED');
      addAudit('TRIP_CANCELLED', `${t.departure_time} ${routeLabel(t.route)}`, '—', 'WEB');
      toast('error', 'Рейс скасовано. Пасажири сповіщені.');
      renderSchedule();
    });
}

// ── FIX #2: Edit Trip ──
function openEditTrip(tripId) {
  editingTripId = tripId;
  const t = trips.find(x => x.id === tripId);
  document.getElementById('edit-trip-modal-title').textContent = `✏️ Редагувати рейс — ${t.departure_time} ${routeLabel(t.route)}`;
  document.getElementById('et-route').value = t.route;
  document.getElementById('et-date').value = t.date;
  document.getElementById('et-time').value = t.departure_time;
  document.getElementById('et-arrival').value = t.arrival_time || '';
  document.getElementById('et-price-seated').value = t.price_seated;
  document.getElementById('et-price-standing').value = t.price_standing;

  const vs = document.getElementById('et-vehicle');
  vs.innerHTML = vehicles.filter(v => v.is_active).map(v =>
    `<option value="${v.id}" ${v.id === t.vehicle_id ? 'selected' : ''}>${v.model} [${v.plate}]</option>`
  ).join('');
  const ds = document.getElementById('et-driver');
  ds.innerHTML = drivers.map(d =>
    `<option value="${d.id}" ${d.id === t.driver_id ? 'selected' : ''}>${d.name}</option>`
  ).join('');
  openModal('modal-edit-trip');
}

function saveEditTrip() {
  const t = trips.find(x => x.id === editingTripId);
  if (!t) return;
  const oldDriverId = t.driver_id;
  const oldVehicleId = t.vehicle_id;

  t.route = document.getElementById('et-route').value;
  t.date = document.getElementById('et-date').value;
  t.departure_time = document.getElementById('et-time').value;
  t.arrival_time = document.getElementById('et-arrival').value;
  t.driver_id = parseInt(document.getElementById('et-driver').value);
  t.vehicle_id = parseInt(document.getElementById('et-vehicle').value);
  t.price_seated = parseFloat(document.getElementById('et-price-seated').value);
  t.price_standing = parseFloat(document.getElementById('et-price-standing').value);

  // Notify if driver or vehicle changed (mock)
  const changes = [];
  if (oldDriverId !== t.driver_id) {
    const newDriver = drivers.find(d => d.id === t.driver_id);
    changes.push(`водій → ${newDriver?.name}`);
  }
  if (oldVehicleId !== t.vehicle_id) {
    const newVehicle = vehicles.find(v => v.id === t.vehicle_id);
    changes.push(`авто → ${newVehicle?.model} [${newVehicle?.plate}]`);
  }
  if (changes.length > 0) {
    toast('info', `📢 Сповіщення надіслано пасажирам: ${changes.join(', ')}`);
  }

  addAudit('TRIP_EDITED', `${t.departure_time} ${routeLabel(t.route)}`, '—', 'WEB');
  closeModal('modal-edit-trip');
  editingTripId = null;
  toast('success', 'Рейс оновлено');
  renderSchedule();
}

// ══════════════════════════════════════════════
//  SCHEDULE WIZARD
// ══════════════════════════════════════════════
let wizardMode = 'single'; // 'single' | 'week' | 'weekend'
let wizardRows = [];

function openScheduleWizard() {
  wizardMode = 'single';
  document.getElementById('wizard-step-choose').style.display = 'block';
  document.getElementById('wizard-step-single').style.display = 'none';
  document.getElementById('wizard-step-template').style.display = 'none';
  openModal('modal-schedule-wizard');
}

function wizardSelectMode(mode) {
  wizardMode = mode;
  document.getElementById('wizard-step-choose').style.display = 'none';
  if (mode === 'single') {
    document.getElementById('wizard-step-single').style.display = 'block';
    document.getElementById('wizard-step-template').style.display = 'none';
    // Populate dropdowns for single
    populateWizardSingleDropdowns();
  } else {
    document.getElementById('wizard-step-single').style.display = 'none';
    document.getElementById('wizard-step-template').style.display = 'block';
    buildWizardTemplate(mode);
  }
}

function populateWizardSingleDropdowns() {
  const today = isoDate(TODAY);
  document.getElementById('sw-date').value = today;
  const vs = document.getElementById('sw-vehicle');
  vs.innerHTML = '<option value="">— Авто —</option>' + vehicles.filter(v => v.is_active).map(v =>
    `<option value="${v.id}">${v.model} [${v.plate}]</option>`).join('');
  const ds = document.getElementById('sw-driver');
  ds.innerHTML = '<option value="">— Водій —</option>' + drivers.map(d =>
    `<option value="${d.id}">${d.name}</option>`).join('');
}

function buildWizardTemplate(mode) {
  const startDate = new Date(TODAY);
  // For 'week' start from Monday, for 'weekend' start from next Saturday
  if (mode === 'week') {
    const dow = startDate.getDay();
    const diff = dow === 0 ? 1 : (dow === 6 ? 2 : 8 - dow);
    // Start from today for simplicity
  }

  const days = mode === 'week' ? 7 : 2;
  const routes = ['drohobych-lviv', 'lviv-drohobych'];
  wizardRows = [];

  for (let i = 0; i < days; i++) {
    const d = new Date(TODAY);
    d.setDate(d.getDate() + i);
    routes.forEach(route => {
      SCHEDULE_TEMPLATE[route].forEach(time => {
        wizardRows.push({
          date: isoDate(d),
          route,
          departure_time: time,
          driver_id: '',
          vehicle_id: '',
          price_seated: 120,
          price_standing: 80,
          enabled: true,
        });
      });
    });
  }

  renderWizardTable();
}

function renderWizardTable() {
  const container = document.getElementById('wizard-template-table');
  const vehicleOpts = vehicles.filter(v => v.is_active).map(v =>
    `<option value="${v.id}">${v.model} [${v.plate}]</option>`).join('');
  const driverOpts = drivers.map(d => `<option value="${d.id}">${d.name}</option>`).join('');

  container.innerHTML = `
    <div style="max-height:360px;overflow-y:auto;">
    <table style="width:100%;border-collapse:collapse;">
      <thead>
        <tr style="position:sticky;top:0;background:var(--surface2);z-index:1;">
          <th style="padding:8px;text-align:left;font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;">✓</th>
          <th style="padding:8px;text-align:left;font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;">Дата</th>
          <th style="padding:8px;text-align:left;font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;">Час</th>
          <th style="padding:8px;text-align:left;font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;">Маршрут</th>
          <th style="padding:8px;text-align:left;font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;">Водій</th>
          <th style="padding:8px;text-align:left;font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;">Авто</th>
        </tr>
      </thead>
      <tbody>
        ${wizardRows.map((row, i) => `
          <tr style="border-bottom:1px solid var(--border);opacity:${row.enabled ? 1 : 0.4};">
            <td style="padding:6px 8px;">
              <input type="checkbox" ${row.enabled ? 'checked' : ''} onchange="wizardToggleRow(${i}, this.checked)" style="accent-color:var(--accent);">
            </td>
            <td style="padding:6px 8px;font-size:12px;white-space:nowrap;">${row.date}</td>
            <td style="padding:6px 8px;font-size:13px;font-weight:700;">${row.departure_time}</td>
            <td style="padding:6px 8px;font-size:12px;">${routeLabel(row.route)}</td>
            <td style="padding:6px 8px;">
              <select class="form-select" style="padding:4px 6px;font-size:12px;" onchange="wizardRowUpdate(${i},'driver_id',this.value)">
                <option value="">—</option>${driverOpts}
              </select>
            </td>
            <td style="padding:6px 8px;">
              <select class="form-select" style="padding:4px 6px;font-size:12px;" onchange="wizardRowUpdate(${i},'vehicle_id',this.value)">
                <option value="">—</option>${vehicleOpts}
              </select>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    </div>
    <div style="margin-top:12px;font-size:12px;color:var(--text-muted);">
      Рейсів для створення: <strong style="color:var(--accent);">${wizardRows.filter(r => r.enabled).length}</strong>
    </div>
  `;
}

function wizardToggleRow(i, val) {
  wizardRows[i].enabled = val;
  renderWizardTable();
}

function wizardRowUpdate(i, field, val) {
  wizardRows[i][field] = val ? parseInt(val) : '';
}

function wizardSaveSingle() {
  const route = document.getElementById('sw-route').value;
  const date = document.getElementById('sw-date').value;
  const time = document.getElementById('sw-time').value;
  const arrival = document.getElementById('sw-arrival').value;
  const vehicleId = parseInt(document.getElementById('sw-vehicle').value);
  const driverId = parseInt(document.getElementById('sw-driver').value);
  const priceSeated = parseFloat(document.getElementById('sw-price-seated').value || 120);
  const priceStanding = parseFloat(document.getElementById('sw-price-standing').value || 80);
  if (!date || !time || !vehicleId || !driverId) { toast('error', 'Заповніть всі обов\'язкові поля'); return; }
  const conflict = trips.find(t => t.date === date &&
    (t.driver_id === driverId || t.vehicle_id === vehicleId) &&
    t.departure_time === time && t.status !== 'CANCELLED');
  if (conflict) { toast('error', '⚠️ Конфлікт: водій або авто вже призначені на цей час'); return; }
  const v = vehicles.find(x => x.id === vehicleId);
  trips.push({
    id: nextTripId++, driver_id: driverId, vehicle_id: vehicleId, route, date,
    departure_time: time, arrival_time: arrival, status: 'SCHEDULED',
    seats_limit_snapshot: v.total_seats, standing_limit_snapshot: v.total_standing,
    price_seated: priceSeated, price_standing: priceStanding, closed_by: null, cash_submitted: null
  });
  closeModal('modal-schedule-wizard');
  toast('success', 'Рейс створено!');
  renderSchedule();
}

function wizardSaveTemplate() {
  const rows = wizardRows.filter(r => r.enabled);
  const missing = rows.filter(r => !r.driver_id || !r.vehicle_id);
  if (missing.length > 0) {
    toast('error', `${missing.length} рейсів без водія або авто. Заповніть або зніміть галочку.`);
    return;
  }
  let created = 0;
  let conflicts = 0;
  rows.forEach(row => {
    const conflict = trips.find(t => t.date === row.date &&
      (t.driver_id === row.driver_id || t.vehicle_id === row.vehicle_id) &&
      t.departure_time === row.departure_time && t.status !== 'CANCELLED');
    if (conflict) { conflicts++; return; }
    const v = vehicles.find(x => x.id === row.vehicle_id);
    trips.push({
      id: nextTripId++, driver_id: row.driver_id, vehicle_id: row.vehicle_id,
      route: row.route, date: row.date, departure_time: row.departure_time,
      arrival_time: '', status: 'SCHEDULED',
      seats_limit_snapshot: v.total_seats, standing_limit_snapshot: v.total_standing,
      price_seated: row.price_seated, price_standing: row.price_standing,
      closed_by: null, cash_submitted: null
    });
    created++;
  });
  closeModal('modal-schedule-wizard');
  if (conflicts > 0) toast('error', `${conflicts} рейсів пропущено через конфлікти`);
  toast('success', `✅ Створено ${created} рейсів! PDF надіслано водіям.`);
  renderSchedule();
}

// ══════════════════════════════════════════════
//  MANIFEST
// ══════════════════════════════════════════════
function openManifest(tripId) {
  currentManifestTripId = tripId;
  const t = trips.find(x => x.id === tripId);
  const stats = getTripStats(tripId);
  document.getElementById('manifest-title').textContent = 'Маніфест рейсу';
  document.getElementById('manifest-subtitle').textContent = `${t.departure_time} | ${routeLabel(t.route)} | ${statusLabel(t.status)}`;
  updateManifestBadges(tripId);
  renderManifestList(tripId);
  document.getElementById('manifest-backdrop').style.display = 'block';
  document.getElementById('manifest-panel').classList.add('open');
}

function updateManifestBadges(tripId) {
  const t = trips.find(x => x.id === tripId);
  const stats = getTripStats(tripId);
  document.getElementById('manifest-seated-badge').textContent = `👤 ${stats.seated}/${t.seats_limit_snapshot} сид.`;
  document.getElementById('manifest-standing-badge').textContent = `🧍 ${stats.standing} стоячих`;
  document.getElementById('manifest-parcel-badge').textContent = `📦 ${stats.parcels} посилок`;
  const wlBadge = document.getElementById('manifest-waitlist-badge');
  if (stats.waitlist > 0) {
    wlBadge.textContent = `⏳ ${stats.waitlist} черга`;
    wlBadge.style.display = 'inline-flex';
  } else {
    wlBadge.style.display = 'none';
  }
}

function closeManifest() {
  document.getElementById('manifest-backdrop').style.display = 'none';
  document.getElementById('manifest-panel').classList.remove('open');
  currentManifestTripId = null;
}

function renderManifestList(tripId) {
  const b = bookings.filter(x => x.trip_id === tripId && x.status !== 'CANCELLED');
  const list = document.getElementById('manifest-passenger-list');
  if (b.length === 0) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><p>Список пасажирів порожній</p></div>`;
    return;
  }
  // Group: Active, Boarded, Waitlist, NoShow
  const groups = [
    { label: 'На борту', items: b.filter(x => x.status === 'BOARDED'), color: 'var(--green)' },
    { label: 'Заброньовано', items: b.filter(x => ['RESERVED', 'PAID'].includes(x.status)), color: 'var(--accent)' },
    { label: '⏳ Черга (Waitlist)', items: b.filter(x => x.status === 'WAITLIST'), color: 'var(--blue)' },
    { label: 'No-Show', items: b.filter(x => x.status === 'NOSHOW'), color: 'var(--text-dim)' },
  ];

  list.innerHTML = groups.map(g => {
    if (g.items.length === 0) return '';
    return `
      <div style="font-size:11px;font-weight:700;color:${g.color};text-transform:uppercase;letter-spacing:0.5px;padding:10px 0 6px;border-bottom:1px solid var(--border);margin-bottom:6px;">${g.label} (${g.items.length})</div>
      ${g.items.map(bk => renderBookingRow(bk)).join('')}
    `;
  }).join('');
}

function renderBookingRow(bk) {
  const p = bk.passenger_id ? passengers.find(x => x.id === bk.passenger_id) : null;
  const srcClass = { BOT: 'source-bot', PHONE: 'source-phone', DRIVER: 'source-driver', WEB: 'source-bot', INSTAGRAM: 'source-instagram' }[bk.source] || '';
  const statusClass = { RESERVED: 'status-reserved', BOARDED: 'status-boarded', PAID: 'status-reserved', NOSHOW: 'status-noshow', CANCELLED: 'status-cancelled', WAITLIST: 'status-waitlist' }[bk.status] || '';
  const typeLabel = { SEATED: 'Сидяче', STANDING: 'Стояче', PARCEL: '📦 Посилка' }[bk.booking_type];
  const name = p ? p.full_name : bk.booking_type === 'PARCEL' ? 'Посилка' : 'Стоячий';
  const phone = p ? p.phone : '—';

  let actions = '';
  if (['RESERVED', 'PAID'].includes(bk.status)) {
    actions = `
      <button class="btn btn-ghost btn-sm" onclick="openEditBooking(${bk.id})" title="Редагувати">✏️</button>
      <button class="btn btn-danger btn-sm" onclick="cancelBooking(${bk.id})">✕</button>
    `;
  }
  if (bk.status === 'WAITLIST') {
    actions = `<button class="btn btn-success btn-sm" onclick="promoteFromWaitlist(${bk.id})">→ Підтвердити</button>`;
  }

  return `
<div class="passenger-row" id="booking-row-${bk.id}">
  <div style="flex:1;min-width:0;">
    <div class="passenger-name">${name} <span class="passenger-source ${srcClass}">${bk.source}</span>
      ${bk.comment ? `<span style="font-size:11px;color:var(--text-muted);font-weight:400;"> · ${bk.comment}</span>` : ''}
    </div>
    <div class="passenger-phone">${phone} · ${typeLabel}${bk.passengers_count > 1 ? ' ×' + bk.passengers_count : ''}</div>
  </div>
  <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
    <span class="passenger-status ${statusClass}">${bk.status}</span>
    ${actions}
  </div>
</div>`;
}

// FIX #3: Edit booking (change seats / move to another trip)
let editingBookingId = null;
function openEditBooking(bookingId) {
  editingBookingId = bookingId;
  const bk = bookings.find(x => x.id === bookingId);
  const p = bk.passenger_id ? passengers.find(x => x.id === bk.passenger_id) : null;

  document.getElementById('eb-passenger-name').textContent = p ? p.full_name : '—';
  document.getElementById('eb-seats').value = bk.passengers_count;
  // Populate target trip dropdown
  const td = document.getElementById('eb-target-trip');
  td.innerHTML = `<option value="${bk.trip_id}" selected>Поточний рейс (без змін)</option>` +
    trips.filter(t => t.id !== bk.trip_id && !['CANCELLED', 'CLOSED', 'COMPLETED'].includes(t.status))
      .map(t => `<option value="${t.id}">${t.date} ${t.departure_time} ${routeLabel(t.route)}</option>`)
      .join('');
  openModal('modal-edit-booking');
}

function saveEditBooking() {
  const bk = bookings.find(x => x.id === editingBookingId);
  if (!bk) return;
  const newSeats = parseInt(document.getElementById('eb-seats').value);
  const newTripId = parseInt(document.getElementById('eb-target-trip').value);

  if (newTripId !== bk.trip_id) {
    // Move to another trip — check capacity
    const targetTrip = trips.find(t => t.id === newTripId);
    const targetStats = getTripStats(newTripId);
    if (targetStats.seated + newSeats > targetTrip.seats_limit_snapshot) {
      toast('error', 'Недостатньо місць на цільовому рейсі'); return;
    }
    const oldTripId = bk.trip_id;
    bk.trip_id = newTripId;
    bk.amount_paid = targetTrip.price_seated * newSeats;
    toast('success', `Пасажира перенесено на ${targetTrip.departure_time} ${routeLabel(targetTrip.route)}. Telegram-сповіщення надіслано.`);
    addAudit('BOOKING_MOVED', `→ ${targetTrip.departure_time} ${routeLabel(targetTrip.route)}`,
      bk.passenger_id ? passengers.find(p => p.id === bk.passenger_id)?.full_name : '—', 'WEB');
    if (currentManifestTripId === oldTripId || currentManifestTripId === newTripId) {
      renderManifestList(currentManifestTripId);
      updateManifestBadges(currentManifestTripId);
    }
  }
  bk.passengers_count = newSeats;
  closeModal('modal-edit-booking');
  editingBookingId = null;
  renderSchedule();
  if (currentManifestTripId) {
    renderManifestList(currentManifestTripId);
    updateManifestBadges(currentManifestTripId);
  }
  toast('success', 'Бронювання оновлено');
}

// FIX #4: Promote from waitlist
function promoteFromWaitlist(bookingId) {
  const bk = bookings.find(x => x.id === bookingId);
  const t = trips.find(x => x.id === bk.trip_id);
  const stats = getTripStats(bk.trip_id);
  if (stats.seated + bk.passengers_count > t.seats_limit_snapshot) {
    toast('error', 'Місць недостатньо для переведення з черги'); return;
  }
  bk.status = 'RESERVED';
  bk.amount_paid = t.price_seated * bk.passengers_count;
  const p = passengers.find(x => x.id === bk.passenger_id);
  toast('success', `${p?.full_name || 'Пасажир'} переведено з черги → RESERVED. Telegram-сповіщення надіслано.`);
  addAudit('WAITLIST_PROMOTED', `${t.departure_time} ${routeLabel(t.route)}`, p?.full_name || '—', 'WEB');
  renderManifestList(bk.trip_id);
  updateManifestBadges(bk.trip_id);
  renderSchedule();
}

function cancelBooking(bookingId) {
  showConfirm('❌', 'Скасувати бронювання?', 'Місце звільниться для нових пасажирів.', () => {
    const bk = bookings.find(x => x.id === bookingId);
    if (bk) bk.status = 'CANCELLED';
    toast('info', 'Бронювання скасовано');
    if (currentManifestTripId) {
      renderManifestList(currentManifestTripId);
      updateManifestBadges(currentManifestTripId);
    }
    renderSchedule();
  });
}

function addPassengerFromManifest() {
  const phone = document.getElementById('manifest-phone').value.trim();
  const seats = parseInt(document.getElementById('manifest-seats').value);
  // FIX #5: source selection (PHONE / INSTAGRAM)
  const source = document.getElementById('manifest-source').value;
  const t = trips.find(x => x.id === currentManifestTripId);
  if (!phone) { toast('error', 'Введіть номер телефону'); return; }
  if (!t) return;

  const stats = getTripStats(currentManifestTripId);
  const seatsLeft = t.seats_limit_snapshot - stats.seated;

  // FIX: waitlist if no seats
  if (seatsLeft <= 0) {
    showConfirm('⏳', 'Місць немає — додати в чергу?',
      `Пасажир буде доданий у Waitlist. При звільненні місця диспетчер зможе перевести його вручну.`, () => {
        let p = passengers.find(x => x.phone === phone);
        if (!p) {
          const nameInput = document.getElementById('manifest-passenger-name').value.trim();
          if (!nameInput) {
            document.getElementById('manifest-shadow-name-row').style.display = 'block';
            document.getElementById('manifest-passenger-name').focus();
            toast('info', 'Введіть ім\'я нового пасажира');
            return;
          }
          p = { id: nextPassengerId++, full_name: nameInput, phone, telegram_id: null, is_active: true, created_at: isoDate(TODAY), total_trips: 0, total_noshows: 0 };
          passengers.push(p);
        }
        bookings.push({
          id: nextBookingId++, trip_id: currentManifestTripId, passenger_id: p.id,
          created_by_id: 10, booking_type: 'SEATED', source, status: 'WAITLIST',
          passengers_count: seats, amount_paid: 0, created_at: new Date().toISOString(),
          validated_by_id: null, validated_at: null, comment: null
        });
        document.getElementById('manifest-phone').value = '';
        toast('info', `${p.full_name} доданий у чергу (Waitlist)`);
        renderManifestList(currentManifestTripId);
        updateManifestBadges(currentManifestTripId);
        renderSchedule();
      }
    );
    return;
  }

  if (seatsLeft < seats) {
    toast('error', `Доступно лише ${seatsLeft} місць. Змініть кількість.`); return;
  }

  let p = passengers.find(x => x.phone === phone);
  if (!p) {
    const nameInput = document.getElementById('manifest-passenger-name').value.trim();
    if (!nameInput) {
      document.getElementById('manifest-shadow-name-row').style.display = 'block';
      document.getElementById('manifest-passenger-name').focus();
      toast('info', 'Введіть ім\'я нового пасажира (тіньовий профіль)');
      return;
    }
    p = { id: nextPassengerId++, full_name: nameInput, phone, telegram_id: null, is_active: true, created_at: isoDate(TODAY), total_trips: 0, total_noshows: 0 };
    passengers.push(p);
    toast('info', `Створено тіньовий профіль для ${nameInput}`);
    document.getElementById('manifest-shadow-name-row').style.display = 'none';
    document.getElementById('manifest-passenger-name').value = '';
  }

  bookings.push({
    id: nextBookingId++, trip_id: currentManifestTripId, passenger_id: p.id,
    created_by_id: 10, booking_type: 'SEATED', source, status: 'RESERVED',
    passengers_count: seats, amount_paid: t.price_seated * seats,
    created_at: new Date().toISOString(), validated_by_id: null, validated_at: null, comment: null
  });
  document.getElementById('manifest-phone').value = '';
  addAudit('BOOKING_CREATED', `${t.departure_time} ${routeLabel(t.route)}`, p.full_name, source);
  toast('success', `Бронювання додано для ${p.full_name}`);
  renderManifestList(currentManifestTripId);
  updateManifestBadges(currentManifestTripId);
  renderSchedule();
}

// ══════════════════════════════════════════════
//  CRM
// ══════════════════════════════════════════════
function renderCRM() {
  const search = document.getElementById('crm-search').value.toLowerCase();
  const statusF = document.getElementById('crm-filter-status').value;
  const sortF = document.getElementById('crm-sort').value;
  let list = [...passengers];
  if (search) list = list.filter(p => p.full_name.toLowerCase().includes(search) || p.phone.includes(search));
  if (statusF === 'active') list = list.filter(p => p.is_active);
  if (statusF === 'blocked') list = list.filter(p => !p.is_active);
  if (sortF === 'name') list.sort((a, b) => a.full_name.localeCompare(b.full_name, 'uk'));
  if (sortF === 'trust_asc') list.sort((a, b) => trustScore(a) - trustScore(b));
  if (sortF === 'trust_desc') list.sort((a, b) => trustScore(b) - trustScore(a));
  if (sortF === 'noshows') list.sort((a, b) => b.total_noshows - a.total_noshows);
  const tbody = document.getElementById('crm-tbody');
  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);">Пасажирів не знайдено</td></tr>`;
    return;
  }
  tbody.innerHTML = list.map(p => {
    const ts = trustScore(p);
    const tsClass = ts >= 75 ? 'high' : ts >= 50 ? 'mid' : 'low';
    const tsColor = ts >= 75 ? 'var(--green)' : ts >= 50 ? 'var(--orange)' : 'var(--red)';
    const tgBadge = p.telegram_id
      ? `<span style="background:var(--blue-dim);color:var(--blue);font-size:10px;padding:1px 5px;border-radius:3px;font-weight:700;">TG</span>`
      : `<span style="background:var(--orange-dim);color:var(--orange);font-size:10px;padding:1px 5px;border-radius:3px;font-weight:700;">Тіньовий</span>`;
    return `<tr>
      <td><div style="font-weight:700;">${p.full_name} ${tgBadge}</div></td>
      <td style="font-size:12px;color:var(--text-muted);">${p.phone}</td>
      <td style="font-size:13px;"><strong>${p.total_trips}</strong> / <span style="color:${p.total_noshows > 0 ? 'var(--red)' : 'var(--text-muted)'};">${p.total_noshows} no-show</span></td>
      <td>
        <div class="trust-bar">
          <div class="trust-mini-bar"><div class="trust-mini-fill" style="width:${ts}%;background:${tsColor};"></div></div>
          <div class="trust-score ${tsClass}">${ts}</div>
        </div>
      </td>
      <td>${p.is_active ? '<span class="badge badge-active">Активний</span>' : '<span class="badge badge-cancelled">Заблокований</span>'}</td>
      <td style="font-size:12px;color:var(--text-muted);">${p.created_at}</td>
      <td>
        <div style="display:flex;gap:6px;">
          <button class="btn btn-ghost btn-sm" onclick="viewPassenger(${p.id})">Деталі</button>
          ${p.is_active
            ? `<button class="btn btn-danger btn-sm" onclick="blockPassenger(${p.id})">Блок</button>`
            : `<button class="btn btn-success btn-sm" onclick="unblockPassenger(${p.id})">Розблок.</button>`}
        </div>
      </td>
    </tr>`;
  }).join('');
}

function blockPassenger(id) {
  const p = passengers.find(x => x.id === id);
  showConfirm('🚫', `Заблокувати пасажира?`,
    `${p.full_name}\n${p.phone}\n\nПасажир не зможе бронювати місця.`, () => {
      p.is_active = false;
      toast('error', `${p.full_name} заблокований`);
      renderCRM();
    });
}

function unblockPassenger(id) {
  const p = passengers.find(x => x.id === id);
  p.is_active = true;
  toast('success', `${p.full_name} розблокований`);
  renderCRM();
}

function viewPassenger(id) {
  const p = passengers.find(x => x.id === id);
  const ts = trustScore(p);
  const tsColor = ts >= 75 ? 'var(--green)' : ts >= 50 ? 'var(--orange)' : 'var(--red)';
  const pBookings = bookings.filter(b => b.passenger_id === id);
  document.getElementById('modal-passenger-body').innerHTML = `
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;padding:16px;background:var(--surface2);border-radius:var(--radius-sm);">
      <div style="width:56px;height:56px;border-radius:50%;background:var(--bg);border:2px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:900;color:var(--accent);">${p.full_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}</div>
      <div>
        <div style="font-size:18px;font-weight:900;">${p.full_name}</div>
        <div style="font-size:13px;color:var(--text-muted);">${p.phone}</div>
        <div style="margin-top:4px;">${p.telegram_id
          ? '<span style="background:var(--blue-dim);color:var(--blue);font-size:11px;padding:2px 7px;border-radius:4px;font-weight:700;">Telegram</span>'
          : '<span style="background:var(--orange-dim);color:var(--orange);font-size:11px;padding:2px 7px;border-radius:4px;font-weight:700;">Тіньовий профіль</span>'}</div>
      </div>
    </div>
    <div class="form-row-3" style="margin-bottom:16px;">
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px;text-align:center;">
        <div style="font-size:28px;font-weight:900;font-family:'Bebas Neue',sans-serif;">${p.total_trips}</div>
        <div style="font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;">Поїздок</div>
      </div>
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px;text-align:center;">
        <div style="font-size:28px;font-weight:900;font-family:'Bebas Neue',sans-serif;color:${p.total_noshows > 0 ? 'var(--red)' : 'inherit'};">${p.total_noshows}</div>
        <div style="font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;">No-Show</div>
      </div>
      <div style="background:var(--surface2);border:1px solid ${tsColor};border-radius:var(--radius-sm);padding:14px;text-align:center;">
        <div style="font-size:28px;font-weight:900;font-family:'Bebas Neue',sans-serif;color:${tsColor};">${ts}</div>
        <div style="font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;">Trust Score</div>
      </div>
    </div>
    <div style="font-size:12px;color:var(--text-muted);font-weight:700;text-transform:uppercase;margin-bottom:8px;">Остання активність</div>
    ${pBookings.slice(-3).reverse().map(bk => {
      const trip = trips.find(t => t.id === bk.trip_id);
      return `<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);font-size:13px;">
        <span>${trip ? trip.departure_time + ' ' + routeLabel(trip.route) : '—'}</span>
        <span class="passenger-status ${bk.status === 'BOARDED' ? 'status-boarded' : bk.status === 'NOSHOW' ? 'status-noshow' : 'status-reserved'}">${bk.status}</span>
      </div>`;
    }).join('') || '<div style="color:var(--text-muted);font-size:13px;padding:8px 0;">Бронювань не знайдено</div>'}
  `;
  document.getElementById('modal-passenger-footer').innerHTML = `
    <button class="btn btn-ghost" onclick="closeModal('modal-passenger')">Закрити</button>
    ${p.is_active
      ? `<button class="btn btn-danger" onclick="blockPassenger(${id});closeModal('modal-passenger');renderCRM();">Заблокувати</button>`
      : `<button class="btn btn-success" onclick="unblockPassenger(${id});closeModal('modal-passenger');renderCRM();">Розблокувати</button>`}
  `;
  openModal('modal-passenger');
}

// ══════════════════════════════════════════════
//  FINANCE
// ══════════════════════════════════════════════
function renderFinance() {
  const allRevenue = bookings.filter(b => !['CANCELLED', 'NOSHOW', 'WAITLIST'].includes(b.status)).reduce((a, b) => a + (b.amount_paid || 0), 0);
  const todayTrips = trips.filter(t => t.date === isoDate(TODAY));
  const todayRevenue = todayTrips.reduce((a, t) => { const s = getTripStats(t.id); return a + s.revenue; }, 0);
  const pendingClose = trips.filter(t => t.status === 'COMPLETED').length;

  document.getElementById('finance-stats').innerHTML = `
    <div class="stat-card accent"><div class="stat-label">Виручка сьогодні</div><div class="stat-value" style="color:var(--accent);">${todayRevenue}</div><div class="stat-sub">грн</div></div>
    <div class="stat-card green"><div class="stat-label">Загальна виручка</div><div class="stat-value" style="color:var(--green);">${allRevenue}</div><div class="stat-sub">грн</div></div>
    <div class="stat-card blue"><div class="stat-label">Рейсів сьогодні</div><div class="stat-value" style="color:var(--blue);">${todayTrips.length}</div><div class="stat-sub">рейсів</div></div>
    <div class="stat-card red"><div class="stat-label">Очік. закриття</div><div class="stat-value" style="color:var(--red);">${pendingClose}</div><div class="stat-sub">рейсів</div></div>
  `;

  const pending = trips.filter(t => t.status === 'COMPLETED');
  const pc = document.getElementById('pending-close-container');
  if (pending.length === 0) {
    pc.innerHTML = `<div class="empty-state"><div class="empty-icon">✅</div><p>Усі рейси закриті</p></div>`;
  } else {
    pc.innerHTML = pending.map(t => {
      const stats = getTripStats(t.id);
      const driver = drivers.find(d => d.id === t.driver_id);
      const vehicle = vehicles.find(v => v.id === t.vehicle_id);
      return `<div class="trip-card completed" style="margin-bottom:12px;">
        <div class="trip-card-header">
          <div>
            <div style="display:flex;align-items:baseline;gap:10px;"><div class="trip-time">${t.departure_time}</div><div class="trip-route">${routeLabel(t.route)} · ${t.date}</div></div>
            <div class="trip-meta"><span>👨‍✈️ ${driver?.name || '—'}</span><span>🚌 ${vehicle?.plate || '—'}</span></div>
          </div>
          <span class="badge badge-completed">Завершено</span>
        </div>
        <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px;margin-bottom:14px;">
          <div class="finance-row"><span class="finance-label">Сидячих (BOARDED/RESERVED)</span><span class="finance-value">${stats.seated}</span></div>
          <div class="finance-row"><span class="finance-label">Стоячих</span><span class="finance-value">${stats.standing}</span></div>
          <div class="finance-row"><span class="finance-label">Посилок</span><span class="finance-value">${stats.parcels}</span></div>
          <div class="finance-row"><span class="finance-label">Розрахункова виручка</span><span class="finance-value green">${stats.revenue} грн</span></div>
        </div>
        <button class="btn btn-success" onclick="openCloseTrip(${t.id})">💰 Закрити рейс (фінансово)</button>
      </div>`;
    }).join('');
  }

  const closed = trips.filter(t => t.status === 'CLOSED');
  document.getElementById('closed-trips-tbody').innerHTML = closed.length === 0
    ? `<tr><td colspan="10" style="text-align:center;padding:30px;color:var(--text-muted);">Закритих рейсів немає</td></tr>`
    : closed.map(t => {
      const stats = getTripStats(t.id);
      const driver = drivers.find(d => d.id === t.driver_id);
      const vehicle = vehicles.find(v => v.id === t.vehicle_id);
      const cashDiff = t.cash_submitted != null ? (t.cash_submitted - stats.revenue) : null;
      const diffStr = cashDiff != null
        ? `<span style="color:${cashDiff >= 0 ? 'var(--green)' : 'var(--red)'};">${cashDiff >= 0 ? '+' : ''}${cashDiff} грн</span>`
        : '—';
      return `<tr>
        <td style="font-size:12px;">${t.date}</td>
        <td style="font-weight:700;">${t.departure_time} ${routeLabel(t.route)}</td>
        <td style="font-size:12px;">${driver?.name || '—'}</td>
        <td style="font-size:12px;">${vehicle?.plate || '—'}</td>
        <td>${stats.seated}</td><td>${stats.standing}</td><td>${stats.parcels}</td>
        <td style="color:var(--green);font-weight:700;">${stats.revenue} грн</td>
        <td>${t.cash_submitted != null ? t.cash_submitted + ' грн' : '—'}</td>
        <td>${diffStr}</td>
        <td style="font-size:12px;color:var(--text-muted);">${t.closed_by || 'Система'}</td>
      </tr>`;
    }).join('');

  document.getElementById('audit-tbody').innerHTML = auditLog.map(a => {
    const srcColor = { BOT: 'var(--blue)', PHONE: 'var(--orange)', DRIVER: 'var(--green)', SYSTEM: 'var(--text-dim)', WEB: 'var(--purple)', INSTAGRAM: 'var(--purple)' }[a.source] || 'var(--text-muted)';
    return `<tr>
      <td style="font-size:11px;color:var(--text-muted);white-space:nowrap;">${a.time}</td>
      <td><span style="font-weight:700;font-size:12px;">${a.action}</span></td>
      <td style="font-size:12px;">${a.trip}</td>
      <td style="font-size:12px;">${a.passenger}</td>
      <td><span style="font-size:11px;font-weight:700;color:${srcColor};">${a.source}</span></td>
      <td style="font-size:12px;color:var(--text-muted);">${a.by}</td>
    </tr>`;
  }).join('');
}

function openCloseTrip(tripId) {
  pendingCloseId = tripId;
  const t = trips.find(x => x.id === tripId);
  const stats = getTripStats(tripId);
  const driver = drivers.find(d => d.id === t.driver_id);
  document.getElementById('close-trip-summary').innerHTML = `
    <div style="font-weight:700;font-size:15px;margin-bottom:12px;">${t.departure_time} · ${routeLabel(t.route)} · ${t.date}</div>
    <div class="finance-row"><span class="finance-label">Водій</span><span class="finance-value">${driver?.name || '—'}</span></div>
    <div class="finance-row"><span class="finance-label">Сидячих пасажирів</span><span class="finance-value">${stats.seated}</span></div>
    <div class="finance-row"><span class="finance-label">Стоячих пасажирів</span><span class="finance-value">${stats.standing}</span></div>
    <div class="finance-row"><span class="finance-label">Посилок</span><span class="finance-value">${stats.parcels}</span></div>
    <div class="finance-row"><span class="finance-label" style="font-weight:900;">Розрахункова виручка</span><span class="finance-value green" style="font-size:18px;">${stats.revenue} грн</span></div>
  `;
  // FIX #6: Reset cash input
  document.getElementById('ct-cash-submitted').value = '';
  document.getElementById('ct-cash-diff').textContent = '';
  openModal('modal-close-trip');
}

// FIX #6: Live cash diff calculation
document.getElementById('ct-cash-submitted').addEventListener('input', function () {
  if (!pendingCloseId) return;
  const t = trips.find(x => x.id === pendingCloseId);
  const stats = getTripStats(pendingCloseId);
  const cash = parseFloat(this.value);
  const el = document.getElementById('ct-cash-diff');
  if (!isNaN(cash)) {
    const diff = cash - stats.revenue;
    el.textContent = diff === 0 ? '✅ Збіг' : diff > 0 ? `+${diff} грн надлишок` : `${diff} грн недостача`;
    el.style.color = diff >= 0 ? 'var(--green)' : 'var(--red)';
  } else {
    el.textContent = '';
  }
});

function confirmCloseTrip() {
  if (!pendingCloseId) return;
  const t = trips.find(x => x.id === pendingCloseId);
  const cashVal = document.getElementById('ct-cash-submitted').value;
  t.status = 'CLOSED';
  t.closed_by = document.getElementById('current-user-name').textContent;
  t.cash_submitted = cashVal ? parseFloat(cashVal) : null;
  bookings.filter(b => b.trip_id === pendingCloseId && ['RESERVED', 'PAID'].includes(b.status)).forEach(b => {
    b.status = 'NOSHOW';
    const p = passengers.find(x => x.id === b.passenger_id);
    if (p) p.total_noshows++;
  });
  addAudit('TRIP_CLOSED', `${t.departure_time} ${routeLabel(t.route)}`, '—', 'WEB');
  closeModal('modal-close-trip');
  pendingCloseId = null;
  toast('success', '✅ Рейс фінансово закрито');
  renderFinance();
  renderSchedule();
}

function exportCSV() {
  const rows = [['Дата', 'Маршрут', 'Водій', 'Сид.', 'Стоячі', 'Посилки', 'Розрахункова', 'Здана', 'Різниця', 'Статус']];
  trips.forEach(t => {
    const stats = getTripStats(t.id);
    const driver = drivers.find(d => d.id === t.driver_id);
    const diff = t.cash_submitted != null ? (t.cash_submitted - stats.revenue) : '';
    rows.push([t.date, routeLabel(t.route), driver?.name || '—', stats.seated, stats.standing, stats.parcels, stats.revenue, t.cash_submitted ?? '', diff, t.status]);
  });
  const csv = rows.map(r => r.join(',')).join('\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURIComponent(csv);
  a.download = 'trips_report.csv'; a.click();
  toast('success', 'CSV завантажено');
}

// ══════════════════════════════════════════════
//  VEHICLES
// ══════════════════════════════════════════════
function renderVehicles() {
  document.getElementById('vehicles-grid').innerHTML = vehicles.map(v => `
    <div class="vehicle-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
        <div class="vehicle-plate">${v.plate}</div>
        <span class="vehicle-status ${v.is_active ? 'active' : 'inactive'}">${v.is_active ? '● Активний' : '● Неактивний'}</span>
      </div>
      <div class="vehicle-model">${v.model}</div>
      <div class="vehicle-seats">
        <span class="seat-chip seated">💺 ${v.total_seats} сидячих</span>
        <span class="seat-chip standing">🧍 ${v.total_standing} стоячих</span>
      </div>
      <div style="display:flex;gap:8px;margin-top:4px;">
        <button class="btn btn-ghost btn-sm" style="flex:1;" onclick="editVehicle(${v.id})">✏️ Редагувати</button>
        ${v.is_active
          ? `<button class="btn btn-danger btn-sm" onclick="toggleVehicle(${v.id})">Деактивувати</button>`
          : `<button class="btn btn-success btn-sm" onclick="toggleVehicle(${v.id})">Активувати</button>`}
      </div>
    </div>
  `).join('');
}

function editVehicle(id) {
  const v = vehicles.find(x => x.id === id);
  document.getElementById('vehicle-modal-title').textContent = 'Редагувати ТЗ';
  document.getElementById('av-edit-id').value = id;
  document.getElementById('av-plate').value = v.plate;
  document.getElementById('av-model').value = v.model;
  document.getElementById('av-seats').value = v.total_seats;
  document.getElementById('av-standing').value = v.total_standing;
  openModal('modal-add-vehicle');
}

function saveVehicle() {
  const editId = document.getElementById('av-edit-id').value;
  const plate = document.getElementById('av-plate').value.trim();
  const model = document.getElementById('av-model').value.trim();
  const seats = parseInt(document.getElementById('av-seats').value);
  const standing = parseInt(document.getElementById('av-standing').value);
  if (!plate || !model || !seats) { toast('error', 'Заповніть всі поля'); return; }
  if (editId) {
    const v = vehicles.find(x => x.id === parseInt(editId));
    v.plate = plate; v.model = model; v.total_seats = seats; v.total_standing = standing;
    toast('info', 'ТЗ оновлено (snapshot існуючих рейсів не змінено)');
  } else {
    vehicles.push({ id: Date.now(), plate, model, total_seats: seats, total_standing: standing, is_active: true });
    toast('success', 'Транспортний засіб додано');
  }
  document.getElementById('av-edit-id').value = '';
  document.getElementById('vehicle-modal-title').textContent = 'Додати транспортний засіб';
  closeModal('modal-add-vehicle');
  renderVehicles();
  populateCreateTripDropdowns();
}

function toggleVehicle(id) {
  const v = vehicles.find(x => x.id === id);
  const futureTripWithVehicle = trips.find(t => t.vehicle_id === id && t.date >= isoDate(TODAY) && !['CANCELLED', 'CLOSED'].includes(t.status));
  if (v.is_active && futureTripWithVehicle) {
    showConfirm('⚠️', 'Деактивувати ТЗ?',
      `Є заплановані рейси з цим транспортним засобом (${futureTripWithVehicle.departure_time} ${routeLabel(futureTripWithVehicle.route)}). Перепризначте водія перед деактивацією.`,
      () => { v.is_active = false; toast('info', 'ТЗ деактивовано'); renderVehicles(); });
  } else {
    v.is_active = !v.is_active;
    toast(v.is_active ? 'success' : 'info', v.is_active ? 'ТЗ активовано' : 'ТЗ деактивовано');
    renderVehicles();
  }
}

function populateCreateTripDropdowns() {
  // Used by wizard single form
  const vs = document.getElementById('sw-vehicle');
  if (vs) {
    vs.innerHTML = '<option value="">— Оберіть авто —</option>' +
      vehicles.filter(v => v.is_active).map(v =>
        `<option value="${v.id}">${v.model} [${v.plate}] · ${v.total_seats}+${v.total_standing}</option>`).join('');
  }
  const ds = document.getElementById('sw-driver');
  if (ds) {
    ds.innerHTML = '<option value="">— Оберіть водія —</option>' +
      drivers.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
  }
}

// ══════════════════════════════════════════════
//  BROADCAST
// ══════════════════════════════════════════════
function renderBroadcast() {
  const tripSelect = document.getElementById('broadcast-trip-select');
  tripSelect.innerHTML = `<option value="all">📢 Усі активні пасажири (${passengers.filter(p => p.telegram_id && p.is_active).length} TG)</option>` +
    trips.filter(t => !['CLOSED', 'CANCELLED'].includes(t.status)).map(t => {
      const stats = getTripStats(t.id);
      return `<option value="${t.id}">${t.date} ${t.departure_time} ${routeLabel(t.route)} · ${stats.seated} пас.</option>`;
    }).join('');
  renderBroadcastPreview();
}

function renderBroadcastPreview() {
  const target = document.getElementById('broadcast-trip-select').value;
  const text = document.getElementById('broadcast-text').value;
  let count = 0;
  if (target === 'all') {
    count = passengers.filter(p => p.telegram_id && p.is_active).length;
  } else {
    const tripId = parseInt(target);
    count = bookings.filter(b => b.trip_id === tripId && ['RESERVED', 'PAID', 'BOARDED'].includes(b.status) && b.passenger_id)
      .map(b => passengers.find(p => p.id === b.passenger_id))
      .filter(p => p && p.telegram_id).length;
  }
  document.getElementById('broadcast-preview-count').textContent = `Отримувачів: ${count} Telegram-акаунтів`;
  document.getElementById('broadcast-preview-text').textContent = text || '(текст не введено)';
}

function sendBroadcast() {
  const text = document.getElementById('broadcast-text').value.trim();
  if (!text) { toast('error', 'Введіть текст повідомлення'); return; }
  const countEl = document.getElementById('broadcast-preview-count').textContent;
  showConfirm('📢', 'Надіслати розсилку?', `${countEl}\n\n"${text.slice(0, 80)}${text.length > 80 ? '...' : ''}"`, () => {
    document.getElementById('broadcast-text').value = '';
    renderBroadcastPreview();
    toast('success', `✅ Розсилку надіслано! ${countEl}`);
    addAudit('BROADCAST_SENT', '—', `(${countEl})`, 'WEB');
  });
}

// ══════════════════════════════════════════════
//  MODALS
// ══════════════════════════════════════════════
function openModal(id) {
  document.getElementById(id).classList.add('open');
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}
document.querySelectorAll('.modal-backdrop').forEach(bd => {
  bd.addEventListener('click', (e) => { if (e.target === bd) bd.classList.remove('open'); });
});

function showConfirm(icon, title, msg, cb) {
  document.getElementById('confirm-icon').textContent = icon;
  document.getElementById('confirm-title').textContent = title;
  document.getElementById('confirm-msg').textContent = msg;
  pendingConfirmCb = cb;
  openModal('confirm-modal');
}
document.getElementById('confirm-ok-btn').addEventListener('click', () => {
  if (pendingConfirmCb) { pendingConfirmCb(); pendingConfirmCb = null; }
  closeModal('confirm-modal');
});

// ══════════════════════════════════════════════
//  TOAST
// ══════════════════════════════════════════════
function toast(type, msg) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const tc = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${msg}</span>`;
  tc.appendChild(el);
  setTimeout(() => {
    el.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

// ══════════════════════════════════════════════
//  KEYBOARD SHORTCUTS
// ══════════════════════════════════════════════
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'n') { e.preventDefault(); openScheduleWizard(); }
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop.open').forEach(m => m.classList.remove('open'));
    closeManifest();
  }
});

// ══════════════════════════════════════════════
//  LOGOUT
// ══════════════════════════════════════════════
function handleLogout() {
  showConfirm('👋', 'Вийти з системи?', 'Поточна сесія буде завершена.', () => toast('info', 'Вихід із системи...'));
}

// ══════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════
function init() {
  const today = isoDate(TODAY);
  document.getElementById('finance-date-from').value = today;
  document.getElementById('finance-date-to').value = today;
  populateCreateTripDropdowns();
  renderSchedule();
}

init();