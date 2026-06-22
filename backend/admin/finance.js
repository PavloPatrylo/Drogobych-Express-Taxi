// ══════════════════════════════════════════════
//  СТОРІНКА: ФІНАНСИ ТА ЗВІТИ
// ══════════════════════════════════════════════

function renderFinance() {
  const dateFromEl = document.getElementById('finance-date-from');
  const dateToEl = document.getElementById('finance-date-to');
  const dateFrom = dateFromEl ? dateFromEl.value : '';
  const dateTo = dateToEl ? dateToEl.value : '';

  let filteredTrips = trips;
  if (dateFrom) filteredTrips = filteredTrips.filter(t => t.date >= dateFrom);
  if (dateTo) filteredTrips = filteredTrips.filter(t => t.date <= dateTo);

  const filteredTripIds = new Set(filteredTrips.map(t => t.id));
  const filteredBookings = bookings.filter(b => filteredTripIds.has(b.trip_id));

  const allRevenue = filteredBookings.filter(b => !['CANCELLED', 'NOSHOW'].includes(b.status)).reduce((a, b) => a + (b.amount_paid || 0), 0);
  const todayTrips = trips.filter(t => t.date === isoDate(TODAY));
  const todayRevenue = todayTrips.reduce((a, t) => { const s = getTripStats(t.id); return a + s.revenue; }, 0);
  const pendingClose = filteredTrips.filter(t => t.status === 'COMPLETED').length;

  document.getElementById('finance-stats').innerHTML = `
    <div class="stat-card accent"><div class="stat-label">Виручка сьогодні</div><div class="stat-value" style="color:var(--accent);">${todayRevenue}</div><div class="stat-sub">грн</div></div>
    <div class="stat-card green"><div class="stat-label">Загальна виручка</div><div class="stat-value" style="color:var(--green);">${allRevenue}</div><div class="stat-sub">грн</div></div>
    <div class="stat-card blue"><div class="stat-label">Рейсів сьогодні</div><div class="stat-value" style="color:var(--blue);">${todayTrips.length}</div><div class="stat-sub">рейсів</div></div>
    <div class="stat-card red"><div class="stat-label">Очік. закриття</div><div class="stat-value" style="color:var(--red);">${pendingClose}</div><div class="stat-sub">рейсів</div></div>
  `;

  // ── Рейси, що потребують фінансового закриття ──
  const pending = filteredTrips.filter(t => t.status === 'COMPLETED');
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
          <div class="finance-row"><span class="finance-label">Загальна виручка (SUM amount_paid)</span><span class="finance-value green">${stats.revenue} грн</span></div>
        </div>
        <button class="btn btn-success" onclick="openCloseTrip(${t.id})">💰 Закрити рейс (фінансово)</button>
      </div>`;
    }).join('');
  }

  // ── Закриті рейси ──
  const closed = filteredTrips.filter(t => t.status === 'CLOSED');
  document.getElementById('closed-trips-tbody').innerHTML = closed.length === 0
    ? `<tr><td colspan="11" style="text-align:center;padding:30px;color:var(--text-muted);">Закритих рейсів немає</td></tr>`
    : closed.map(t => {
      const stats = getTripStats(t.id);
      const driver = drivers.find(d => d.id === t.driver_id);
      const vehicle = vehicles.find(v => v.id === t.vehicle_id);
      const diff = (t.submitted_amount || 0) - stats.revenue;
      const diffClass = diff === 0 ? 'green' : 'red';
      const diffText = diff === 0 ? '0' : diff > 0 ? `+${diff}` : `${diff}`;
      return `<tr>
        <td style="font-size:12px;">${t.date}</td>
        <td style="font-weight:700;">${t.departure_time} ${routeLabel(t.route)}</td>
        <td style="font-size:12px;">${driver?.name || '—'}</td>
        <td style="font-size:12px;">${vehicle?.plate || '—'}</td>
        <td>${stats.seated}</td><td>${stats.standing}</td><td>${stats.parcels}</td>
        <td style="color:var(--green);font-weight:700;">${stats.revenue} грн</td>
        <td style="font-weight:700;">${t.submitted_amount || 0} грн</td>
        <td class="${diffClass}" style="font-weight:700;">${diffText} грн</td>
        <td style="font-size:12px;color:var(--text-muted);">${t.closed_by || 'Система'}</td>
      </tr>`;
    }).join('');

  // ── Аудит-слід ──
  // Filter audit trail logs by date range as well
  let filteredAudit = auditLog;
  if (dateFrom || dateTo) {
    filteredAudit = filteredAudit.filter(a => {
      if (!a.created_at) return true;
      const aDate = a.created_at.split('T')[0];
      if (dateFrom && aDate < dateFrom) return false;
      if (dateTo && aDate > dateTo) return false;
      return true;
    });
  }
  document.getElementById('audit-tbody').innerHTML = filteredAudit.map(a => {
    const srcColor = { BOT: 'var(--blue)', PHONE: 'var(--orange)', DRIVER: 'var(--green)', SYSTEM: 'var(--text-dim)' }[a.source] || 'var(--text-muted)';
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
    <div class="finance-row"><span class="finance-label" style="font-weight:900;">Загальна виручка</span><span class="finance-value green" style="font-size:18px;">${stats.revenue} грн</span></div>
  `;
  openModal('modal-close-trip');
}

async function confirmCloseTrip() {
  if (!pendingCloseId) return;
  const t = trips.find(x => x.id === pendingCloseId);
  const submittedAmount = parseFloat(document.getElementById('ct-cash-submitted').value) || 0;

  try {
    const updatedTrip = await api.post(`/finance/trips/${pendingCloseId}/close`, {
      submitted_amount: submittedAmount
    });
    
    t.status = 'CLOSED';
    t.closed_by = updatedTrip.closed_by;
    t.submitted_amount = updatedTrip.submitted_amount;

    // Re-fetch bookings and audit log to keep state in sync
    const [bData, aData] = await Promise.all([
      apiFetch('/bookings').catch(() => []),
      apiFetch('/audit/log').catch(() => [])
    ]);
    bookings = bData;
    auditLog = aData;

    closeModal('modal-close-trip');
    pendingCloseId = null;
    document.getElementById('ct-cash-submitted').value = '';
    toast('success', '✅ Рейс фінансово закрито');
    renderFinance();
    renderSchedule();
  } catch (error) {
    toast('error', `Помилка закриття рейсу: ${error.message}`);
  }
}

function exportCSV() {
  const dateFrom = document.getElementById('finance-date-from')?.value;
  const dateTo = document.getElementById('finance-date-to')?.value;
  let filteredTrips = trips;
  if (dateFrom) filteredTrips = filteredTrips.filter(t => t.date >= dateFrom);
  if (dateTo) filteredTrips = filteredTrips.filter(t => t.date <= dateTo);

  const rows = [['Дата', 'Маршрут', 'Водій', 'Сид.', 'Стоячі', 'Посилки', 'Виручка', 'Статус']];
  filteredTrips.forEach(t => {
    const stats = getTripStats(t.id);
    const driver = drivers.find(d => d.id === t.driver_id);
    rows.push([t.date, routeLabel(t.route), driver?.name || '—', stats.seated, stats.standing, stats.parcels, stats.revenue, t.status]);
  });
  const csv = rows.map(r => r.join(',')).join('\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURIComponent(csv);
  a.download = 'trips_report.csv';
  a.click();
  toast('success', 'CSV завантажено');
}