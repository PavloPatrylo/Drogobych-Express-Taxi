document.addEventListener('DOMContentLoaded', async () => {
    const tg = window.Telegram.WebApp;
    if (tg.ready) tg.ready();
    tg.expand();
    tg.setHeaderColor("#facc15");
    
    let parsedId = tg.initDataUnsafe?.user?.id;
    if (!parsedId || isNaN(Number(parsedId))) {
        const urlParams = new URLSearchParams(window.location.search);
        const paramTgId = urlParams.get('tg_id');
        if (paramTgId && !isNaN(Number(paramTgId))) {
            parsedId = Number(paramTgId);
        } else {
            const savedId = localStorage.getItem('express_taxi_tg_id');
            if (savedId && !isNaN(Number(savedId))) {
                parsedId = Number(savedId);
            } else {
                parsedId = 1685900931;
            }
        }
    }

    let telegramId = Number(parsedId);
    if (isNaN(telegramId)) telegramId = 1685900931;
    localStorage.setItem('express_taxi_tg_id', telegramId);
    let fallbackName = tg.initDataUnsafe?.user?.first_name || "Користувач";

    const API_URL = window.location.origin + '/api';

    let authToken = sessionStorage.getItem('express_taxi_token') || null;

    async function authFetch(url, options = {}) {
        options.headers = options.headers || {};
        if (authToken) {
            options.headers['Authorization'] = `Bearer ${authToken}`;
        }
        options.headers['ngrok-skip-browser-warning'] = 'true';
        return fetch(url, options);
    }

    async function initAuth() {
        if (tg && tg.initData) {
            try {
                const res = await fetch(`${API_URL}/auth/telegram-webapp`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'ngrok-skip-browser-warning': 'true'
                    },
                    body: JSON.stringify({ init_data: tg.initData })
                });
                if (res.ok) {
                    const data = await res.json();
                    authToken = data.access_token;
                    sessionStorage.setItem('express_taxi_token', authToken);
                    if (data.user && data.user.telegram_id) {
                        telegramId = data.user.telegram_id;
                    }
                    initWebSocket();
                }
            } catch (e) {
                console.error("Telegram WebApp auth error:", e);
            }
        }
    }

    await initAuth();

    const expandedTrips = new Set();

    // Елементи DOM
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role');
    const tripsEl = document.getElementById('user-trips');
    const avatarEl = document.getElementById('user-avatar');

    const fromSelect = document.getElementById('from-select');
    const toSelect = document.getElementById('to-select');
    const dateInput = document.getElementById('travel-date');
    const searchBtn = document.getElementById('search-btn');
    const resultsContainer = document.getElementById('results-container');

    // Навігація вкладок (пасажир)
    const navSearch = document.getElementById('nav-search');
    const navTrips = document.getElementById('nav-trips');
    const viewSearch = document.getElementById('view-search');
    const viewTrips = document.getElementById('view-trips');

    // Блоки водія
    const passengerNav = document.getElementById('passenger-nav');
    const viewDriver = document.getElementById('view-driver');

    // Налаштовуємо дати (за замовчуванням - Сьогодні)
    const todayStr = getKyivDateStr(0);
    dateInput.value = todayStr;
    dateInput.min = todayStr;

    const summaryDatePicker = document.getElementById('summary-date-picker');
    if (summaryDatePicker) {
        summaryDatePicker.value = todayStr;
        summaryDatePicker.addEventListener('change', fetchDriverSummary);
    }
    // 👆 КІНЕЦЬ НОВОГО БЛОКУ 👆




    // --- ЛОГІКА ПЕРЕМИКАННЯ ВКЛАДОК (пасажир) ---
    navSearch.addEventListener('click', () => {
        navSearch.className = "text-yellow-600 font-bold border-b-2 border-yellow-500 pb-1 w-1/2";
        navTrips.className = "text-gray-400 font-bold border-b-2 border-transparent pb-1 w-1/2";
        viewSearch.classList.remove('hidden');
        viewTrips.classList.add('hidden');
    });

    navTrips.addEventListener('click', () => {
        navTrips.className = "text-yellow-600 font-bold border-b-2 border-yellow-500 pb-1 w-1/2";
        navSearch.className = "text-gray-400 font-bold border-b-2 border-transparent pb-1 w-1/2";
        viewTrips.classList.remove('hidden');
        viewSearch.classList.add('hidden');
        fetchMyTickets();
    });

    const navDriverTrips = document.getElementById('nav-driver-trips');
    const navDriverSchedule = document.getElementById('nav-driver-schedule');
    const navDriverSummary = document.getElementById('nav-driver-summary');

    const driverTripsView = document.getElementById('driver-trips-view');
    const driverScheduleView = document.getElementById('driver-schedule-view');
    const driverSummaryView = document.getElementById('driver-summary-view');

    if (navDriverTrips && navDriverSchedule && navDriverSummary) {
        navDriverTrips.addEventListener('click', () => {
            navDriverTrips.className = "text-yellow-600 font-bold border-b-2 border-yellow-500 pb-2 w-1/3 mt-2";
            navDriverSchedule.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/3 mt-2";
            navDriverSummary.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/3 mt-2";

            if (driverTripsView) driverTripsView.classList.remove('hidden');
            if (driverScheduleView) driverScheduleView.classList.add('hidden');
            if (driverSummaryView) driverSummaryView.classList.add('hidden');

            fetchDriverManifest();
        });

        navDriverSchedule.addEventListener('click', () => {
            navDriverTrips.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/3 mt-2";
            navDriverSchedule.className = "text-yellow-600 font-bold border-b-2 border-yellow-500 pb-2 w-1/3 mt-2";
            navDriverSummary.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/3 mt-2";

            if (driverTripsView) driverTripsView.classList.add('hidden');
            if (driverScheduleView) driverScheduleView.classList.remove('hidden');
            if (driverSummaryView) driverSummaryView.classList.add('hidden');

            fetchDriverSchedule();
        });

        navDriverSummary.addEventListener('click', () => {
            navDriverTrips.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/3 mt-2";
            navDriverSchedule.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/3 mt-2";
            navDriverSummary.className = "text-yellow-600 font-bold border-b-2 border-yellow-500 pb-2 w-1/3 mt-2";

            if (driverTripsView) driverTripsView.classList.add('hidden');
            if (driverScheduleView) driverScheduleView.classList.add('hidden');
            if (driverSummaryView) driverSummaryView.classList.remove('hidden');

            fetchDriverSummary();
        });
    }



    
    function showLockScreen(title, desc, helperHtml) {
        const lockScreen = document.getElementById('unregistered-lock-screen');
        if (!lockScreen) return;

        const titleEl = document.getElementById('lock-screen-title');
        const descEl = document.getElementById('lock-screen-desc');
        const boxEl = document.getElementById('lock-screen-box');

        if (titleEl) titleEl.textContent = title;
        if (descEl) descEl.textContent = desc;
        if (boxEl) boxEl.innerHTML = helperHtml;

        lockScreen.classList.remove('hidden');
    }

    // 1. Профіль + маршрутизація за роллю
    async function fetchUserData() {
        nameEl.textContent = fallbackName;
        roleEl.textContent = 'Пасажир 🚶';
        tripsEl.textContent = '🚕 Поїздок: 0';
        const initialParts = fallbackName.split(' ');
        avatarEl.textContent = initialParts.map(p => p[0]).join('').substring(0, 2).toUpperCase() || '🚕';

        try {
            const response = await authFetch(`${API_URL}/users/me`);
            if (response.status === 403) {
                showLockScreen(
                    "Обліковий запис заблоковано",
                    "Ваш доступ до сервісу Express Taxi призупинено адміністратором.",
                    "👋 Зверніться до підтримки або адміністратора для розблокування."
                );
                return;
            }
            const userData = await response.json();
            
            if (!userData.phone || !userData.phone.trim()) {
                console.warn("⚠️ Телефон не підтверджено у чаті бота.");
                showLockScreen(
                    "Реєстрацію не завершено",
                    "Для користування Express Taxi поділіться номером телефону у чаті Telegram-бота.",
                    "👉 Закрийте MiniApp, натисніть <b>«📱 Поділитися номером»</b> у чаті бота та спробуйте зайти знову!"
                );
                return;
            }

            nameEl.textContent = userData.full_name || fallbackName;
            const nameParts = (userData.full_name || fallbackName).split(' ');
            avatarEl.textContent = nameParts.map(p => p[0]).join('').substring(0, 2).toUpperCase();

            // Кнопка редагування ПІБ
            const editNameBtn = document.getElementById('editNameBtn');
            if (editNameBtn && !editNameBtn.dataset.bound) {
                editNameBtn.dataset.bound = 'true';
                editNameBtn.addEventListener('click', async () => {
                    const currentName = userData.full_name || fallbackName;
                    const newName = prompt(
                        "Введіть ваше справжнє Ім'я та Прізвище (це допоможе водієві швидше ідентифікувати вас під час посадки):",
                        currentName
                    );
                    if (newName && newName.trim() && newName.trim() !== currentName) {
                        try {
                            const res = await authFetch(`${API_URL}/users/me`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({ full_name: newName.trim() })
                            });
                            if (res.ok) {
                                const updated = await res.json();
                                userData.full_name = updated.full_name;
                                nameEl.textContent = updated.full_name;
                                const parts = updated.full_name.split(' ');
                                avatarEl.textContent = parts.map(p => p[0]).join('').substring(0, 2).toUpperCase();
                                alert("✅ Ім'я та Прізвище успішно оновлено!");
                            }
                        } catch (err) {
                            alert("❌ Помилка оновлення імені");
                        }
                    }
                });
            }

            // --- РОЛЬ: ВОДІЙ ---
            if (userData.role === 'DRIVER' || userData.role === 'driver') {
                roleEl.textContent = 'Водій 🚕';
                roleEl.className = 'text-yellow-800 text-sm font-bold';
                tripsEl.innerHTML = `<span class="text-yellow-800 font-bold">📅 Графік опубліковано у вкладці «Графік»</span>`;

                // Ховаємо пасажирський інтерфейс
                if (passengerNav) passengerNav.classList.add('hidden');
                if (viewSearch) viewSearch.classList.add('hidden');
                if (viewTrips) viewTrips.classList.add('hidden');

                // Показуємо екран водія
                if (viewDriver) viewDriver.classList.remove('hidden');

                fetchDriverManifest();

            // --- РОЛЬ: ПАСАЖИР (або будь-яка інша) ---
            } else {
                roleEl.textContent = 'Пасажир 🚶';
                tripsEl.textContent = `🚕 Поїздок: ${userData.stats ? userData.stats.total_trips : 0}`;

                fetchLocations();
            }

        } catch (error) {
            console.error('Помилка профілю:', error);
            const lockScreen = document.getElementById('unregistered-lock-screen');
            if (lockScreen) lockScreen.classList.remove('hidden');
        }
    }

    // 2. Міста (тільки для пасажира)
    async function fetchLocations() {
        try {
            const response = await fetch(`${API_URL}/trips/locations`, { headers: { 'ngrok-skip-browser-warning': 'true' }});
            const locations = await response.json();
            let optionsHtml = locations.map(loc => `<option value="${loc.id}">${loc.name}</option>`).join('');
            fromSelect.innerHTML = optionsHtml;
            toSelect.innerHTML = optionsHtml;
            if (locations.length >= 2) { 
                fromSelect.value = locations[0].id; // Дрогобич
                toSelect.value = locations[1].id;   // Львів
            }
        } catch (error) { console.error(error); }
    }

    // 3. Пошук рейсів (пасажир)
    searchBtn.addEventListener('click', async () => {
        const fromId = fromSelect.value, toId = toSelect.value, travelDate = dateInput.value;
        if (fromId === toId) return alert('Пункт відправлення і призначення не можуть збігатися!');
        searchBtn.textContent = 'Шукаємо...'; searchBtn.disabled = true; resultsContainer.innerHTML = '';

        try {
            const response = await fetch(`${API_URL}/trips/search?from_id=${fromId}&to_id=${toId}&travel_date=${travelDate}`, { headers: { 'ngrok-skip-browser-warning': 'true' }});
            if (!response.ok) throw new Error('Помилка пошуку');
            const trips = await response.json();

            if (trips.length === 0) {
                resultsContainer.innerHTML = `<div class="text-center p-6 text-gray-500"><span class="text-4xl block mb-2">📭</span>На цю дату рейсів не знайдено.</div>`;
                return;
            }

            trips.forEach(trip => {
                const time = new Date(trip.departure_time).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Kyiv' });
                const hasSeats = trip.available_seats > 0;

                const isBookable = hasSeats && (trip.status === 'SCHEDULED' || trip.status === 'BOARDING');
                
                let actionButton = '';
                if (!isBookable) {
                    // Якщо рейс АКТИВНИЙ або ЗАВЕРШЕНИЙ
                    if (trip.status === 'ACTIVE' || trip.status === 'COMPLETED') {
                        actionButton = `<div class="w-full bg-gray-200 text-gray-500 font-bold py-2 rounded-xl mt-3 text-center">Рейс вже в дорозі</div>`;
                    } else {
                        actionButton = `<div class="w-full bg-gray-200 text-gray-500 font-bold py-2 rounded-xl mt-3 text-center">Місць немає</div>`;
                    }
                } else {
                    actionButton = `<button class="w-full bg-black text-white font-bold py-2 rounded-xl mt-3 hover:bg-gray-800" onclick="window.bookTrip(${trip.id}, ${trip.available_seats}, ${trip.price_seated})">Забронювати за ${trip.price_seated} грн</button>`;
                }
            // ---------------------


                resultsContainer.innerHTML += `
                    <div class="bg-white p-4 rounded-2xl shadow-sm border-l-4 ${hasSeats ? 'border-yellow-400' : 'border-gray-300'}">
                        <div class="flex justify-between items-start">
                            <span class="text-2xl font-bold">${time}</span>
                            <span class="bg-${hasSeats ? 'green' : 'red'}-100 text-${hasSeats ? 'green' : 'red'}-800 text-xs px-2 py-1 rounded-full font-bold">
                                ${hasSeats ? `Вільних місць: ${trip.available_seats}` : 'ПРОДАНО'}
                            </span>
                        </div>
                        
                        <p class="mt-1 font-medium text-gray-600">${trip.from_location.name} → ${trip.to_location.name}</p>
                        
                        <p class="text-xs text-gray-500 font-bold mt-2 mb-3">
                            🚌 ${trip.vehicle_model} • 
                            <span class="bg-gray-100 border border-gray-300 px-1.5 py-0.5 rounded text-gray-800 tracking-wider uppercase">${trip.vehicle_plate}</span>
                        </p>
                        
                        ${actionButton}
                    </div>`;
            });
        } catch (error) { console.error(error); } finally { searchBtn.textContent = 'Знайти рейс'; searchBtn.disabled = false; }
    });

// === ЛОГІКА МОДАЛКИ БРОНЮВАННЯ ===
    const bookingModal = document.getElementById('bookingModal');
    const closeBookingBtn = document.getElementById('closeBookingBtn');
    const confirmBookingBtn = document.getElementById('confirmBookingBtn');
    const btnMinus = document.getElementById('btn-minus');
    const btnPlus = document.getElementById('btn-plus');
    const seatsCounter = document.getElementById('seats-counter');
    const totalPriceEl = document.getElementById('total-price');

    let currentTripId = null;
    let selectedSeats = 1;
    let maxAvailableSeats = 1;
    let pricePerSeat = 0;

    // 4. Функція, яка викликається кнопкою на самому рейсі
    window.bookTrip = function(tripId, availableSeats, price) {
        currentTripId = tripId;
        maxAvailableSeats = availableSeats;
        pricePerSeat = price;
        selectedSeats = 1; // Завжди скидаємо на 1 при відкритті

        updateBookingUI();
        
        // Відкриваємо модалку
        bookingModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    // Оновлення лічильника і ціни
    function updateBookingUI() {
        seatsCounter.textContent = selectedSeats;
        totalPriceEl.textContent = `${selectedSeats * pricePerSeat} грн`;
        
        // Блокуємо кнопки, якщо досягли лімітів
        btnMinus.disabled = selectedSeats <= 1;
        btnPlus.disabled = selectedSeats >= maxAvailableSeats;
    }

    if (bookingModal) {
        // Кнопки + та -
        btnMinus.addEventListener('click', () => {
            if (selectedSeats > 1) {
                selectedSeats--;
                updateBookingUI();
            }
        });

        btnPlus.addEventListener('click', () => {
            if (selectedSeats < maxAvailableSeats) {
                selectedSeats++;
                updateBookingUI();
            }
        });

        // Закриття модалки
        const closeBookingModal = () => {
            bookingModal.classList.add('hidden');
            document.body.style.overflow = '';
        };

        closeBookingBtn.addEventListener('click', closeBookingModal);
        window.addEventListener('click', (e) => {
            if (e.target === bookingModal) closeBookingModal();
        });

        // Кнопка ПІДТВЕРДИТИ
        confirmBookingBtn.addEventListener('click', async () => {
            confirmBookingBtn.textContent = 'Обробка...';
            confirmBookingBtn.disabled = true;

            try {
                const response = await fetch(`${API_URL}/bookings/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
                    body: JSON.stringify({ 
                        trip_id: currentTripId, 
                        telegram_id: telegramId, 
                        requested_seats: selectedSeats // 👈 Відправляємо кількість місць!
                    })
                });

                if (response.ok) {
                    alert(`✅ Бронювання успішне! Квиток додано у розділ «Мої квитки».`);
                    closeBookingModal();
                    searchBtn.click(); // Оновлюємо кількість місць у пошуку
                    navTrips.click();  // Автоматично відкриваємо «Мої квитки»!
                } else {
                    const errorData = await response.json();
                    alert(`❌ Помилка: ${errorData.detail}`);
                }
            } catch (error) { 
                alert('❌ Помилка з\'єднання з сервером.'); 
            } finally {
                confirmBookingBtn.textContent = 'Підтвердити';
                confirmBookingBtn.disabled = false;
            }
        });
    }

    // 5. Список квитків (пасажир)
    async function fetchMyTickets() {
        const activeContainer = document.getElementById('active-tickets-container');
        const historyContainer = document.getElementById('history-tickets-container');
        
        activeContainer.innerHTML = '<div class="text-center text-gray-400 py-4">Завантаження...</div>';
        historyContainer.innerHTML = '';

        try {
            const response = await fetch(`${API_URL}/bookings/my/${telegramId}`, { headers: { 'ngrok-skip-browser-warning': 'true' }});
            if (!response.ok) throw new Error('Помилка завантаження');
            const tickets = await response.json();

            activeContainer.innerHTML = ''; historyContainer.innerHTML = '';

            if (tickets.length === 0) {
                activeContainer.innerHTML = '<div class="text-center text-gray-500 py-4">У вас ще немає квитків 🎫</div>';
                return;
            }

            const now = new Date();

            tickets.forEach(ticket => {
                const depTime = new Date(ticket.trip_departure_time);
                const timeStr = depTime.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Kyiv' });
                const dateStr = depTime.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit', timeZone: 'Europe/Kyiv' });
                
                const isActive = (ticket.status === 'RESERVED' || ticket.status === 'PAID' || ticket.status === 'BOARDED') && depTime > now;

                let statusBadge = '';
                let actionBtn = '';

                if (ticket.status === 'RESERVED' || ticket.status === 'PAID') {
                    statusBadge = `<span class="bg-blue-100 text-blue-800 text-[10px] px-2 py-1 rounded-full font-bold">АКТИВНИЙ</span>`;
                    actionBtn = `<button class="w-full bg-red-50 text-red-600 font-bold py-2 rounded-xl mt-3 border border-red-200 hover:bg-red-100" onclick="window.cancelTicket(${ticket.id})">Скасувати бронювання</button>`;
                } else if (ticket.status === 'CANCELLED') {
                    statusBadge = `<span class="bg-gray-200 text-gray-600 text-[10px] px-2 py-1 rounded-full font-bold">СКАСОВАНО</span>`;
                } else if (ticket.status === 'NOSHOW') {
                    statusBadge = `<span class="bg-red-100 text-red-800 text-[10px] px-2 py-1 rounded-full font-bold">НЕЯВКА</span>`;
                } else {
                    statusBadge = `<span class="bg-green-100 text-green-800 text-[10px] px-2 py-1 rounded-full font-bold">ЗАВЕРШЕНО</span>`;
                }

                const cardHtml = `
                    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-200">
                        <div class="flex justify-between items-start mb-2">
                            <span class="text-sm font-bold text-gray-500">${dateStr} о ${timeStr}</span>
                            ${statusBadge}
                        </div>
                        <p class="font-bold text-lg">${ticket.from_location} → ${ticket.to_location}</p>
                        <p class="text-xs text-gray-500 mt-1">Місць: ${ticket.passengers_count} • Оплата: ${ticket.amount_paid} грн</p>
                        ${isActive ? actionBtn : ''}
                    </div>`;

                if (isActive) activeContainer.innerHTML += cardHtml;
                else historyContainer.innerHTML += cardHtml;
            });

            if (activeContainer.innerHTML === '') activeContainer.innerHTML = '<div class="text-center text-gray-400 text-sm py-2">Немає активних квитків</div>';
            if (historyContainer.innerHTML === '') historyContainer.innerHTML = '<div class="text-center text-gray-400 text-sm py-2">Історія порожня</div>';

        } catch (error) {
            console.error(error);
            activeContainer.innerHTML = '<div class="text-center text-red-500 py-4">Сталася помилка</div>';
        }
    }

    // 6. Скасування квитка (пасажир)
    window.cancelTicket = async function(bookingId) {
        if (!confirm('Ви дійсно хочете скасувати цей квиток?')) return;
        
        try {
            const response = await fetch(`${API_URL}/bookings/${bookingId}/cancel?telegram_id=${telegramId}`, {
                method: 'PATCH', headers: { 'ngrok-skip-browser-warning': 'true' }
            });

            if (response.ok) {
                alert('✅ Бронювання скасовано');
                fetchMyTickets();
            } else {
                const errorData = await response.json();
                alert(`❌ Помилка: ${errorData.detail}`);
            }
        } catch (error) {
            alert('❌ Помилка з\'єднання з сервером');
        }
    };

    function getKyivDateStr(offsetDays = 0) {
        const d = new Date();
        d.setDate(d.getDate() + offsetDays);
        return d.toLocaleDateString('sv-SE', { timeZone: 'Europe/Kyiv' });
    }

    let currentDriverDate = getKyivDateStr(0);

    // 7. Маніфест рейсів (водій)
    // === НОВЕ: ФУНКЦІЯ ДЛЯ ВОДІЯ (UC-D1 FULL SRS) ===
    async function fetchDriverManifest(targetDate = null) {
        if (targetDate) {
            currentDriverDate = targetDate;
        }

        const datePicker = document.getElementById('driver-date-picker');
        if (datePicker) {
            datePicker.value = currentDriverDate;
        }

        const driverManifestContainer = document.getElementById('driver-manifest-container');

        try {
            const url = `${API_URL}/trips/driver/${telegramId}/manifest?target_date=${currentDriverDate}`;
            const response = await authFetch(url);
            if (!response.ok) throw new Error('Помилка маніфесту');
            const manifests = await response.json();

            driverManifestContainer.innerHTML = '';

            if (manifests.length === 0) {
                driverManifestContainer.innerHTML = `<div class="text-center text-gray-500 py-6 text-sm bg-white rounded-2xl border border-gray-200 shadow-sm mt-2 font-medium">
                    На <strong>${currentDriverDate}</strong> рейсів не призначено 📭
                </div>`;
                return;
            }
            manifests.forEach(manifest => {
                const depTime = new Date(manifest.departure_time);
                const timeStr = depTime.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Kyiv' });
                const dateStr = depTime.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit', timeZone: 'Europe/Kyiv' });
                
                const seated = manifest.passengers.filter(p => p.booking_type === 'SEATED' || p.booking_type === 'seated');
                const standing = manifest.passengers.filter(p => p.booking_type === 'STANDING' || p.booking_type === 'standing');
                const parcels = manifest.passengers.filter(p => p.booking_type === 'PARCEL' || p.booking_type === 'parcel');
                
                const standingCount = standing.reduce((sum, p) => sum + p.seats, 0);
                const parcelCount = parcels.reduce((sum, p) => sum + p.seats, 0);
                const totalPassengers = seated.reduce((sum, p) => sum + p.seats, 0) + standingCount;

                const isTripLocked = String(manifest.trip_status).toUpperCase() === 'COMPLETED' || String(manifest.trip_status).toUpperCase() === 'CLOSED';

                let passengersHtml = '';
                if (seated.length === 0) {
                    passengersHtml = '<p class="text-sm text-gray-400 italic mt-2 text-center">Сидячих пасажирів поки немає</p>';
                } else {
                    passengersHtml = '<div class="mt-3 space-y-3">';
                    seated.forEach((p, index) => {
                        let actionButton = '';
                        if (isTripLocked) {
                            if (p.status === 'BOARDED') {
                                actionButton = `<div class="w-full mt-2 bg-green-50 text-green-700 font-bold py-1.5 rounded-lg text-xs text-center border border-green-200">✓ На борту (Зафіксовано)</div>`;
                            } else if (p.status === 'NOSHOW') {
                                actionButton = `<div class="w-full mt-2 bg-red-50 text-red-500 font-bold py-1.5 rounded-lg text-xs text-center border border-red-200">❌ Неявка</div>`;
                            } else {
                                actionButton = `<div class="w-full mt-2 bg-gray-100 text-gray-500 font-bold py-1.5 rounded-lg text-xs text-center">Заброньовано</div>`;
                            }
                        } else {
                            if (p.status === 'RESERVED' || p.status === 'PAID') {
                                actionButton = `<button class="w-full mt-2 bg-green-500 hover:bg-green-600 text-white font-bold py-2 rounded-lg text-sm transition-colors" onclick="confirmBoarding(${p.booking_id})">✓ Підтвердити посадку</button>`;
                            } else if (p.status === 'BOARDED') {
                                actionButton = `<button class="w-full mt-2 bg-green-50 hover:bg-red-50 text-green-700 hover:text-red-600 border border-green-200 hover:border-red-200 font-bold py-2 rounded-lg text-sm text-center transition-colors" onclick="undoBoarding(${p.booking_id})">✓ На борту (Натисніть для відміни)</button>`;
                            } else if (p.status === 'NOSHOW') {
                                actionButton = `<div class="w-full mt-2 bg-red-50 text-red-500 font-bold py-2 rounded-lg text-sm text-center">❌ Неявка</div>`;
                            }
                        }

                        passengersHtml += `
                            <div class="bg-gray-50 p-3 rounded-xl border border-gray-200 text-sm">
                                <div class="flex justify-between items-start">
                                    <div>
                                        <span class="font-bold text-gray-800">${index + 1}. ${p.full_name}</span><br>
                                        <a href="tel:${p.phone}" class="text-blue-600 font-medium text-xs block mt-1">📞 ${p.phone}</a>
                                    </div>
                                    <div class="text-right">
                                        <span class="font-bold bg-gray-200 px-2 py-1 rounded-md">${p.seats} місць</span><br>
                                        <span class="text-xs text-green-600 font-bold block mt-1">${p.amount_paid} грн</span>
                                    </div>
                                </div>
                                ${actionButton}
                            </div>
                        `;
                    });
                    passengersHtml += '</div>';
                }

                let fastSalesHtml = '';
                const fastSales = manifest.passengers.filter(p => String(p.booking_type).toUpperCase() !== 'SEATED');
                
                if (fastSales.length > 0) {
                    fastSalesHtml = '<h3 class="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2 mt-4">Додатково:</h3><div class="space-y-2">';
                    
                    fastSales.forEach(p => {
                        const icon = String(p.booking_type).toUpperCase() === 'STANDING' ? '🧍' : '📦';
                        fastSalesHtml += `
                            <div class="bg-gray-50 p-2 rounded-lg border border-gray-200">
                                <span class="font-bold text-sm text-gray-700">${icon} ${p.full_name} (${p.amount_paid} грн)</span>
                            </div>
                        `;
                    });
                    fastSalesHtml += '</div>';

                    if (!isTripLocked) {
                        const standingSales = fastSales.filter(p => String(p.booking_type).toUpperCase() === 'STANDING');
                        const parcelSales = manifest.passengers.filter(p => String(p.booking_type).toUpperCase() === 'PARCEL');

                        if (standingSales.length > 0 || parcelSales.length > 0) {
                            fastSalesHtml += '<div class="flex gap-2 mt-3">';
                            
                            if (standingSales.length > 0) {
                                const lastStandingId = standingSales[standingSales.length - 1].booking_id;
                                fastSalesHtml += `<button class="flex-1 bg-red-50 hover:bg-red-100 text-red-600 font-bold py-2 rounded-xl text-xs transition-colors border border-red-200" onclick="cancelQuickSale(${lastStandingId})">➖ Скасувати стоячого</button>`;
                            }
                            
                            if (parcelSales.length > 0) {
                                const lastParcelId = parcelSales[parcelSales.length - 1].booking_id;
                                fastSalesHtml += `<button class="flex-1 bg-red-50 hover:bg-red-100 text-red-600 font-bold py-2 rounded-xl text-xs transition-colors border border-red-200" onclick="cancelQuickSale(${lastParcelId})">➖ Скасувати посилку</button>`;
                            }
                            
                            fastSalesHtml += '</div>';
                        }
                    }
                }
                
                let tripStatusBadge = '';
                let mainActionBtn = '';
                
                const statusUpper = String(manifest.trip_status).toUpperCase();
                if (statusUpper === 'SCHEDULED') {
                    tripStatusBadge = `<span class="bg-blue-100 text-blue-800 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider">ОЧІКУЄТЬСЯ</span>`;
                    mainActionBtn = `<button class="w-full mt-2 bg-black text-white font-bold py-3 rounded-xl text-sm transition-colors" onclick="changeTripStatus(${manifest.trip_id}, 'BOARDING')">▶ Розпочати посадку</button>`;
                } else if (statusUpper === 'BOARDING') {
                    tripStatusBadge = `<span class="bg-yellow-100 text-yellow-800 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider">ПОСАДКА</span>`;
                    mainActionBtn = `<button class="w-full mt-2 bg-black text-white font-bold py-3 rounded-xl text-sm transition-colors" onclick="changeTripStatus(${manifest.trip_id}, 'ACTIVE')">▶ Вирушити (В дорогу)</button>`;
                } else if (statusUpper === 'ACTIVE') {
                    tripStatusBadge = `<span class="bg-green-100 text-green-800 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider">В ДОРОЗІ</span>`;
                    mainActionBtn = `<button class="w-full mt-2 bg-black text-white font-bold py-3 rounded-xl text-sm transition-colors" onclick="changeTripStatus(${manifest.trip_id}, 'COMPLETED')">🏁 Завершити рейс</button>`;
                } else if (statusUpper === 'COMPLETED') {
                    tripStatusBadge = `<span class="bg-green-100 text-green-800 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider">🏁 ЗАВЕРШЕНО</span>`;
                    mainActionBtn = `<div class="w-full mt-2 bg-green-50 text-green-800 border border-green-200 font-bold py-2.5 rounded-xl text-xs text-center">🏁 Рейс завершено. Очікує закриття Диспетчером.</div>`;
                } else if (statusUpper === 'CLOSED') {
                    tripStatusBadge = `<span class="bg-purple-100 text-purple-800 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider">🔒 ЗАКРИТО</span>`;
                    mainActionBtn = `<div class="w-full mt-2 bg-purple-50 text-purple-800 border border-purple-200 font-bold py-2.5 rounded-xl text-xs text-center">🔒 Рейс закрито Диспетчером. Редагування заблоковано.</div>`;
                }

                let quickActionsHtml = '';
                if (!isTripLocked) {
                    quickActionsHtml = `
                        <div class="mt-4">
                            <button class="w-full bg-gray-200 hover:bg-gray-300 text-gray-700 font-bold py-3 rounded-xl text-sm transition-colors mb-2 disabled:opacity-40 disabled:cursor-not-allowed" 
                                onclick="addSeatedPassenger(${manifest.trip_id})" ${manifest.available_seats === 0 ? 'disabled' : ''}>
                                💺 + Сидячий пасажир
                            </button>
                            <div class="flex gap-2">
                                <button class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-bold py-2 rounded-xl text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed" 
                                    onclick="addStandingPassenger(${manifest.trip_id})" ${manifest.available_seats > 0 ? 'disabled' : ''}>
                                    🧍 + Стоячий
                                </button>
                                <button class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-bold py-2 rounded-xl text-sm transition-colors" 
                                    onclick="addParcel(${manifest.trip_id})">
                                    📦 Посилка
                                </button>
                            </div>
                        </div>
                    `;
                }

                const statsHtml = `
                    <div class="flex justify-between bg-yellow-50 p-2 rounded-lg text-xs font-bold text-yellow-800 mb-3 border border-yellow-200">
                        <span>👥 Всього пасажирів: ${totalPassengers}</span>
                        <span>🧍 Стоячих: ${standingCount} | 📦 Посилок: ${parcelCount}</span>
                    </div>
                `;

                const isExpanded = expandedTrips.has(manifest.trip_id);
                const listVisibilityClass = isExpanded ? "transition-all duration-300" : "hidden transition-all duration-300";
                const toggleIcon = isExpanded ? "▲" : "▼";

                const cardHtml = `
                    <div class="bg-white p-4 rounded-2xl shadow-sm border-l-4 border-black">
                        <div class="flex justify-between items-start mb-2">
                            <div>
                                <span class="text-lg font-black text-gray-800 block">${dateStr} о <span class="text-2xl">${timeStr}</span></span>
                                <div class="mt-1">${tripStatusBadge}</div>
                            </div>
                            <span class="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full font-bold mt-1">
                                Вільних: ${manifest.available_seats}
                            </span>
                        </div>
                        <p class="font-bold text-gray-500 mb-2 mt-1">${manifest.from_location} → ${manifest.to_location}</p>
                        
                        ${statsHtml}

                        <hr class="my-3 border-gray-100 border-2 dashed">
                        <button class="w-full flex justify-between items-center bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 font-bold py-3 px-4 rounded-xl text-sm transition-colors mb-2" onclick="togglePassengers(${manifest.trip_id})">
                            <span>📋 Сидячі пасажири (${seated.length})</span>
                            <span id="toggle-icon-${manifest.trip_id}" class="text-gray-400">${toggleIcon}</span> </button>

                        <div id="passengers-list-${manifest.trip_id}" class="${listVisibilityClass}">
                            ${passengersHtml}
                            ${fastSalesHtml}
                        </div>
                        
                        <hr class="my-4 border-gray-100">
                        ${quickActionsHtml}
                        <div class="mt-2">
                            ${mainActionBtn}
                        </div>
                    </div>`;
                    
                driverManifestContainer.innerHTML += cardHtml;
            });
        } catch (error) {
            console.error(error);
            driverManifestContainer.innerHTML = '<div class="text-center text-red-500 py-4">Сталася помилка при завантаженні</div>';
        }
    }

    // === ПІДТВЕРДЖЕННЯ ПОСАДКИ (UC-D5) ===
    window.confirmBoarding = async function(bookingId) {
        try {
            const response = await authFetch(`${API_URL}/bookings/${bookingId}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'BOARDED' })
            });
            if (response.ok) fetchDriverManifest();
            else {
                const err = await response.json();
                alert(`❌ Помилка: ${err.detail}`);
            }
        } catch (error) { alert('❌ Помилка сервера'); }
    };
// === ЗМІНА СТАТУСУ РЕЙСУ (UC-D2) ===
    window.changeTripStatus = async function(tripId, newStatus) {
        let actionText = '';
        if (newStatus === 'BOARDING') actionText = 'розпочати посадку пасажирів';
        else if (newStatus === 'ACTIVE') actionText = 'вирушити в дорогу (всіх відсутніх буде відмічено як "Неявка")';
        else if (newStatus === 'COMPLETED') actionText = 'завершити цей рейс';

        if (!confirm(`Ви дійсно хочете ${actionText}?`)) return;

        try {
            const response = await authFetch(`${API_URL}/trips/${tripId}/status?telegram_id=${telegramId}`, {
                method: 'PATCH',
                headers: { 
                    'Content-Type': 'application/json' 
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (response.ok) {
                fetchDriverManifest();
            } else {
                const errorData = await response.json();
                alert(`❌ ${errorData.detail}`);
            }
        } catch (error) {
            console.error(error);
            alert('❌ Помилка з\'єднання з сервером');
        }
    };

    // === ДОДАВАННЯ СТОЯЧОГО ПАСАЖИРА (UC-D3) ===
    window.addStandingPassenger = async function(tripId) {
        try {
            const response = await authFetch(`${API_URL}/bookings/standing`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json' 
                },
                body: JSON.stringify({ trip_id: tripId, telegram_id: telegramId })
            });

            if (response.ok) {
                fetchDriverManifest();
            } else {
                const errorData = await response.json();
                alert(`❌ ${errorData.detail}`);
            }
        } catch (error) {
            console.error(error);
            alert('❌ Помилка з\'єднання з сервером');
        }
    };

    // === ДОДАВАННЯ ПОСИЛКИ ===
    window.addParcel = async function(tripId) {
        let desc = prompt("Введіть опис посилки (або телефон отримувача):", "Коробка");
        if (desc === null) return;

        let priceStr = prompt("Введіть вартість доставки (грн):", "50");
        if (priceStr === null) return;

        let price = parseFloat(priceStr);
        if (isNaN(price)) price = 0;

        try {
            const response = await authFetch(`${API_URL}/bookings/parcel`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json' 
                },
                body: JSON.stringify({ 
                    trip_id: tripId, 
                    telegram_id: telegramId,
                    description: desc,
                    price: price
                })
            });

            if (response.ok) {
                fetchDriverManifest(); 
            } else {
                const errorData = await response.json();
                alert(`❌ Помилка: ${errorData.detail}`);
            }
        } catch (error) {
            console.error(error);
            alert('❌ Помилка з\'єднання з сервером');
        }
    };

    window.togglePassengers = function(tripId) {
        const listContainer = document.getElementById(`passengers-list-${tripId}`);
        const icon = document.getElementById(`toggle-icon-${tripId}`);
        
        if (listContainer.classList.contains('hidden')) {
            listContainer.classList.remove('hidden');
            icon.textContent = '▲'; 
            expandedTrips.add(tripId);
        } else {
            listContainer.classList.add('hidden');
            icon.textContent = '▼'; 
            expandedTrips.delete(tripId);
        }
    };

    window.cancelQuickSale = async function(bookingId) {
        if (!confirm('Видалити цей запис?')) return;
        try {
            const response = await authFetch(`${API_URL}/bookings/${bookingId}/quick-sale?telegram_id=${telegramId}`, {
                method: 'DELETE'
            });
            if (response.ok) fetchDriverManifest();
            else alert("❌ Помилка при видаленні");
        } catch (e) { alert("❌ Помилка з'єднання"); }
    };
    async function fetchDriverSummary() {
        const container = document.getElementById('driver-summary-container');
        const datePicker = document.getElementById('summary-date-picker');
        
        // Формуємо параметр для запиту, якщо вибрана дата
        let dateQuery = '';
        if (datePicker && datePicker.value) {
            dateQuery = `?target_date=${datePicker.value}`;
        }

        container.innerHTML = '<div class="text-center text-gray-400 py-4">Завантаження підсумків...</div>';

        try {
            // 👇 ДОДАЛИ dateQuery В КІНЕЦЬ URL 👇
            const response = await authFetch(`${API_URL}/trips/driver/${telegramId}/summary${dateQuery}`);
            
            if (!response.ok) throw new Error();
            const data = await response.json();

            if (data.trips.length === 0) {
                container.innerHTML = `<div class="text-center text-gray-500 py-10">Немає завершених рейсів на цю дату (${data.date})</div>`;
                return;
            }

            let html = `<div class="bg-amber-100 text-amber-900 text-center p-4 rounded-2xl mb-4 border border-amber-300 shadow-sm">
                            <p class="text-xs font-black uppercase text-amber-800 tracking-wider">💵 ЗДАТИ КАСИРУ ЗА ${data.date}</p>
                            <p class="text-3xl font-black mt-1 text-amber-950 font-mono">${data.total_to_hand_in ?? 0} ₴</p>
                            <p class="text-[11px] font-bold text-amber-700 mt-1">Розрахована каса до здачі за активними квитками рейсів</p>
                        </div>`;

            data.trips.forEach(trip => {
                let badge = '<span class="bg-green-100 text-green-800 text-[10px] font-bold px-2 py-0.5 rounded-full">Завершено</span>';
                if (trip.status === 'CLOSED') {
                    badge = '<span class="bg-purple-100 text-purple-800 text-[10px] font-bold px-2 py-0.5 rounded-full">🔒 Фінансово закрито</span>';
                }

                let breakdownHtml = '';
                if (trip.submitted_cash !== null || trip.submitted_card !== null) {
                    breakdownHtml = `
                        <div class="mt-2 pt-2 border-t border-gray-100 text-[11px] font-bold flex justify-between text-gray-600">
                            <span>💵 Готівка: <span class="text-green-700">${trip.submitted_cash ?? 0} ₴</span></span>
                            <span>💳 Картка: <span class="text-blue-700">${trip.submitted_card ?? 0} ₴</span></span>
                        </div>
                    `;
                }

                html += `
                    <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-200 mb-3">
                        <div class="flex justify-between font-bold border-b pb-2 mb-2 items-center">
                            <div>
                                <span class="text-gray-900 font-black text-sm">${trip.time}</span> | <span class="text-gray-700 text-xs">${trip.route}</span>
                                <div class="mt-0.5">${badge}</div>
                            </div>
                            <span class="text-green-600 font-black text-base">+${trip.trip_sum} ₴</span>
                        </div>
                        <div class="text-xs font-bold text-gray-500 grid grid-cols-3 gap-2 text-center">
                            <div class="bg-gray-50 p-2 rounded-lg">💺 Сидячих<br><span class="text-black text-sm">${trip.seated}</span></div>
                            <div class="bg-gray-50 p-2 rounded-lg">🧍 Стоячих<br><span class="text-black text-sm">${trip.standing}</span></div>
                            <div class="bg-gray-50 p-2 rounded-lg">📦 Посилок<br><span class="text-black text-sm">${trip.parcels}</span></div>
                        </div>
                        ${breakdownHtml}
                    </div>
                `;
            });

            container.innerHTML = html;
        } catch (error) {
            container.innerHTML = '<div class="text-center text-red-500 py-4">Помилка завантаження звіту</div>';
        }
    }

    async function fetchDriverSchedule() {
        const container = document.getElementById('driver-schedule-container');
        if (!container) return;
        
        container.innerHTML = '<div class="text-center text-gray-400 py-8 font-bold text-xs">⏳ Завантаження опублікованого графіку...</div>';

        try {
            const todayStr = getKyivDateStr(0);
            const dateToObj = new Date();
            dateToObj.setDate(dateToObj.getDate() + 6);
            const dateToStr = dateToObj.toLocaleDateString('sv-SE', { timeZone: 'Europe/Kyiv' });

            const response = await authFetch(`${API_URL}/trips/driver/${telegramId}/published-schedule?date_from=${todayStr}&date_to=${dateToStr}`);

            if (!response.ok) throw new Error();
            const data = await response.json();

            if (!data.trips || data.trips.length === 0) {
                container.innerHTML = `
                    <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 text-center space-y-3">
                        <div class="text-4xl">📅</div>
                        <h3 class="font-black text-gray-800 text-sm">Опублікований графік відсутній</h3>
                        <p class="text-xs text-gray-500 font-medium">Наразі Диспетчер ще не опублікував графік рейсів на цей період. Зверніться до адміністрації.</p>
                    </div>
                `;
                return;
            }

            let html = `
                <div class="bg-yellow-400 text-slate-950 p-4 rounded-2xl shadow-sm mb-4 border border-yellow-500 space-y-2">
                    <div class="flex justify-between items-center border-b border-black/10 pb-2">
                        <span class="text-xs font-black uppercase tracking-wider">👨‍✈️ Графік Водія: ${data.driver_name}</span>
                        <span class="bg-black text-yellow-400 text-[10px] font-bold px-2 py-0.5 rounded-full">${data.trips_count} рейсів</span>
                    </div>
                    <div class="text-xs font-bold flex justify-between pt-1">
                        <span>Період: ${data.date_from} — ${data.date_to}</span>
                        <span>Місць: ${data.total_seats}</span>
                    </div>
                </div>
            `;

            if (data.comment) {
                html += `
                    <div class="bg-blue-50 text-blue-900 border border-blue-200 p-3 rounded-xl mb-4 text-xs font-medium flex items-center gap-2">
                        <span>ℹ️ <strong>Примітка Диспетчера:</strong> ${data.comment}</span>
                    </div>
                `;
            }

            // РЕНДЕРИМО СТИЛЬНУ ТАБЛИЦЮ РЕЙСІВ
            html += `
                <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs border-collapse">
                            <thead class="bg-gray-100 border-b border-gray-200 font-bold uppercase text-[10px] text-gray-600">
                                <tr>
                                    <th class="p-3">Дата / Час</th>
                                    <th class="p-3">Маршрут</th>
                                    <th class="p-3">Автобус</th>
                                    <th class="p-3 text-center">Зайнято</th>
                                    <th class="p-3 text-center">Статус</th>
                                    <th class="p-3 w-6"></th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-100 font-medium">
            `;

            data.trips.forEach(t => {
                let statusBadge = '<span class="bg-yellow-100 text-yellow-800 text-[10px] font-bold px-2 py-0.5 rounded-full">Заплановано</span>';
                if (t.status === 'ACTIVE') statusBadge = '<span class="bg-blue-100 text-blue-800 text-[10px] font-bold px-2 py-0.5 rounded-full">В дорозі</span>';
                else if (t.status === 'COMPLETED' || t.status === 'CLOSED') statusBadge = '<span class="bg-green-100 text-green-800 text-[10px] font-bold px-2 py-0.5 rounded-full">Завершено</span>';

                html += `
                    <tr class="schedule-trip-card hover:bg-yellow-50 active:bg-yellow-100 cursor-pointer transition-colors" data-date="${t.date}" data-trip-id="${t.trip_id}">
                        <td class="p-3 font-bold whitespace-nowrap">
                            <div class="text-gray-900 font-black">${t.time}</div>
                            <div class="text-[10px] text-gray-500 font-mono">${t.date_formatted}</div>
                        </td>
                        <td class="p-3 font-bold text-gray-800">${t.route}</td>
                        <td class="p-3 font-mono text-[11px] whitespace-nowrap">
                            <div class="font-bold text-gray-700">${t.vehicle_model}</div>
                            <div class="text-[10px] text-gray-500">${t.vehicle_plate}</div>
                        </td>
                        <td class="p-3 text-center font-bold font-mono whitespace-nowrap">
                            <span class="${t.booked_seats >= t.seats_limit ? 'text-red-600 font-black' : 'text-gray-700'}">${t.booked_seats}</span> / ${t.seats_limit}
                        </td>
                        <td class="p-3 text-center whitespace-nowrap">${statusBadge}</td>
                        <td class="p-3 text-right text-yellow-600 font-bold">➔</td>
                    </tr>
                `;
            });

            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            container.innerHTML = html;

            container.querySelectorAll('.schedule-trip-card').forEach(card => {
                card.onclick = function() {
                    const targetDate = this.getAttribute('data-date');
                    const tripId = Number(this.getAttribute('data-trip-id'));
                    window.openTripFromSchedule(targetDate, tripId);
                };
            });

        } catch (err) {
            container.innerHTML = '<div class="text-center text-red-500 py-4 font-bold text-xs">❌ Помилка завантаження графіку</div>';
        }
    }

    window.openTripFromSchedule = function(targetDate, tripId) {
        const navDriverTrips = document.getElementById('nav-driver-trips');
        const navDriverSchedule = document.getElementById('nav-driver-schedule');
        const navDriverSummary = document.getElementById('nav-driver-summary');

        const driverTripsView = document.getElementById('driver-trips-view');
        const driverScheduleView = document.getElementById('driver-schedule-view');
        const driverSummaryView = document.getElementById('driver-summary-view');

        if (navDriverTrips && navDriverSchedule && navDriverSummary) {
            navDriverTrips.className = "text-yellow-600 font-bold border-b-2 border-yellow-500 pb-2 w-1/3 mt-2";
            navDriverSchedule.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/3 mt-2";
            navDriverSummary.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/3 mt-2";

            if (driverTripsView) driverTripsView.classList.remove('hidden');
            if (driverScheduleView) driverScheduleView.classList.add('hidden');
            if (driverSummaryView) driverSummaryView.classList.add('hidden');
        }

        expandedTrips.add(tripId);
        fetchDriverManifest(targetDate);
    };

        // --- ЛОГІКА МОДАЛЬНОГО ВІКНА "ІНФО" ---
    const infoBtn = document.getElementById('infoBtn');
    const infoModal = document.getElementById('infoModal');
    const closeInfoBtn = document.getElementById('closeInfoBtn');
    const understandBtn = document.getElementById('understandBtn');

    if (infoBtn && infoModal) {
        // Відкрити
        infoBtn.addEventListener('click', () => {
            infoModal.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Блокуємо скрол фону
        });

        // Закрити
        const closeInfo = () => {
            infoModal.classList.add('hidden');
            document.body.style.overflow = ''; // Повертаємо скрол
        };

        closeInfoBtn.addEventListener('click', closeInfo);
        understandBtn.addEventListener('click', closeInfo);

        // Закрити при кліку на темний фон
        window.addEventListener('click', (e) => {
            if (e.target === infoModal) {
                closeInfo();
            }
        });
    }

    // === ДОДАВАННЯ СИДЯЧОГО ПАСАЖИРА ===
    window.addSeatedPassenger = async function(tripId) {
        try {
            const response = await fetch(`${API_URL}/bookings/seated`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true' 
                },
                body: JSON.stringify({ trip_id: tripId, telegram_id: telegramId })
            });

            if (response.ok) {
                fetchDriverManifest(); // Оновлюємо маніфест
            } else {
                const errorData = await response.json();
                alert(`❌ ${errorData.detail}`);
            }
        } catch (error) {
            console.error(error);
            alert('❌ Помилка з\'єднання з сервером');
        }
    };
    // === ВІДМІНА ПОСАДКИ (ВИПАДКОВИЙ КЛІК) ===
// === ВІДМІНА ПОСАДКИ (ВИПАДКОВИЙ КЛІК) ===
    window.undoBoarding = async function(bookingId) {
        // ❌ Рядок із confirm видалено
        try {
            const response = await fetch(`${API_URL}/bookings/${bookingId}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
                body: JSON.stringify({ status: 'RESERVED' })
            });
            if (response.ok) fetchDriverManifest();
            else {
                const err = await response.json();
                alert(`❌ Помилка: ${err.detail}`);
            }
        } catch (error) { alert('❌ Помилка сервера'); }
    };
    // --- КЕРУВАННЯ НАВІГАТОРОМ ДАТ ДЛЯ ВОДІЯ ---
    const driverPrevBtn = document.getElementById('driver-prev-day');
    const driverTodayBtn = document.getElementById('driver-today-day');
    const driverNextBtn = document.getElementById('driver-next-day');
    const driverDatePicker = document.getElementById('driver-date-picker');

    if (driverPrevBtn) {
        driverPrevBtn.addEventListener('click', () => {
            const parts = currentDriverDate.split('-');
            const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
            d.setDate(d.getDate() - 1);
            const prevStr = d.toLocaleDateString('sv-SE');
            fetchDriverManifest(prevStr);
        });
    }

    if (driverTodayBtn) {
        driverTodayBtn.addEventListener('click', () => {
            fetchDriverManifest(getKyivDateStr(0));
        });
    }

    if (driverNextBtn) {
        driverNextBtn.addEventListener('click', () => {
            const parts = currentDriverDate.split('-');
            const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
            d.setDate(d.getDate() + 1);
            const nextStr = d.toLocaleDateString('sv-SE');
            fetchDriverManifest(nextStr);
        });
    }

    if (driverDatePicker) {
        driverDatePicker.addEventListener('change', (e) => {
            if (e.target.value) {
                fetchDriverManifest(e.target.value);
            }
        });
    }

    // --- WEBSOCKET REAL-TIME CONNECTIVITY ---
    let socket = null;
    let socketReconnectTimer = null;

    function initWebSocket() {
        if (!authToken) {
            console.warn("⚠️ WebSocket: відсутній токен авторизації. Підключення скасовано.");
            return;
        }
        if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) {
            return;
        }
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws?token=${encodeURIComponent(authToken)}`;

        try {
            socket = new WebSocket(wsUrl);
        } catch (err) {
            console.error("❌ WebSocket connection error:", err);
            scheduleReconnect();
            return;
        }

        socket.onopen = () => {
            console.log("🟢 WebSocket з'єднання встановлено");
            if (socketReconnectTimer) {
                clearTimeout(socketReconnectTimer);
                socketReconnectTimer = null;
            }
        };

        socket.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                handleSocketEvent(payload);
            } catch (e) {
                console.error("❌ Error parsing WS message:", e);
            }
        };

        socket.onclose = (event) => {
            if (event && event.code === 1008) {
                console.warn("🔴 WebSocket: токен авторизації недійсний (код 1008). Зупинено перепідключення.");
                return;
            }
            console.warn("🔴 WebSocket з'єднання розірвано. Reconnecting in 4s...");
            scheduleReconnect();
        };

        socket.onerror = (err) => {
            console.error("❌ WebSocket error:", err);
            try { socket.close(); } catch (e) {}
        };
    }

    function scheduleReconnect() {
        if (!socketReconnectTimer) {
            socketReconnectTimer = setTimeout(() => {
                socketReconnectTimer = null;
                initWebSocket();
            }, 4000);
        }
    }

    function handleSocketEvent(payload) {
        if (!payload || !payload.event) return;
        const { event, data } = payload;
        console.log("🔔 WS event received:", event, data);

        if (event === "TRIP_MUTATED" || event === "BOOKING_MUTATED") {
            // Оновлюємо пошук пасажира (якщо активний)
            if (viewSearch && !viewSearch.classList.contains('hidden')) {
                if (fromSelect && fromSelect.value && toSelect && toSelect.value && dateInput && dateInput.value) {
                    if (searchBtn && !searchBtn.disabled) {
                        searchBtn.click();
                    }
                }
            }
            // Оновлюємо квитки пасажира (якщо активні)
            if (viewTrips && !viewTrips.classList.contains('hidden')) {
                if (typeof fetchMyTickets === 'function') fetchMyTickets();
            }
            // Оновлюємо панель водія
            if (viewDriver && !viewDriver.classList.contains('hidden')) {
                if (driverTripsView && !driverTripsView.classList.contains('hidden')) {
                    if (typeof fetchDriverManifest === 'function') fetchDriverManifest();
                }
                if (driverScheduleView && !driverScheduleView.classList.contains('hidden')) {
                    if (typeof fetchDriverSchedule === 'function') fetchDriverSchedule();
                }
                if (driverSummaryView && !driverSummaryView.classList.contains('hidden')) {
                    if (typeof fetchDriverSummary === 'function') fetchDriverSummary();
                }
            }
        } else if (event === "CASH_CONFIRMED") {
            if (viewDriver && !viewDriver.classList.contains('hidden')) {
                if (driverSummaryView && !driverSummaryView.classList.contains('hidden')) {
                    if (typeof fetchDriverSummary === 'function') fetchDriverSummary();
                }
            }
        }
    }

    // --- СТАРТ ---
    fetchUserData();
    initWebSocket();
});
