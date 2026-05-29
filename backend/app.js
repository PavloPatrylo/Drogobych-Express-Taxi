document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp;
    tg.expand();
    tg.setHeaderColor("#facc15");
    
    let telegramId = tg.initDataUnsafe?.user?.id || 1685900931;
    let fallbackName = tg.initDataUnsafe?.user?.first_name || "Користувач";

    const API_URL = 'https://da78ae539bebd0.lhr.life/api';

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

    // Налаштовуємо дати
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    dateInput.value = tomorrow.toISOString().split('T')[0];
    dateInput.min = today.toISOString().split('T')[0];


    // 👇 ДОДАЙ ЦЕЙ БЛОК ДЛЯ ВОДІЯ 👇
    const summaryDatePicker = document.getElementById('summary-date-picker');
    if (summaryDatePicker) {
        // Ставимо сьогоднішню дату за замовчуванням
        summaryDatePicker.value = today.toISOString().split('T')[0];
        
        // Коли водій змінює дату - автоматично завантажуємо новий звіт
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
    const navDriverSummary = document.getElementById('nav-driver-summary');
    const viewDriverTrips = document.getElementById('driver-trips-view');
    const viewDriverSummary = document.getElementById('driver-summary-view');

    if (navDriverTrips && navDriverSummary) {
        navDriverTrips.addEventListener('click', () => {
            navDriverTrips.className = "text-yellow-600 font-bold border-b-2 border-yellow-500 pb-2 w-1/2 mt-2";
            navDriverSummary.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/2 mt-2";
            viewDriverTrips.classList.remove('hidden');
            viewDriverSummary.classList.add('hidden');
            fetchDriverManifest();
        });

        navDriverSummary.addEventListener('click', () => {
            navDriverSummary.className = "text-yellow-600 font-bold border-b-2 border-yellow-500 pb-2 w-1/2 mt-2";
            navDriverTrips.className = "text-gray-400 font-bold border-b-2 border-transparent pb-2 w-1/2 mt-2";
            viewDriverSummary.classList.remove('hidden');
            viewDriverTrips.classList.add('hidden');
            fetchDriverSummary();
        });
    }



    
    // 1. Профіль + маршрутизація за роллю
    async function fetchUserData() {
        try {
            const response = await fetch(`${API_URL}/users/${telegramId}`, { headers: { 'ngrok-skip-browser-warning': 'true' }});
            if (!response.ok) throw new Error('Користувача не знайдено');
            const userData = await response.json();
            
            nameEl.textContent = userData.full_name || fallbackName;
            const nameParts = (userData.full_name || fallbackName).split(' ');
            avatarEl.textContent = nameParts.map(p => p[0]).join('').substring(0, 2).toUpperCase();

            // --- РОЛЬ: ВОДІЙ ---
            if (userData.role === 'DRIVER' || userData.role === 'driver') {
                roleEl.textContent = 'Водій 🚕';
                roleEl.className = 'text-yellow-800 text-sm font-bold';
                // Перевіряємо, чи є PDF в базі (припустимо, у тебе буде поле userData.schedule_pdf_url)
                if (userData.schedule_pdf_url) {
                    tripsEl.innerHTML = `<a href="${userData.schedule_pdf_url}" target="_blank" class="text-yellow-600 underline font-bold">📄 Мій графік (PDF)</a>`;
                } else {
                    tripsEl.textContent = `На жаль, ваш графік ще не завантажено. Зверніться до адміністрації.`;
                }

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
            nameEl.textContent = fallbackName;
            // У разі помилки — показуємо пасажирський режим за замовчуванням
            fetchLocations();
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
            if (locations.length >= 2) { fromSelect.value = locations[1].id; toSelect.value = locations[0].id; }
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
                    alert(`✅ Бронювання успішне!`);
                    closeBookingModal();
                    searchBtn.click(); // Оновлюємо пошук
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
    }

    // 7. Маніфест рейсів (водій)
// === НОВЕ: ФУНКЦІЯ ДЛЯ ВОДІЯ (UC-D1 FULL SRS) ===
async function fetchDriverManifest() {
        const driverManifestContainer = document.getElementById('driver-manifest-container');
        
        // ❌ ПРИБИРАЄМО ЦЕЙ РЯДОК, щоб сторінка не "схлопувалася" і не стрибала:
        // driverManifestContainer.innerHTML = '<div class="text-center text-gray-400 py-4">Завантаження рейсів...</div>';

        try {
            const response = await fetch(`${API_URL}/trips/driver/${telegramId}/manifest`, { headers: { 'ngrok-skip-browser-warning': 'true' }});
            if (!response.ok) throw new Error('Помилка маніфесту');
            const manifests = await response.json();

            // ✅ Очищаємо контейнер ТІЛЬКИ ТОДІ, коли дані вже на руках!
            driverManifestContainer.innerHTML = '';

            if (manifests.length === 0) {
                driverManifestContainer.innerHTML = '<div class="text-center text-gray-500 py-4 text-lg mt-10">На сьогодні рейсів не призначено 📭</div>';
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

                let passengersHtml = '';
                if (seated.length === 0) {
                    passengersHtml = '<p class="text-sm text-gray-400 italic mt-2 text-center">Сидячих пасажирів поки немає</p>';
                } else {
                    passengersHtml = '<div class="mt-3 space-y-3">';
                    seated.forEach((p, index) => {
                        let actionButton = '';
                        if (p.status === 'RESERVED' || p.status === 'PAID') {
                            actionButton = `<button class="w-full mt-2 bg-green-500 hover:bg-green-600 text-white font-bold py-2 rounded-lg text-sm transition-colors" onclick="confirmBoarding(${p.booking_id})">✓ Підтвердити посадку</button>`;
                        } else if (p.status === 'BOARDED') {
                            // Тепер це активна кнопка, яка дозволяє скасувати посадку
                            actionButton = `<button class="w-full mt-2 bg-green-50 hover:bg-red-50 text-green-700 hover:text-red-600 border border-green-200 hover:border-red-200 font-bold py-2 rounded-lg text-sm text-center transition-colors" onclick="undoBoarding(${p.booking_id})">✓ На борту (Натисніть для відміни)</button>`;
                        } else if (p.status === 'NOSHOW') {
                            actionButton = `<div class="w-full mt-2 bg-red-50 text-red-500 font-bold py-2 rounded-lg text-sm text-center">❌ Неявка</div>`;
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
// (Це додаємо відразу ПІСЛЯ блоку формування seated пасажирів)
// (Це додаємо відразу ПІСЛЯ блоку формування seated пасажирів)
                let fastSalesHtml = '';
                const fastSales = manifest.passengers.filter(p => String(p.booking_type).toUpperCase() !== 'SEATED');
                
                if (fastSales.length > 0) {
                    fastSalesHtml = '<h3 class="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2 mt-4">Додатково:</h3><div class="space-y-2">';
                    
                    // 1. Виводимо список пасажирів/посилок БЕЗ індивідуальних кнопок видалення
                    fastSales.forEach(p => {
                        const icon = String(p.booking_type).toUpperCase() === 'STANDING' ? '🧍' : '📦';
                        fastSalesHtml += `
                            <div class="bg-gray-50 p-2 rounded-lg border border-gray-200">
                                <span class="font-bold text-sm text-gray-700">${icon} ${p.full_name} (${p.amount_paid} грн)</span>
                            </div>
                        `;
                    });
                    fastSalesHtml += '</div>';

                    // 2. Додаємо загальні кнопки скасування (вони видаляють ОСТАННІЙ доданий запис)
                    const standingSales = fastSales.filter(p => String(p.booking_type).toUpperCase() === 'STANDING');
                    const parcelSales = fastSales.filter(p => String(p.booking_type).toUpperCase() === 'PARCEL');

                    if (standingSales.length > 0 || parcelSales.length > 0) {
                        fastSalesHtml += '<div class="flex gap-2 mt-3">';
                        
                        if (standingSales.length > 0) {
                            // Беремо ID останнього доданого стоячого
                            const lastStandingId = standingSales[standingSales.length - 1].booking_id;
                            fastSalesHtml += `<button class="flex-1 bg-red-50 hover:bg-red-100 text-red-600 font-bold py-2 rounded-xl text-xs transition-colors border border-red-200" onclick="cancelQuickSale(${lastStandingId})">➖ Скасувати стоячого</button>`;
                        }
                        
                        if (parcelSales.length > 0) {
                            // Беремо ID останньої доданої посилки
                            const lastParcelId = parcelSales[parcelSales.length - 1].booking_id;
                            fastSalesHtml += `<button class="flex-1 bg-red-50 hover:bg-red-100 text-red-600 font-bold py-2 rounded-xl text-xs transition-colors border border-red-200" onclick="cancelQuickSale(${lastParcelId})">➖ Скасувати посилку</button>`;
                        }
                        
                        fastSalesHtml += '</div>';
                    }
                }
                
                // Вкінці, де ти збираєш cardHtml, додай ${fastSalesHtml} після ${passengersHtml} всередині контейнера passengers-list.
                // === ДИНАМІЧНА КНОПКА СТАТУСУ РЕЙСУ (UC-D2) ===
                let tripStatusBadge = '';
                let mainActionBtn = '';
                
                if (manifest.trip_status === 'SCHEDULED' || manifest.trip_status === 'scheduled') {
                    tripStatusBadge = `<span class="bg-blue-100 text-blue-800 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider">ОЧІКУЄТЬСЯ</span>`;
                    mainActionBtn = `<button class="w-full mt-2 bg-black text-white font-bold py-3 rounded-xl text-sm transition-colors" onclick="changeTripStatus(${manifest.trip_id}, 'BOARDING')">▶ Розпочати посадку</button>`;
                } else if (manifest.trip_status === 'BOARDING' || manifest.trip_status === 'boarding') {
                    tripStatusBadge = `<span class="bg-yellow-100 text-yellow-800 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider">ПОСАДКА</span>`;
                    mainActionBtn = `<button class="w-full mt-2 bg-black text-white font-bold py-3 rounded-xl text-sm transition-colors" onclick="changeTripStatus(${manifest.trip_id}, 'ACTIVE')">▶ Вирушити (В дорогу)</button>`;
                } else if (manifest.trip_status === 'ACTIVE' || manifest.trip_status === 'active') {
                    tripStatusBadge = `<span class="bg-green-100 text-green-800 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider">В ДОРОЗІ</span>`;
                    mainActionBtn = `<button class="w-full mt-2 bg-black text-white font-bold py-3 rounded-xl text-sm transition-colors" onclick="changeTripStatus(${manifest.trip_id}, 'COMPLETED')">🏁 Завершити рейс</button>`;
                }

// ПЕРЕВІР, ЧИ Є ТУТ onclick:
                let quickActionsHtml = `
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
                    <div class="mt-4">
                        ${mainActionBtn}
                    </div>
                `;

                const statsHtml = `
                    <div class="flex justify-between bg-yellow-50 p-2 rounded-lg text-xs font-bold text-yellow-800 mb-3 border border-yellow-200">
                        <span>👥 Всього пасажирів: ${totalPassengers}</span>
                        <span>🧍 Стоячих: ${standingCount} | 📦 Посилок: ${parcelCount}</span>
                    </div>
                `;

// === ПЕРЕВІРЯЄМО СТАН РОЗГОРТАННЯ ===
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
                    </div>`;
                    
                driverManifestContainer.innerHTML += cardHtml;
            });
        } catch (error) {
            console.error(error);
            driverManifestContainer.innerHTML = '<div class="text-center text-red-500 py-4">Сталася помилка при завантаженні</div>';
        }
    }

    // === ПІДТВЕРДЖЕННЯ ПОСАДКИ (UC-D5) ===
// === ПІДТВЕРДЖЕННЯ ПОСАДКИ (UC-D5) ===
    window.confirmBoarding = async function(bookingId) {
        // ❌ Рядок із confirm видалено
        try {
            const response = await fetch(`${API_URL}/bookings/${bookingId}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
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
        // Формуємо зрозумілий текст для підтвердження
        let actionText = '';
        if (newStatus === 'BOARDING') actionText = 'розпочати посадку пасажирів';
        else if (newStatus === 'ACTIVE') actionText = 'вирушити в дорогу (всіх відсутніх буде відмічено як "Неявка")';
        else if (newStatus === 'COMPLETED') actionText = 'завершити цей рейс';

        if (!confirm(`Ви дійсно хочете ${actionText}?`)) return;

        try {
            // Відправляємо PATCH запит на наш новий ендпоінт
            const response = await fetch(`${API_URL}/trips/${tripId}/status?telegram_id=${telegramId}`, {
                method: 'PATCH',
                headers: { 
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true' 
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (response.ok) {
                // Основний сценарій: Оновлюємо маніфест, щоб побачити новий статус
                fetchDriverManifest();
            } else {
                // Альтернативний сценарій A2.2: Виводимо помилку (напр. "Ця дія недоступна")
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
        // Згідно з SRS (NFR-06) - працює в 1 клік, без підтверджень
        try {
            const response = await fetch(`${API_URL}/bookings/standing`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true' 
                },
                body: JSON.stringify({ trip_id: tripId, telegram_id: telegramId })
            });

            if (response.ok) {
                // Миттєво оновлюємо маніфест
                fetchDriverManifest();
            } else {
                // Виводимо помилку, наприклад "Ліміт стоячих вичерпано"
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
        // Запитуємо у водія короткі дані
        let desc = prompt("Введіть опис посилки (або телефон отримувача):", "Коробка");
        if (desc === null) return; // Якщо водій натиснув "Скасувати"

        let priceStr = prompt("Введіть вартість доставки (грн):", "50");
        if (priceStr === null) return;

        // Перетворюємо введену ціну на число, якщо ввели текст - ставимо 0
        let price = parseFloat(priceStr);
        if (isNaN(price)) price = 0;

        try {
            const response = await fetch(`${API_URL}/bookings/parcel`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true' 
                },
                body: JSON.stringify({ 
                    trip_id: tripId, 
                    telegram_id: telegramId,
                    description: desc,
                    price: price
                })
            });

            if (response.ok) {
                // Безшовне оновлення екрану
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
    // === ЗГОРТАННЯ/РОЗГОРТАННЯ СПИСКУ ПАСАЖИРІВ ===
// === ЗГОРТАННЯ/РОЗГОРТАННЯ СПИСКУ ПАСАЖИРІВ ===
    window.togglePassengers = function(tripId) {
        const listContainer = document.getElementById(`passengers-list-${tripId}`);
        const icon = document.getElementById(`toggle-icon-${tripId}`);
        
        if (listContainer.classList.contains('hidden')) {
            listContainer.classList.remove('hidden');
            icon.textContent = '▲'; 
            expandedTrips.add(tripId); // ✅ Запам'ятовуємо, що цей рейс відкрито
        } else {
            listContainer.classList.add('hidden');
            icon.textContent = '▼'; 
            expandedTrips.delete(tripId); // ✅ Видаляємо з пам'яті, бо рейс закрито
        }
    };
    window.cancelQuickSale = async function(bookingId) {
        if (!confirm('Видалити цей запис?')) return;
        try {
            const response = await fetch(`${API_URL}/bookings/${bookingId}/quick-sale?telegram_id=${telegramId}`, {
                method: 'DELETE', headers: { 'ngrok-skip-browser-warning': 'true' }
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
            const response = await fetch(`${API_URL}/trips/driver/${telegramId}/summary${dateQuery}`, { headers: { 'ngrok-skip-browser-warning': 'true' }});
            
            if (!response.ok) throw new Error();
            const data = await response.json();

            if (data.trips.length === 0) {
                container.innerHTML = `<div class="text-center text-gray-500 py-10">Немає завершених рейсів на цю дату (${data.date})</div>`;
                return;
            }

            let html = `<div class="bg-green-100 text-green-800 text-center p-4 rounded-2xl mb-4 border border-green-200">
                            <p class="text-sm font-bold uppercase">Заробіток за ${data.date}</p>
                            <p class="text-4xl font-black mt-1">${data.total_sum} ₴</p>
                        </div>`;

            data.trips.forEach(trip => {
                html += `
                    <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-200 mb-3">
                        <div class="flex justify-between font-bold border-b pb-2 mb-2">
                            <span>${trip.time} | ${trip.route}</span>
                            <span class="text-green-600">+${trip.trip_sum} ₴</span>
                        </div>
                        <div class="text-xs font-bold text-gray-500 grid grid-cols-3 gap-2 text-center">
                            <div class="bg-gray-50 p-2 rounded-lg">💺 Сидячих<br><span class="text-black text-sm">${trip.seated}</span></div>
                            <div class="bg-gray-50 p-2 rounded-lg">🧍 Стоячих<br><span class="text-black text-sm">${trip.standing}</span></div>
                            <div class="bg-gray-50 p-2 rounded-lg">📦 Посилок<br><span class="text-black text-sm">${trip.parcels}</span></div>
                        </div>
                    </div>
                `;
            });

            container.innerHTML = html;
        } catch (error) {
            container.innerHTML = '<div class="text-center text-red-500 py-4">Помилка завантаження звіту</div>';
        }
    }

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
    // --- СТАРТ ---
    fetchUserData();
});
