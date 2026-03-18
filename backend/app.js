document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp;
    tg.expand();
    tg.setHeaderColor("#facc15");
    
    let telegramId = tg.initDataUnsafe?.user?.id || 1685900931;
    let fallbackName = tg.initDataUnsafe?.user?.first_name || "Користувач";

    const API_URL = 'https://6462489b8d0903.lhr.life/api';

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
                tripsEl.textContent = `🚗 Рейсів: ${userData.stats ? userData.stats.total_trips : 0}`;

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
                const actionButton = hasSeats 
                    ? `<button class="w-full bg-black text-white font-bold py-2 rounded-xl mt-3 hover:bg-gray-800" onclick="window.bookTrip(${trip.id})">Забронювати за ${trip.price_seated} грн</button>`
                    : `<div class="w-full bg-gray-200 text-gray-500 font-bold py-2 rounded-xl mt-3 text-center">Місць немає</div>`;

                resultsContainer.innerHTML += `
                    <div class="bg-white p-4 rounded-2xl shadow-sm border-l-4 ${hasSeats ? 'border-yellow-400' : 'border-gray-300'}">
                        <div class="flex justify-between items-start">
                            <span class="text-2xl font-bold">${time}</span>
                            <span class="bg-${hasSeats ? 'green' : 'red'}-100 text-${hasSeats ? 'green' : 'red'}-800 text-xs px-2 py-1 rounded-full font-bold">
                                ${hasSeats ? `Вільних місць: ${trip.available_seats}` : 'ПРОДАНО'}
                            </span>
                        </div>
                        <p class="mt-1 font-medium text-gray-600">${trip.from_location.name} → ${trip.to_location.name}</p>
                        ${actionButton}
                    </div>`;
            });
        } catch (error) { console.error(error); } finally { searchBtn.textContent = 'Знайти рейс'; searchBtn.disabled = false; }
    });

    // 4. Бронювання (пасажир)
    window.bookTrip = async function(tripId) {
        if (!confirm('Ви впевнені, що хочете забронювати це місце?')) return;
        try {
            const response = await fetch(`${API_URL}/bookings/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
                body: JSON.stringify({ trip_id: tripId, telegram_id: telegramId, requested_seats: 1 })
            });

            if (response.ok) {
                alert(`✅ Бронювання успішне!`);
                searchBtn.click(); 
            } else {
                const errorData = await response.json();
                alert(`❌ Помилка: ${errorData.detail}`);
            }
        } catch (error) { alert('❌ Помилка з\'єднання з сервером.'); }
    };

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
    async function fetchDriverManifest() {
        const driverManifestContainer = document.getElementById('driver-manifest-container');
        driverManifestContainer.innerHTML = '<div class="text-center text-gray-400 py-4">Завантаження рейсів...</div>';

        try {
            const response = await fetch(`${API_URL}/trips/driver/${telegramId}/manifest`, { headers: { 'ngrok-skip-browser-warning': 'true' }});
            if (!response.ok) throw new Error('Помилка маніфесту');
            const manifests = await response.json();

            driverManifestContainer.innerHTML = '';

            if (manifests.length === 0) {
                driverManifestContainer.innerHTML = '<div class="text-center text-gray-500 py-4 text-lg mt-10">У вас немає призначених рейсів на найближчий час 📭</div>';
                return;
            }

            manifests.forEach(manifest => {
                const depTime = new Date(manifest.departure_time);
                const timeStr = depTime.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Kyiv' });
                const dateStr = depTime.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit', timeZone: 'Europe/Kyiv' });
                
                let passengersHtml = '';
                if (manifest.passengers.length === 0) {
                    passengersHtml = '<p class="text-sm text-gray-400 italic mt-2 text-center">Пасажирів поки немає</p>';
                } else {
                    passengersHtml = '<div class="mt-3 space-y-2">';
                    manifest.passengers.forEach((p, index) => {
                        passengersHtml += `
                            <div class="bg-gray-50 p-3 rounded-xl border border-gray-200 text-sm flex justify-between items-center">
                                <div>
                                    <span class="font-bold text-gray-800">${index + 1}. ${p.full_name}</span><br>
                                    <a href="tel:${p.phone}" class="text-blue-600 font-medium text-xs block mt-1">📞 ${p.phone}</a>
                                </div>
                                <div class="text-right">
                                    <span class="font-bold bg-gray-200 px-2 py-1 rounded-md">${p.seats} місць</span><br>
                                    <span class="text-xs text-green-600 font-bold block mt-1">${p.amount_paid} грн</span>
                                </div>
                            </div>
                        `;
                    });
                    passengersHtml += '</div>';
                }

                const cardHtml = `
                    <div class="bg-white p-4 rounded-2xl shadow-sm border-l-4 border-black">
                        <div class="flex justify-between items-start mb-2">
                            <span class="text-lg font-black text-gray-800">${dateStr} о <span class="text-2xl">${timeStr}</span></span>
                            <span class="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full font-bold">
                                Вільних: ${manifest.available_seats}
                            </span>
                        </div>
                        <p class="font-bold text-gray-500 mb-2">${manifest.from_location} → ${manifest.to_location}</p>
                        <hr class="my-3 border-gray-100 border-2 dashed">
                        <h3 class="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">Список пасажирів:</h3>
                        ${passengersHtml}
                    </div>`;
                
                driverManifestContainer.innerHTML += cardHtml;
            });

        } catch (error) {
            console.error(error);
            driverManifestContainer.innerHTML = '<div class="text-center text-red-500 py-4">Сталася помилка при завантаженні</div>';
        }
    }

    // --- СТАРТ ---
    fetchUserData();
});