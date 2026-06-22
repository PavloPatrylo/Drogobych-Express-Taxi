// ══════════════════════════════════════════════
//  СТОРІНКА: КЛІЄНТИ (CRM)
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
  if (list.length === 0) { tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);">Пасажирів не знайдено</td></tr>`; return; }
  tbody.innerHTML = list.map(p => {
    const ts = trustScore(p);
    const tsClass = ts >= 75 ? 'high' : ts >= 50 ? 'mid' : 'low';
    const tsColor = ts >= 75 ? 'var(--green)' : ts >= 50 ? 'var(--orange)' : 'var(--red)';
    const tgBadge = p.telegram_id ? `<span style="background:var(--blue-dim);color:var(--blue);font-size:10px;padding:1px 5px;border-radius:3px;font-weight:700;">TG</span>` : `<span style="background:var(--orange-dim);color:var(--orange);font-size:10px;padding:1px 5px;border-radius:3px;font-weight:700;">Тіньовий</span>`;
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
          ${p.is_active ? `<button class="btn btn-danger btn-sm" onclick="blockPassenger(${p.id})">Блок</button>` : `<button class="btn btn-success btn-sm" onclick="unblockPassenger(${p.id})">Розблок.</button>`}
        </div>
      </td>
    </tr>`;
  }).join('');
}

function blockPassenger(id) {
  const p = passengers.find(x => x.id === id);
  showConfirm('🚫', `Заблокувати пасажира?`, `${p.full_name}\n${p.phone}\n\nПасажир не зможе бронювати місця.`, async () => {
    try {
      await api.post(`/passengers/${id}/block`);
      p.is_active = false;
      toast('error', `${p.full_name} заблокований`);
      renderCRM();
    } catch (error) {
      toast('error', `Помилка блокування: ${error.message}`);
    }
  });
}

async function unblockPassenger(id) {
  const p = passengers.find(x => x.id === id);
  try {
    await api.post(`/passengers/${id}/unblock`);
    p.is_active = true;
    toast('success', `${p.full_name} розблокований`);
    renderCRM();
  } catch (error) {
    toast('error', `Помилка розблокування: ${error.message}`);
  }
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
        <div style="margin-top:4px;">${p.telegram_id ? '<span style="background:var(--blue-dim);color:var(--blue);font-size:11px;padding:2px 7px;border-radius:4px;font-weight:700;">Telegram</span>' : '<span style="background:var(--orange-dim);color:var(--orange);font-size:11px;padding:2px 7px;border-radius:4px;font-weight:700;">Тіньовий профіль</span>'}</div>
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
    ${p.is_active ? `<button class="btn btn-danger" onclick="blockPassenger(${id});closeModal('modal-passenger');renderCRM();">Заблокувати</button>` : `<button class="btn btn-success" onclick="unblockPassenger(${id});closeModal('modal-passenger');renderCRM();">Розблокувати</button>`}
  `;
  openModal('modal-passenger');
}