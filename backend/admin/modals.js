// ══════════════════════════════════════════════
//  МОДАЛЬНІ ВІКНА, ПІДТВЕРДЖЕННЯ, ТОСТИ
//  (Спільні UI-примітиви для всіх сторінок)
// ══════════════════════════════════════════════

function openModal(id) {
  document.getElementById(id).classList.add('open');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

// Закриття модалки кліком на бекдроп (поза вікном)
document.querySelectorAll('.modal-backdrop').forEach(bd => {
  bd.addEventListener('click', (e) => { if (e.target === bd) bd.classList.remove('open'); });
});

// ── Універсальне підтвердження дії ──
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

// ── Тости (сповіщення в кутку екрану) ──
function toast(type, msg) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const tc = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${msg}</span>`;
  tc.appendChild(el);
  setTimeout(() => { el.style.animation = 'toastOut 0.3s ease forwards'; setTimeout(() => el.remove(), 300); }, 3000);
}