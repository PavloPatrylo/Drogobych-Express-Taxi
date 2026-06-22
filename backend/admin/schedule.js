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
  const canEdit = ['SCHEDULED', 'BOARDING'].includes(t.status);
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
  showConfirm('🚦', `Змінити статус рейсу?`, `${t.departure_time} ${routeLabel(t.route)}\n${statusLabel(t.status)} → ${statusLabel(next)}`, async () => {
    try {
      const updatedTrip = await api.request(`/trips/${tripId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: next })
      });
      t.status = next;
      // Re-fetch bookings and audit log to keep state in sync
      const [bData, aData] = await Promise.all([
        apiFetch('/bookings').catch(() => []),
        apiFetch('/audit/log').catch(() => [])
      ]);
      bookings = bData;
      auditLog = aData;
      toast('success', `Статус рейсу змінено: ${statusLabel(next)}`);
      renderSchedule();
    } catch (error) {
      toast('error', `Помилка зміни статусу: ${error.message}`);
    }
  });
}

function cancelTrip(tripId) {
  const t = trips.find(x => x.id === tripId);
  showConfirm('⛔', 'Скасувати рейс?', `${t.departure_time} ${routeLabel(t.route)}\nВсі бронювання будуть скасовані.`, async () => {
    try {
      await api.post(`/trips/${tripId}/cancel`);
      t.status = 'CANCELLED';
      const [bData, aData] = await Promise.all([
        apiFetch('/bookings').catch(() => []),
        apiFetch('/audit/log').catch(() => [])
      ]);
      bookings = bData;
      auditLog = aData;
      toast('error', 'Рейс скасовано');
      renderSchedule();
    } catch (error) {
      toast('error', `Помилка скасування рейсу: ${error.message}`);
    }
  });
}

function openScheduleWizard() {
  populateScheduleWizardDropdowns();
  
  // Set default values
  document.getElementById('sw-date').value = isoDate(TODAY);
  document.getElementById('sw-time').value = '12:00';
  document.getElementById('sw-arrival').value = '14:30';
  document.getElementById('sw-price-seated').value = 120;
  document.getElementById('sw-price-standing').value = 80;
  
  document.getElementById('wizard-step-choose').style.display = 'flex';
  document.getElementById('wizard-step-single').style.display = 'none';
  document.getElementById('wizard-step-template').style.display = 'none';
  openModal('modal-schedule-wizard');
}

function wizardSelectMode(mode) {
  document.getElementById('wizard-step-choose').style.display = 'none';
  if (mode === 'single') {
    document.getElementById('wizard-step-single').style.display = 'block';
  } else if (mode === 'template') {
    document.getElementById('wizard-step-template').style.display = 'block';
    const dateInput = document.getElementById('wt-date');
    dateInput.value = isoDate(TODAY);
    loadTemplateForDate(dateInput.value);
  }
}

function populateScheduleWizardDropdowns() {
  const vSelect = document.getElementById('sw-vehicle');
  if (vSelect) {
    vSelect.innerHTML = vehicles.filter(v => v.is_active).map(v => `<option value="${v.id}">${v.model} [${v.plate}]</option>`).join('');
  }
  const dSelect = document.getElementById('sw-driver');
  if (dSelect) {
    dSelect.innerHTML = drivers.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
  }
}

function populateEditTripDropdowns() {
  const vSelect = document.getElementById('et-vehicle');
  if (vSelect) {
    vSelect.innerHTML = vehicles.filter(v => v.is_active).map(v => `<option value="${v.id}">${v.model} [${v.plate}]</option>`).join('');
  }
  const dSelect = document.getElementById('et-driver');
  if (dSelect) {
    dSelect.innerHTML = drivers.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
  }
}

async function wizardSaveSingle() {
  const route = document.getElementById('sw-route').value;
  const date = document.getElementById('sw-date').value;
  const time = document.getElementById('sw-time').value;
  const arrival = document.getElementById('sw-arrival').value || null;
  const vehicleId = parseInt(document.getElementById('sw-vehicle').value);
  const driverId = parseInt(document.getElementById('sw-driver').value);
  const priceSeated = parseFloat(document.getElementById('sw-price-seated').value);
  const priceStanding = parseFloat(document.getElementById('sw-price-standing').value);
  if (!date || !time || !vehicleId || !driverId) { toast('error', 'Заповніть всі обов\'язкові поля'); return; }

  try {
    const newTrip = await api.post('/trips', {
      driver_id: driverId,
      vehicle_id: vehicleId,
      route: route,
      date: date,
      departure_time: time,
      arrival_time: arrival,
      price_seated: priceSeated,
      price_standing: priceStanding
    });
    trips.push(newTrip);
    closeModal('modal-schedule-wizard');
    toast('success', 'Рейс створено!');
    renderSchedule();
  } catch (error) {
    toast('error', `Помилка створення рейсу: ${error.message}`);
  }
}

let currentEditTripId = null;

function openEditTrip(tripId) {
  currentEditTripId = tripId;
  const t = trips.find(x => x.id === tripId);
  if (!t) return;

  populateEditTripDropdowns();

  document.getElementById('et-route').value = t.route;
  document.getElementById('et-date').value = t.date;
  document.getElementById('et-time').value = t.departure_time;
  document.getElementById('et-arrival').value = t.arrival_time || '';
  document.getElementById('et-vehicle').value = t.vehicle_id;
  document.getElementById('et-driver').value = t.driver_id;
  document.getElementById('et-price-seated').value = t.price_seated;
  document.getElementById('et-price-standing').value = t.price_standing;

  openModal('modal-edit-trip');
}

async function saveEditTrip() {
  if (!currentEditTripId) return;
  const route = document.getElementById('et-route').value;
  const date = document.getElementById('et-date').value;
  const time = document.getElementById('et-time').value;
  const arrival = document.getElementById('et-arrival').value || null;
  const vehicleId = parseInt(document.getElementById('et-vehicle').value);
  const driverId = parseInt(document.getElementById('et-driver').value);
  const priceSeated = parseFloat(document.getElementById('et-price-seated').value);
  const priceStanding = parseFloat(document.getElementById('et-price-standing').value);

  if (!date || !time || !vehicleId || !driverId) { toast('error', 'Заповніть всі обов\'язкові поля'); return; }

  try {
    const updatedTrip = await api.put(`/trips/${currentEditTripId}`, {
      driver_id: driverId,
      vehicle_id: vehicleId,
      route: route,
      date: date,
      departure_time: time,
      arrival_time: arrival,
      price_seated: priceSeated,
      price_standing: priceStanding
    });

    const idx = trips.findIndex(x => x.id === currentEditTripId);
    if (idx !== -1) {
      trips[idx] = updatedTrip;
    }

    closeModal('modal-edit-trip');
    toast('success', 'Рейс оновлено!');
    renderSchedule();
  } catch (error) {
    toast('error', `Помилка оновлення рейсу: ${error.message}`);
  }
}

function loadTemplateForDate(date) {
  document.getElementById('wt-day-info').textContent = 'Шаблони в розробці';
  document.getElementById('wizard-template-table').innerHTML = `<div class="empty-state"><p>Шаблони розкладу будуть доступні в наступній версії.</p></div>`;
}
function addExtraRowToWizard() {
  toast('info', 'Ця функція тимчасово недоступна');
}
function wizardSaveTemplateDay() {
  toast('info', 'Ця функція тимчасово недоступна');
}