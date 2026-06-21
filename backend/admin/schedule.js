// ══════════════════════════════════════════════
//  СТОРІНКА: РОЗКЛАД РЕЙСІВ
// ══════════════════════════════════════════════

function renderSchedule() {
  const d = getDateForOffset(currentDayOffset);
  document.getElementById('schedule-date-label').textContent = formatDate(d) + (currentDayOffset === 0 ? ' — сьогодні' : currentDayOffset === -1 ? ' — вчора' : ' — завтра');
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
      <span>Сидячих: <strong>${stats.seated} / ${t.seats_limit_snapshot}</strong></span>
      <span style="color:var(--text-muted);font-size:12px;">Стоячі: ${stats.standing}/${t.standing_limit_snapshot} · Посилки: ${stats.parcels} · Виручка: <strong style="color:var(--green)">${stats.revenue} грн</strong></span>
    </div>
    <div class="progress-bar"><div class="progress-fill ${fillClass}" style="width:${pct}%"></div></div>
  </div>
  <div class="trip-actions">
    <button class="btn btn-blue btn-sm" onclick="openManifest(${t.id})">📋 Маніфест</button>
    ${canClose ? `<button class="btn btn-success btn-sm" onclick="openCloseTrip(${t.id})">💰 Закрити рейс</button>` : ''}
    ${canCancel ? `<button class="btn btn-danger btn-sm" onclick="cancelTrip(${t.id})">Скасувати</button>` : ''}
  </div>
</div>`;
}

function changeStatus(tripId) {
  const t = trips.find(x => x.id === tripId);
  if (!t || !statusNext[t.status]) return;
  const next = statusNext[t.status];
  showConfirm('🚦', `Змінити статус рейсу?`, `${t.departure_time} ${routeLabel(t.route)}\n${statusLabel(t.status)} → ${statusLabel(next)}`, () => {
    t.status = next;
    if (next === 'COMPLETED') {
      bookings.filter(b => b.trip_id === tripId && ['RESERVED', 'PAID'].includes(b.status)).forEach(b => {
        b.status = 'NOSHOW';
        const p = passengers.find(x => x.id === b.passenger_id);
        if (p) { p.total_noshows++; }
      });
    }
    toast('success', `Статус рейсу змінено: ${statusLabel(next)}`);
    renderSchedule();
  });
}

function cancelTrip(tripId) {
  const t = trips.find(x => x.id === tripId);
  showConfirm('⛔', 'Скасувати рейс?', `${t.departure_time} ${routeLabel(t.route)}\nВсі бронювання будуть скасовані.`, () => {
    t.status = 'CANCELLED';
    bookings.filter(b => b.trip_id === tripId && !['CANCELLED', 'NOSHOW'].includes(b.status)).forEach(b => b.status = 'CANCELLED');
    toast('error', 'Рейс скасовано');
    renderSchedule();
  });
}

function createTrip() {
  const route = document.getElementById('ct-route').value;
  const date = document.getElementById('ct-date').value;
  const time = document.getElementById('ct-time').value;
  const arrival = document.getElementById('ct-arrival').value;
  const vehicleId = parseInt(document.getElementById('ct-vehicle').value);
  const driverId = parseInt(document.getElementById('ct-driver').value);
  const priceSeated = parseFloat(document.getElementById('ct-price-seated').value);
  const priceStanding = parseFloat(document.getElementById('ct-price-standing').value);
  if (!date || !time || !vehicleId || !driverId) { toast('error', 'Заповніть всі обов\'язкові поля'); return; }
  // перевірка конфлікту водія/авто на цей же час
  const conflict = trips.find(t => t.date === date && (t.driver_id === driverId || t.vehicle_id === vehicleId) && t.departure_time === time && t.status !== 'CANCELLED');
  if (conflict) { toast('error', '⚠️ Конфлікт: водій або авто вже призначені на цей час'); return; }
  const v = vehicles.find(x => x.id === vehicleId);
  trips.push({ id: nextTripId++, driver_id: driverId, vehicle_id: vehicleId, route, date, departure_time: time, arrival_time: arrival, status: 'SCHEDULED', seats_limit_snapshot: v.total_seats, standing_limit_snapshot: v.total_standing, price_seated: priceSeated, price_standing: priceStanding, closed_by: null });
  closeModal('modal-create-trip');
  toast('success', 'Рейс створено!');
  renderSchedule();
}