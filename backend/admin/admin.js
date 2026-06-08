/**
 * DROGOBYCH EXPRESS TAXI - Admin Panel Logic
 * Fully integrated with Backend API
 */

const API_BASE = '/api/admin';

// STATE
let currentDayOffset = 0;
let trips = [];
let users = [];
let vehicles = [];
let locations = [];
let stats = {};

// UTILS
const formatDate = (d) => {
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    return `${dd}.${mm}.${d.getFullYear()}`;
};

const getDateForOffset = (offset) => {
    const d = new Date();
    d.setDate(d.getDate() + offset);
    return d;
};

const routeLabel = (trip) => {
    if (!trip.from_location || !trip.to_location) return '—';
    return `${trip.from_location.name} → ${trip.to_location.name}`;
};

const statusLabel = (s) => ({
    SCHEDULED: 'Заплановано', BOARDING: 'Посадка', ACTIVE: 'В дорозі',
    COMPLETED: 'Завершено', CLOSED: 'Закрито', CANCELLED: 'Скасовано'
}[s] || s);

const statusBadge = (s) => `badge-${s.toLowerCase()}`;
const statusNextLabel = { SCHEDULED: 'Розпочати посадку', BOARDING: 'Вирушити', ACTIVE: 'Завершити рейс' };
const statusNextValue = { SCHEDULED: 'BOARDING', BOARDING: 'ACTIVE', ACTIVE: 'COMPLETED' };

// API CALLS
async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(error);
        toast('error', `Помилка: ${error.message}`);
        return null;
    }
}

// ══════════════════════════════════════════════
//  INITIALIZATION
// ══════════════════════════════════════════════
async function init() {
    await Promise.all([
        fetchLocations(),
        fetchVehicles(),
        fetchUsers() // Used as drivers list
    ]);
    await fetchTrips();
    await fetchStats();
}

// ══════════════════════════════════════════════
//  DATA FETCHING
// ══════════════════════════════════════════════
async function fetchTrips() {
    const data = await apiFetch(`/trips?day_offset=${currentDayOffset}`);
    if (data) {
        trips = data;
        renderSchedule();
    }
}

async function fetchStats() {
    const data = await apiFetch('/stats');
    if (data) {
        stats = data;
        renderFinance();
    }
}

async function fetchUsers(search = "") {
    const data = await apiFetch(`/users?search=${encodeURIComponent(search)}`);
    if (data) {
        users = data;
        renderCRM();
        populateDriverDropdowns();
    }
}

async function fetchVehicles() {
    const data = await apiFetch('/vehicles');
    if (data) {
        vehicles = data;
        renderVehicles();
        populateVehicleDropdowns();
    }
}

async function fetchLocations() {
    const data = await apiFetch('/locations');
    if (data) {
        locations = data;
        populateLocationDropdowns();
    }
}

// ══════════════════════════════════════════════
//  SCHEDULE & TRIPS
// ══════════════════════════════════════════════
function renderSchedule() {
    const d = getDateForOffset(currentDayOffset);
    document.getElementById('schedule-date-label').textContent = formatDate(d) +
        (currentDayOffset === 0 ? ' — сьогодні' : currentDayOffset === -1 ? ' — вчора' : ' — завтра');

    const container = document.getElementById('trips-container');
    if (trips.length === 0) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">🚌</div><p>Рейсів не знайдено.</p></div>`;
        return;
    }

    container.innerHTML = trips.map(t => renderTripCard(t)).join('');
}

function renderTripCard(t) {
    const pct = 0; // Stats from backend needed for real occupancy
    const canChangeStatus = ['SCHEDULED', 'BOARDING', 'ACTIVE'].includes(t.status);
    const time = new Date(t.departure_time).toLocaleTimeString('uk', { hour: '2-digit', minute: '2-digit' });

    return `
<div class="trip-card ${t.status.toLowerCase()}" id="trip-card-${t.id}">
  <div class="trip-card-header">
    <div>
      <div style="display:flex;align-items:baseline;gap:10px;">
        <div class="trip-time">${time}</div>
        <div class="trip-route">${routeLabel(t)}</div>
      </div>
      <div class="trip-meta">
        <span>👨‍✈️ ${t.driver.full_name || '—'}</span>
        <span>🚌 ${t.vehicle.model} [${t.vehicle.plate_number}]</span>
        <span>💺 ${t.price_seated} грн / 🧍 ${t.price_standing} грн</span>
      </div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;">
      <span class="badge ${statusBadge(t.status)}">${statusLabel(t.status)}</span>
      ${canChangeStatus ? `<button class="btn btn-ghost btn-sm" onclick="changeTripStatus(${t.id}, '${statusNextValue[t.status]}')">${statusNextLabel[t.status]}</button>` : ''}
    </div>
  </div>
  <div class="trip-stats">
    <div class="trip-stats-row">
      <span>Сидячих: <strong>? / ${t.seats_limit_snapshot}</strong></span>
      <span style="color:var(--text-muted);font-size:12px;">Стоячі: ? / ${t.standing_limit_snapshot}</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
  </div>
  <div class="trip-actions">
    <button class="btn btn-blue btn-sm" onclick="openManifest(${t.id})">📋 Маніфест</button>
    <button class="btn btn-ghost btn-sm">✏️ Редагувати</button>
    ${t.status === 'COMPLETED' ? `<button class="btn btn-success btn-sm" onclick="openCloseTrip(${t.id})">💰 Закрити рейс</button>` : ''}
  </div>
</div>`;
}

async function changeTripStatus(tripId, newStatus) {
    const data = await apiFetch(`/trips/${tripId}/status?status=${newStatus}`, { method: 'PATCH' });
    if (data) {
        toast('success', `Статус змінено на ${statusLabel(newStatus)}`);
        fetchTrips();
    }
}

// ══════════════════════════════════════════════
//  CRM
// ══════════════════════════════════════════════
function renderCRM() {
    const tbody = document.getElementById('crm-tbody');
    if (users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);">Пасажирів не знайдено</td></tr>`;
        return;
    }
    tbody.innerHTML = users.map(p => {
        const stats = p.stats || { total_trips: 0, total_noshows: 0, trust_score_cached: 100 };
        const ts = stats.trust_score_cached;
        const tsColor = ts >= 75 ? 'var(--green)' : ts >= 50 ? 'var(--orange)' : 'var(--red)';
        
        return `<tr>
      <td><div style="font-weight:700;">${p.full_name || '—'}</div></td>
      <td style="font-size:12px;color:var(--text-muted);">${p.phone || '—'}</td>
      <td style="font-size:13px;"><strong>${stats.total_trips}</strong> / <span style="color:${stats.total_noshows > 0 ? 'var(--red)' : 'var(--text-muted)'};">${stats.total_noshows} no-show</span></td>
      <td>
        <div class="trust-bar">
          <div class="trust-mini-bar"><div class="trust-mini-fill" style="width:${ts}%;background:${tsColor};"></div></div>
          <div class="trust-score">${ts}</div>
        </div>
      </td>
      <td><span class="badge badge-active">${p.role}</span></td>
      <td>—</td>
      <td><button class="btn btn-ghost btn-sm">Деталі</button></td>
    </tr>`;
    }).join('');
}

// ══════════════════════════════════════════════
//  FINANCE
// ══════════════════════════════════════════════
function renderFinance() {
    document.getElementById('finance-stats').innerHTML = `
    <div class="stat-card accent"><div class="stat-label">Виручка сьогодні</div><div class="stat-value" style="color:var(--accent);">${stats.revenue_today || 0}</div><div class="stat-sub">грн</div></div>
    <div class="stat-card green"><div class="stat-label">Загальна виручка</div><div class="stat-value" style="color:var(--green);">${stats.revenue_today || 0}</div><div class="stat-sub">грн</div></div>
    <div class="stat-card blue"><div class="stat-label">Рейсів всього</div><div class="stat-value" style="color:var(--blue);">${stats.trips_total || 0}</div><div class="stat-sub">рейсів</div></div>
    <div class="stat-card red"><div class="stat-label">Користувачів</div><div class="stat-value" style="color:var(--red);">${stats.users_total || 0}</div><div class="stat-sub">осіб</div></div>
  `;
}

// ══════════════════════════════════════════════
//  VEHICLES
// ══════════════════════════════════════════════
function renderVehicles() {
    document.getElementById('vehicles-grid').innerHTML = vehicles.map(v => `
    <div class="vehicle-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
        <div class="vehicle-plate">${v.plate_number}</div>
        <span class="vehicle-status ${v.is_active ? 'active' : 'inactive'}">${v.is_active ? '● Активний' : '● Неактивний'}</span>
      </div>
      <div class="vehicle-model">${v.model}</div>
      <div class="vehicle-seats">
        <span class="seat-chip seated">💺 ${v.total_seats} сидячих</span>
        <span class="seat-chip standing">🧍 ${v.total_standing} стоячих</span>
      </div>
    </div>
  `).join('');
}

async function saveVehicle() {
    const data = {
        plate_number: document.getElementById('av-plate').value,
        model: document.getElementById('av-model').value,
        total_seats: parseInt(document.getElementById('av-seats').value),
        total_standing: parseInt(document.getElementById('av-standing').value),
        is_active: true
    };
    const res = await apiFetch('/vehicles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (res) {
        toast('success', 'Авто додано');
        closeModal('modal-add-vehicle');
        fetchVehicles();
    }
}

// ══════════════════════════════════════════════
//  WIZARD / CREATE TRIP
// ══════════════════════════════════════════════
async function wizardSaveSingle() {
    const data = {
        from_location_id: parseInt(document.getElementById('sw-from').value),
        to_location_id: parseInt(document.getElementById('sw-to').value),
        departure_time: `${document.getElementById('sw-date').value}T${document.getElementById('sw-time').value}:00Z`,
        driver_id: parseInt(document.getElementById('sw-driver').value),
        vehicle_id: parseInt(document.getElementById('sw-vehicle').value),
        price_seated: parseFloat(document.getElementById('sw-price-seated').value),
        price_standing: parseFloat(document.getElementById('sw-price-standing').value)
    };
    const res = await apiFetch('/trips', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (res) {
        toast('success', 'Рейс створено');
        closeModal('modal-schedule-wizard');
        fetchTrips();
    }
}

// ══════════════════════════════════════════════
//  DROPDOWNS POPULATION
// ══════════════════════════════════════════════
function populateLocationDropdowns() {
    const html = locations.map(l => `<option value="${l.id}">${l.name}</option>`).join('');
    // For single wizard
    const from = document.getElementById('sw-from');
    const to = document.getElementById('sw-to');
    if (from && to) {
        from.innerHTML = html;
        to.innerHTML = html;
    }
}

function populateDriverDropdowns() {
    const drivers = users.filter(u => u.role === 'driver');
    const html = drivers.map(d => `<option value="${d.id}">${d.full_name || d.phone}</option>`).join('');
    const sw = document.getElementById('sw-driver');
    if (sw) sw.innerHTML = html;
}

function populateVehicleDropdowns() {
    const activeVehicles = vehicles.filter(v => v.is_active);
    const html = activeVehicles.map(v => `<option value="${v.id}">${v.model} [${v.plate_number}]</option>`).join('');
    const sw = document.getElementById('sw-vehicle');
    if (sw) sw.innerHTML = html;
}

// ══════════════════════════════════════════════
//  UI CONTROLS
// ══════════════════════════════════════════════
document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => {
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        el.classList.add('active');
        const page = el.dataset.page;
        document.getElementById('page-' + page).classList.add('active');
    });
});

document.querySelectorAll('[data-day]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('[data-day]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentDayOffset = parseInt(btn.dataset.day);
        fetchTrips();
    });
});

function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

function toast(type, msg) {
    const tc = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${type === 'success' ? '✅' : '❌'}</span><span>${msg}</span>`;
    tc.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

// START
init();
