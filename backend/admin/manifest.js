// ══════════════════════════════════════════════
//  МАНІФЕСТ РЕЙСУ (виїзна панель)
// ══════════════════════════════════════════════

function openManifest(tripId) {
  currentManifestTripId = tripId;
  const t = trips.find(x => x.id === tripId);
  const stats = getTripStats(tripId);
  document.getElementById('manifest-title').textContent = 'Маніфест рейсу';
  document.getElementById('manifest-subtitle').textContent = `${t.departure_time} | ${routeLabel(t.route)} | ${statusLabel(t.status)}`;
  document.getElementById('manifest-seated-badge').textContent = `👤 ${stats.seated}/${t.seats_limit_snapshot} сид.`;
  document.getElementById('manifest-standing-badge').textContent = `🧍 ${stats.standing} стоячих`;
  document.getElementById('manifest-parcel-badge').textContent = `📦 ${stats.parcels} посилок`;
  renderManifestList(tripId);
  document.getElementById('manifest-backdrop').style.display = 'block';
  document.getElementById('manifest-panel').classList.add('open');
}

function closeManifest() {
  document.getElementById('manifest-backdrop').style.display = 'none';
  document.getElementById('manifest-panel').classList.remove('open');
  currentManifestTripId = null;
}

function renderManifestList(tripId) {
  const b = bookings.filter(x => x.trip_id === tripId && x.status !== 'CANCELLED');
  const list = document.getElementById('manifest-passenger-list');
  if (b.length === 0) { list.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><p>Список пасажирів порожній</p></div>`; return; }
  list.innerHTML = b.map(bk => {
    const p = bk.passenger_id ? passengers.find(x => x.id === bk.passenger_id) : null;
    const srcClass = { BOT: 'source-bot', PHONE: 'source-phone', DRIVER: 'source-driver', WEB: 'source-bot', INSTAGRAM: 'source-bot' }[bk.source] || '';
    const statusClass = { RESERVED: 'status-reserved', BOARDED: 'status-boarded', PAID: 'status-reserved', NOSHOW: 'status-noshow', CANCELLED: 'status-cancelled' }[bk.status] || '';
    const typeLabel = { SEATED: 'Сидяче', STANDING: 'Стояче', PARCEL: '📦 Посилка' }[bk.booking_type];
    const name = p ? p.full_name : bk.booking_type === 'PARCEL' ? 'Посилка' : 'Стоячий';
    const phone = p ? p.phone : '—';
    return `
<div class="passenger-row">
  <div style="flex:1;min-width:0;">
    <div class="passenger-name">${name} <span class="passenger-source ${srcClass}">${bk.source}</span>
      ${bk.comment ? `<span style="font-size:11px;color:var(--text-muted);font-weight:400;"> · ${bk.comment}</span>` : ''}
    </div>
    <div class="passenger-phone">${phone} · ${typeLabel}${bk.passengers_count > 1 ? ' ×' + bk.passengers_count : ''}</div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
    <span class="passenger-status ${statusClass}">${bk.status}</span>
    ${bk.status === 'RESERVED' || bk.status === 'PAID' ? `<button class="btn btn-success btn-sm" onclick="cancelBooking(${bk.id})">Скасувати</button>` : ''}
  </div>
</div>`;
  }).join('');
}

function cancelBooking(bookingId) {
  showConfirm('❌', 'Скасувати бронювання?', 'Місце звільниться для нових пасажирів.', () => {
    const bk = bookings.find(x => x.id === bookingId);
    if (bk) bk.status = 'CANCELLED';
    toast('info', 'Бронювання скасовано');
    if (currentManifestTripId) {
      renderManifestList(currentManifestTripId);
      const stats = getTripStats(currentManifestTripId);
      const t = trips.find(x => x.id === currentManifestTripId);
      document.getElementById('manifest-seated-badge').textContent = `👤 ${stats.seated}/${t.seats_limit_snapshot} сид.`;
    }
    renderSchedule();
  });
}

function addPassengerFromManifest() {
  const phone = document.getElementById('manifest-phone').value.trim();
  const seats = parseInt(document.getElementById('manifest-seats').value);
  const t = trips.find(x => x.id === currentManifestTripId);
  if (!phone) { toast('error', 'Введіть номер телефону'); return; }
  if (!t) return;
  const stats = getTripStats(currentManifestTripId);
  if (stats.seated + seats > t.seats_limit_snapshot) { toast('error', 'Недостатньо місць на рейсі'); return; }
  // знайти існуючого пасажира або створити "тіньовий" профіль
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
  bookings.push({ id: nextBookingId++, trip_id: currentManifestTripId, passenger_id: p.id, created_by_id: 10, booking_type: 'SEATED', source: 'PHONE', status: 'RESERVED', passengers_count: seats, amount_paid: t.price_seated * seats, created_at: new Date().toISOString(), validated_by_id: null, validated_at: null, comment: null });
  document.getElementById('manifest-phone').value = '';
  toast('success', `Бронювання додано для ${p.full_name}`);
  renderManifestList(currentManifestTripId);
  const stats2 = getTripStats(currentManifestTripId);
  document.getElementById('manifest-seated-badge').textContent = `👤 ${stats2.seated}/${t.seats_limit_snapshot} сид.`;
  renderSchedule();
}