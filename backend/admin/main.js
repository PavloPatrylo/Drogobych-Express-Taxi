// ══════════════════════════════════════════════
//  ГОЛОВНИЙ ФАЙЛ: ІНІЦІАЛІЗАЦІЯ ТА НАВІГАЦІЯ (main.js)
// ══════════════════════════════════════════════

// ── 1. НАВІГАЦІЯ ПО БОКОВОМУ МЕНЮ ──
document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => {
        // Знімаємо активний клас з усіх пунктів меню та сторінок
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        
        // Робимо активним натиснутий елемент
        el.classList.add('active');
        const page = el.dataset.page;
        document.getElementById('page-' + page).classList.add('active');
        
        // Викликаємо функцію рендеру для відповідної сторінки
        if (page === 'schedule' && typeof renderSchedule === 'function') renderSchedule();
        if (page === 'crm' && typeof renderCRM === 'function') renderCRM();
        if (page === 'finance' && typeof renderFinance === 'function') renderFinance();
        if (page === 'vehicles' && typeof renderVehicles === 'function') renderVehicles();
        if (page === 'broadcast' && typeof renderBroadcast === 'function') renderBroadcast();
    });
});

// ── 2. ВКЛАДКИ (TABS) НА СТОРІНКАХ ──
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

// ── 3. ФІЛЬТРИ ДАТ ТА МАРШРУТІВ (РОЗКЛАД) ──
document.querySelectorAll('[data-day]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('[data-day]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentDayOffset = parseInt(btn.dataset.day);
        if (typeof renderSchedule === 'function') renderSchedule();
    });
});

if (document.getElementById('route-filter')) {
    document.getElementById('route-filter').addEventListener('change', () => renderSchedule());
}
if (document.getElementById('status-filter')) {
    document.getElementById('status-filter').addEventListener('change', () => renderSchedule());
}

// ── 4. ГАРЯЧІ КЛАВІШІ (HOTKEYS) ──
document.addEventListener('keydown', (e) => {
    // Ctrl + N: Відкрити створення рейсу (Майстер розкладу)
    if (e.ctrlKey && e.key === 'n') { 
        e.preventDefault(); 
        if (typeof openScheduleWizard === 'function') openScheduleWizard();
        else if (typeof openModal === 'function') openModal('modal-create-trip'); 
    }
    // Escape: Закрити будь-які модалки та маніфест
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-backdrop.open').forEach(m => m.classList.remove('open'));
        if (typeof closeManifest === 'function') closeManifest();
    }
});

// ── 5. ВИХІД З СИСТЕМИ (LOGOUT) ──
function handleLogout() {
    showConfirm('👋', 'Вийти з системи?', 'Ваш сеанс буде завершено, токен видалено.', () => {
        api.clearToken();
        window.location.reload(); // Перезавантажуємо сторінку, щоб викинуло на введення токена
    });
}

// ── 6. ІНІЦІАЛІЗАЦІЯ ДОДАТКУ ТА РОБОТА З БЕКЕНДОМ ──
async function init() {
    // Встановлюємо сьогоднішню дату в усі інпути дат
    const todayStr = isoDate(TODAY);
    if (document.getElementById('finance-date-from')) document.getElementById('finance-date-from').value = todayStr;
    if (document.getElementById('finance-date-to')) document.getElementById('finance-date-to').value = todayStr;
    if (document.getElementById('wt-date')) document.getElementById('wt-date').value = todayStr;

    try {
        // 1. Отримуємо дані про поточного користувача (Хто авторизувався?)
        const me = await apiFetch('/auth/me').catch(() => ({ full_name: "Адміністратор", role: "ADMIN" })); 
        
        // Оновлюємо UI (Ім'я, роль, аватарка)
        if (document.getElementById('current-user-name')) {
            document.getElementById('current-user-name').textContent = me.full_name || "Адміністратор";
            document.getElementById('current-user-role').textContent = me.role || "ADMIN";
            
            const initials = (me.full_name || "А Д").split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();
            document.getElementById('user-avatar-abbr').textContent = initials;
        }

        // Застосовуємо RBAC (ховаємо елементи власника, якщо це звичайний диспетчер)
        const roleUpper = (me.role || "").toUpperCase();
        if (roleUpper !== 'ADMIN' && roleUpper !== 'SUPERUSER') {
            document.querySelectorAll('.owner-only').forEach(el => el.classList.add('hidden'));
        }

        // 2. Завантажуємо базові дані паралельно (шоб було швидше)
        const [vData, uData, tData, pData, bData, aData] = await Promise.all([
            apiFetch('/vehicles').catch(() => []),       // Автопарк
            apiFetch('/users').catch(() => []),          // Персонал (водії)
            apiFetch('/trips').catch(() => []),          // Рейси
            apiFetch('/passengers').catch(() => []),     // Клієнти (CRM)
            apiFetch('/bookings').catch(() => []),       // Бронювання
            apiFetch('/audit/log').catch(() => [])       // Аудит-слід
        ]);

        // Наповнюємо глобальні змінні з data.js
        vehicles = vData;
        drivers = uData.filter(u => u.is_driver || u.role === 'driver'); 
        trips = tData;
        passengers = pData;
        bookings = bData;
        auditLog = aData;

        // 3. Запускаємо відмальовку інтерфейсу
        if (typeof populateCreateTripDropdowns === 'function') populateCreateTripDropdowns();
        if (typeof renderSchedule === 'function') renderSchedule();
        
        toast('success', '✅ Зв\'язок з БД встановлено!');

    } catch (error) {
        toast('error', `Помилка ініціалізації: ${error.message}`);
        console.error("Init Error:", error);
        
        // Навіть якщо сталася помилка, намагаємось відрендерити пустий розклад
        if (typeof renderSchedule === 'function') renderSchedule();
    }
}

// Запускаємо додаток після того, як всі скрипти завантажились
init();