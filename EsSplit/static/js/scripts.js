document.addEventListener('DOMContentLoaded', function () {
    if (window.scriptHasRun) return;
    window.scriptHasRun = true;

    // --- ZMIENNE POMOCNICZE ---
    // (dawniej: touchedUserIds do "blokowania" suwaków; teraz kontrola sumy działa od razu)

    // Suwaki: kumulacyjne "lockowanie" – kiedy raz ustawisz osobę, jej kwota zostaje stała,
    // a reszta dzieli tylko pozostałą pulę (proporcjonalnie do aktualnych wartości, bez resetu do równego podziału).
    const lockedFriendIds = new Set();
    const lockOrder = []; // kolejność "zamrażania" (ostatni = najbardziej elastyczny przy cięciu puli)

    const roundToCents = (n) => {
        const x = Number(n);
        if (!Number.isFinite(x)) return 0;
        return Math.round(x * 100) / 100;
    };

    const toCents = (n) => {
        const x = Number(n);
        if (!Number.isFinite(x)) return 0;
        return Math.round(x * 100);
    };

    const fromCents = (c) => (Number(c || 0) / 100);

    const lockId = (id) => {
        const friendId = String(id);
        lockedFriendIds.add(friendId);
        const idx = lockOrder.indexOf(friendId);
        if (idx >= 0) lockOrder.splice(idx, 1);
        lockOrder.push(friendId);
    };

    const themeSwitch = document.getElementById('theme-switch');
    const body = document.body;

    const THEME_STORAGE_KEY = 'fastsplit_theme'; // 'dark' | 'light'

    const setTheme = (isDark) => {
        body.classList.toggle('dark-theme', Boolean(isDark));
        if (themeSwitch) themeSwitch.checked = Boolean(isDark);
    };

    const getAutoTheme = () => {
        // 1) Preferencja systemowa
        if (window.matchMedia) {
            try {
                return window.matchMedia('(prefers-color-scheme: dark)').matches;
            } catch (e) {
                // ignore
            }
        }

        // 2) Fallback "po zachodzie" (prosty): noc wg czasu lokalnego
        const hour = new Date().getHours();
        return hour >= 20 || hour < 6;
    };

    const initTheme = () => {
        let saved = null;
        try {
            saved = localStorage.getItem(THEME_STORAGE_KEY);
        } catch (e) {
            // ignore
        }

        if (saved === 'dark') return setTheme(true);
        if (saved === 'light') return setTheme(false);

        // Brak ręcznej preferencji → auto
        setTheme(getAutoTheme());
    };

    initTheme();

    if (themeSwitch) {
        themeSwitch.addEventListener('change', () => {
            const isDark = themeSwitch.checked;
            setTheme(isDark);
            try {
                localStorage.setItem(THEME_STORAGE_KEY, isDark ? 'dark' : 'light');
            } catch (e) {
                // ignore
            }
        });
    }

    // --- POWIADOMIENIA (panel w headerze) ---
    const notificationsToggle = document.getElementById('notifications-toggle');
    const notificationsPanel = document.getElementById('notifications-panel');
    const notificationsBadge = document.getElementById('notifications-badge');

    const billNotificationsList = document.getElementById('bill-notifications-list');
    const billNotificationsEmpty = document.getElementById('bill-notifications-empty');

    const billPopupOverlay = document.getElementById('bill-popup-overlay');
    const billPopupBody = document.getElementById('bill-popup-body');
    const billPopupClose = document.getElementById('bill-popup-close');
    const billPopupReject = document.getElementById('bill-popup-reject');
    const billPopupRejectForm = document.getElementById('bill-popup-reject-form');
    const billPopupAcceptForm = document.getElementById('bill-popup-accept-form');

    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfInput ? csrfInput.value : null;

    const openBillPopup = ({ billId, creator, description, amountOwed }) => {
        if (!billPopupOverlay || !billPopupBody || !billPopupReject || !billPopupAcceptForm || !billPopupRejectForm) return;

        billPopupBody.innerHTML = `
            <div><strong>Od:</strong> ${escapeHtml(creator)}</div>
            <div><strong>Opis:</strong> ${escapeHtml(description)}</div>
            <div><strong>Twój udział:</strong> ${escapeHtml(amountOwed)} PLN</div>
        `;

        billPopupRejectForm.action = `/bill/${encodeURIComponent(billId)}/reject/`;
        billPopupAcceptForm.action = `/bill/${encodeURIComponent(billId)}/accept/`;

        billPopupOverlay.style.display = 'flex';
    };

    const closeBillPopup = () => {
        if (!billPopupOverlay) return;
        billPopupOverlay.style.display = 'none';
    };

    if (billPopupClose) {
        billPopupClose.addEventListener('click', (e) => {
            e.preventDefault();
            closeBillPopup();
        });
    }

    if (billPopupOverlay) {
        billPopupOverlay.addEventListener('click', (e) => {
            if (e.target === billPopupOverlay) closeBillPopup();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeBillPopup();
    });

    // Zabezpieczenie przed XSS przy budowaniu HTML
    function escapeHtml(str) {
        return String(str ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    // --- POWIADOMIENIA: RACHUNKI (polling) ---
    const BILL_NOTIF_SEEN_KEY = 'fastsplit_seen_pending_bills';

    const getSeenBills = () => {
        try {
            const raw = localStorage.getItem(BILL_NOTIF_SEEN_KEY);
            const arr = raw ? JSON.parse(raw) : [];
            return Array.isArray(arr) ? new Set(arr.map(String)) : new Set();
        } catch (e) {
            return new Set();
        }
    };

    const setSeenBills = (ids) => {
        try {
            localStorage.setItem(BILL_NOTIF_SEEN_KEY, JSON.stringify(Array.from(ids)));
        } catch (e) {
            // ignore
        }
    };

    const renderBillNotifications = (items) => {
        if (!billNotificationsList || !billNotificationsEmpty) return;

        billNotificationsList.innerHTML = '';
        if (!items || items.length === 0) {
            billNotificationsEmpty.hidden = false;
            return;
        }

        billNotificationsEmpty.hidden = true;
        items.forEach((it) => {
            const li = document.createElement('li');
            li.className = 'notification-item';
            li.innerHTML = `
                <span>
                    Nowe rozliczenie od <strong>${escapeHtml(it.creator)}</strong>: ${escapeHtml(it.description)}
                    <br />
                    <small style="opacity:0.8;">Twój udział: <strong>${escapeHtml(it.amount_owed)} PLN</strong></small>
                </span>
                <div>
                    <button type="button" class="btn-accept" data-accept-bill-id="${escapeHtml(it.bill_id)}">Akceptuj</button>
                    <button type="button" class="btn-reject" data-reject-bill-id="${escapeHtml(it.bill_id)}">Odrzuć</button>
                </div>
            `;

            const acceptBtn = li.querySelector('button[data-accept-bill-id]');
            if (acceptBtn) {
                acceptBtn.addEventListener('click', async () => {
                    if (!csrfToken) {
                        showToast('Brak tokenu CSRF – odśwież stronę.', 'error');
                        return;
                    }
                    acceptBtn.disabled = true;
                    try {
                        const res = await fetch(`/bill/${encodeURIComponent(it.bill_id)}/accept/`, {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrfToken,
                                'X-Requested-With': 'XMLHttpRequest',
                                'Accept': 'application/json',
                            },
                        });

                        if (!res.ok) {
                            acceptBtn.disabled = false;
                            showToast('Nie udało się zaakceptować rozliczenia.', 'error');
                            return;
                        }

                        // Usuń z listy (bez przeładowania)
                        li.remove();
                        const remainingItems = billNotificationsList.querySelectorAll('.notification-item').length;
                        if (remainingItems === 0) billNotificationsEmpty.hidden = false;

                        // Badge: zmniejsz o 1, ale nie poniżej 0
                        const currentBadge = notificationsBadge && !notificationsBadge.hidden ? Number(notificationsBadge.textContent) || 0 : 0;
                        updateBadge(Math.max(0, currentBadge - 1));

                        showToast('Zaakceptowano rozliczenie.', 'success');
                        // Odśwież, żeby prawy panel pokazał zaakceptowane PENDING
                        window.location.reload();
                    } catch (e) {
                        acceptBtn.disabled = false;
                        showToast('Błąd sieci przy akceptacji.', 'error');
                    }
                });
            }

            const rejectBtn = li.querySelector('button[data-reject-bill-id]');
            if (rejectBtn) {
                rejectBtn.addEventListener('click', async () => {
                    if (!csrfToken) {
                        showToast('Brak tokenu CSRF – odśwież stronę.', 'error');
                        return;
                    }
                    rejectBtn.disabled = true;
                    try {
                        const res = await fetch(`/bill/${encodeURIComponent(it.bill_id)}/reject/`, {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrfToken,
                                'X-Requested-With': 'XMLHttpRequest',
                                'Accept': 'application/json',
                            },
                        });

                        if (!res.ok) {
                            rejectBtn.disabled = false;
                            showToast('Nie udało się odrzucić rozliczenia.', 'error');
                            return;
                        }

                        li.remove();
                        const remainingItems = billNotificationsList.querySelectorAll('.notification-item').length;
                        if (remainingItems === 0) billNotificationsEmpty.hidden = false;

                        const currentBadge = notificationsBadge && !notificationsBadge.hidden ? Number(notificationsBadge.textContent) || 0 : 0;
                        updateBadge(Math.max(0, currentBadge - 1));

                        showToast('Odrzucono rozliczenie.', 'info');
                        window.location.reload();
                    } catch (e) {
                        rejectBtn.disabled = false;
                        showToast('Błąd sieci przy odrzuceniu.', 'error');
                    }
                });
            }
            billNotificationsList.appendChild(li);
        });
    };

    const updateBadge = (count) => {
        if (!notificationsBadge) return;
        const n = Number(count) || 0;
        notificationsBadge.textContent = String(n);
        notificationsBadge.hidden = n <= 0;
    };

    const fetchBillNotifications = async () => {
        if (!billNotificationsList || !billNotificationsEmpty) return;
        try {
            const res = await fetch('/notifications/pending-bills/', { headers: { 'Accept': 'application/json' } });
            if (!res.ok) return;
            const payload = await res.json();
            const pending = Array.isArray(payload.pending) ? payload.pending : [];

            const seen = getSeenBills();
            let hasNew = false;
            pending.forEach((p) => {
                const id = String(p.bill_id);
                if (!seen.has(id)) {
                    hasNew = true;
                    seen.add(id);
                }
            });

            // Render listy
            renderBillNotifications(pending);

            // Badge: tylko dla rachunków (friend_requests już są w HTML; tutaj dokładamy pending bills)
            // Najprościej: ustawiamy badge na max(istniejący, pending.length) jeśli nie umiemy odczytać friend_requests.
            // Gdy badge już ma liczbę z serwera (notifications_count), podbijamy o różnicę.
            const currentBadge = notificationsBadge && !notificationsBadge.hidden ? Number(notificationsBadge.textContent) || 0 : 0;
            const computed = Math.max(currentBadge, pending.length);
            updateBadge(computed);

            if (hasNew) {
                setSeenBills(seen);
                showToast('Masz nowe rozliczenie do akceptacji.', 'info');
            }
        } catch (e) {
            // ignore
        }
    };

    // Start: pobierz od razu + potem co 10s (tylko jeśli sekcja istnieje)
    if (billNotificationsList && billNotificationsEmpty) {
        fetchBillNotifications();
        setInterval(fetchBillNotifications, 10000);
    }

    const closeNotifications = () => {
        if (!notificationsToggle || !notificationsPanel) return;
        notificationsPanel.hidden = true;
        notificationsToggle.setAttribute('aria-expanded', 'false');
    };

    const openNotifications = () => {
        if (!notificationsToggle || !notificationsPanel) return;
        notificationsPanel.hidden = false;
        notificationsToggle.setAttribute('aria-expanded', 'true');
    };

    const toggleNotifications = () => {
        if (!notificationsToggle || !notificationsPanel) return;
        if (notificationsPanel.hidden) openNotifications();
        else closeNotifications();
    };

    if (notificationsToggle && notificationsPanel) {
        notificationsToggle.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleNotifications();
        });

        notificationsPanel.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        document.addEventListener('click', () => closeNotifications());
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeNotifications();
        });
    }

    // --- WYSZUKIWANIE UŻYTKOWNIKÓW (dropdown + Zaproś) ---
    const searchForm = document.querySelector('.search-friend form');
    const searchInput = document.getElementById('user-search-input');
    const searchResults = document.getElementById('search-results');
    const csrfTokenInput = document.querySelector('.search-friend input[name="csrfmiddlewaretoken"]');

    let searchDebounceId = null;
    let lastQuery = '';

    const closeSearchResults = () => {
        if (!searchResults) return;
        searchResults.hidden = true;
        searchResults.innerHTML = '';
    };

    const openSearchResults = () => {
        if (!searchResults) return;
        searchResults.hidden = false;
    };

    const renderSearchResults = (items) => {
        if (!searchResults) return;
        searchResults.innerHTML = '';

        if (!Array.isArray(items) || items.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'search-result-empty';
            empty.textContent = 'Brak wyników.';
            searchResults.appendChild(empty);
            openSearchResults();
            return;
        }

        items.forEach((u) => {
            const row = document.createElement('div');
            row.className = 'search-result-item';

            const name = document.createElement('div');
            name.className = 'search-result-name';
            name.textContent = u.username;

            const right = document.createElement('div');
            right.className = 'search-result-actions';

            const status = String(u && u.status ? u.status : '').trim();

            const renderInviteButton = () => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'search-invite-btn';
                btn.textContent = 'Zaproś';
                btn.addEventListener('click', async () => {
                    btn.disabled = true;
                    try {
                        const res = await fetch('/invite_user/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                                'X-CSRFToken': csrfTokenInput ? csrfTokenInput.value : ''
                            },
                            body: new URLSearchParams({ user_id: String(u.id) }).toString()
                        });
                        const data = await res.json().catch(() => ({}));
                        if (!res.ok) {
                            showToast(data && data.message ? data.message : 'Nie udało się wysłać zaproszenia.', 'error');
                            btn.disabled = false;
                            return;
                        }
                        showToast(data.message || 'Wysłano zaproszenie.', 'success');
                        right.innerHTML = '';
                        const s = document.createElement('span');
                        s.className = 'search-result-status';
                        s.textContent = 'Wysłano';
                        right.appendChild(s);
                    } catch (e) {
                        showToast('Błąd sieci podczas wysyłania zaproszenia.', 'error');
                        btn.disabled = false;
                    }
                });
                right.appendChild(btn);
            };

            if (status === 'friend') {
                const s = document.createElement('span');
                s.className = 'search-result-status';
                s.textContent = 'Już znajomy';
                right.appendChild(s);
            } else if (status === 'pending_sent') {
                const s = document.createElement('span');
                s.className = 'search-result-status';
                s.textContent = 'Wysłano';
                right.appendChild(s);
            } else if (status === 'pending_received') {
                const s = document.createElement('span');
                s.className = 'search-result-status';
                s.textContent = 'Masz zaproszenie';
                right.appendChild(s);
            } else {
                // domyślnie pokazuj przycisk (np. gdy backend zwróci brak statusu)
                renderInviteButton();
            }

            row.appendChild(name);
            row.appendChild(right);
            searchResults.appendChild(row);
        });

        openSearchResults();
    };

    const runSearch = async (q) => {
        if (!searchResults) return;
        const query = String(q || '').trim();
        lastQuery = query;

        if (query.length < 2) {
            closeSearchResults();
            return;
        }

        try {
            const res = await fetch(`/search_user/?q=${encodeURIComponent(query)}`, { headers: { 'Accept': 'application/json' } });
            if (!res.ok) {
                closeSearchResults();
                return;
            }
            const data = await res.json();
            // jeśli w międzyczasie wpisano coś innego
            if (lastQuery !== query) return;
            renderSearchResults((data && data.results) || []);
        } catch (e) {
            closeSearchResults();
        }
    };

    if (searchInput && searchResults) {
        searchInput.addEventListener('input', () => {
            if (searchDebounceId) clearTimeout(searchDebounceId);
            searchDebounceId = setTimeout(() => runSearch(searchInput.value), 250);
        });

        searchInput.addEventListener('focus', () => {
            if (searchResults.innerHTML.trim() && !searchResults.hidden) return;
            if (searchInput.value && String(searchInput.value).trim().length >= 2) {
                runSearch(searchInput.value);
            }
        });

        document.addEventListener('click', (e) => {
            const target = e.target;
            if (!target) return;
            if (searchResults.contains(target) || searchInput.contains(target)) return;
            closeSearchResults();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeSearchResults();
        });
    }

    if (searchForm && searchInput) {
        searchForm.addEventListener('submit', (e) => {
            // nie rób auto-zapraszania po Enter; tylko pokaż listę
            e.preventDefault();
            runSearch(searchInput.value);
        });
    }

    const form = document.getElementById('split-form');
    const selectedFriendsContainer = document.getElementById('selected-friends');
    const splitDetails = document.getElementById('split-details');
    const amountInput = document.getElementById('amount');
    const tipInput = document.getElementById('tip');
    const chooseBtn = document.getElementById('choose-friends-button');
    const closePopupBtn = document.getElementById('close-popup');

    if (chooseBtn) chooseBtn.addEventListener('click', () => document.getElementById('popup-container').style.display = 'block');
    if (closePopupBtn) closePopupBtn.addEventListener('click', hidePopup);
    if (form) form.addEventListener('submit', handleFormSubmit);

    // Reset przy zmianie kwot
    if (amountInput) amountInput.addEventListener('input', () => {
        refreshSlidersLimit();
    });
    if (tipInput) tipInput.addEventListener('input', () => {
        refreshSlidersLimit();
    });

    function hidePopup() {
        document.getElementById('popup-container').style.display = 'none';
        updateSelectedFriends();
    }

    // --- WYBÓR ZNAJOMYCH ---
    function updateSelectedFriends() {
        selectedFriendsContainer.innerHTML = '';
        const checkedBoxes = document.querySelectorAll('#popup-friends-list input[type="checkbox"]:checked');

        let selectedList = Array.from(checkedBoxes).map(checkbox => ({
            id: checkbox.value,
            name: checkbox.dataset.name
        }));

        // Dodajemy SIEBIE
        const myIdInput = document.getElementById('logged-in-user-id');
        const myNameInput = document.getElementById('logged-in-user-name');

        if (myIdInput && myNameInput) {
            if (!selectedList.some(p => p.id === myIdInput.value)) {
                selectedList.unshift({
                    id: myIdInput.value,
                    name: myNameInput.value + " (Ja)"
                });
            }
        }

        if (selectedList.length > 0) {
            const ul = document.createElement('ul');
            selectedList.forEach(person => {
                const li = document.createElement('li');
                li.textContent = person.name;
                li.dataset.id = person.id;
                ul.appendChild(li);
            });
            selectedFriendsContainer.appendChild(ul);
        } else {
            selectedFriendsContainer.innerHTML = '<p>Nie wybrano nikogo.</p>';
        }

        generateSliders(selectedList);
    }

    // --- SLIDERY ---
    function generateSliders(friendsList) {
        splitDetails.innerHTML = '';

        // Nowa lista / nowe suwaki: resetujemy locki
        lockedFriendIds.clear();
        lockOrder.length = 0;

        let totalAmount = calculateTotal();
        let sliderMax = totalAmount > 0 ? totalAmount : 100;

        if (friendsList.length === 0) return;

        const initialAmount = totalAmount > 0 ? (totalAmount / friendsList.length).toFixed(2) : 0;

        friendsList.forEach(person => {
            const container = document.createElement('div');
            container.classList.add('slider-container');
            container.style.cssText = "display: flex; align-items: center; margin-bottom: 10px;";

            const label = document.createElement('label');
            label.textContent = person.name;
            label.style.cssText = "width: 100px; margin-right: 10px; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;";
            container.appendChild(label);

            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = 0;
            slider.max = sliderMax;
            slider.step = 0.01;
            slider.value = initialAmount;
            slider.dataset.friendId = person.id;
            slider.style.flexGrow = "1";
            container.appendChild(slider);

            const numberInput = document.createElement('input');
            numberInput.type = 'number';
            numberInput.step = '0.01';
            numberInput.min = '0';
            numberInput.max = sliderMax;
            numberInput.value = initialAmount;
            numberInput.style.cssText = "width: 70px; margin-left: 10px; text-align: center;";
            container.appendChild(numberInput);

            const percentSpan = document.createElement('span');
            percentSpan.style.cssText = "width: 45px; margin-left: 5px; font-size: 0.8em; color: grey; text-align: right;";

            const updatePercent = (val) => {
                let p = totalAmount > 0 ? ((val / totalAmount) * 100).toFixed(0) : 0;
                percentSpan.textContent = `${p}%`;
            };
            updatePercent(initialAmount);
            container.appendChild(percentSpan);
            numberInput.percentDisplay = percentSpan;

            const handleInput = (val) => {
                numberInput.value = val;
                slider.value = val;
                updatePercent(val);
                balanceRevolutStyle(slider, friendsList);
            };

            slider.addEventListener('input', () => handleInput(slider.value));
            numberInput.addEventListener('input', () => {
                let val = parseFloat(numberInput.value);
                if (val > sliderMax) val = sliderMax;
                if (isNaN(val) || val < 0) val = 0;
                handleInput(val);
            });

            splitDetails.appendChild(container);
        });
    }

    function calculateTotal() {
        let base = parseFloat(amountInput.value) || 0;
        let tip = parseFloat(tipInput.value) || 0;
        return base + (base * (tip / 100));
    }

    function refreshSlidersLimit() {
        let newTotal = calculateTotal();
        const sliders = Array.from(document.querySelectorAll('#split-details input[type="range"]'));
        const inputs = Array.from(document.querySelectorAll('#split-details input[type="number"]'));

        if (sliders.length === 0) return;

        sliders.forEach((slider, index) => {
            slider.max = newTotal > 0 ? newTotal : 100;
            inputs[index].max = slider.max;
        });

        // Nie resetuj do równego podziału.
        // Zachowaj dotychczasowe wartości (locked pozostają), a resztę dopasuj do nowej puli.
        rebalanceSlidersToTotal({ lockActive: false });
    }

    function getSliderPairs() {
        const sliders = Array.from(document.querySelectorAll('#split-details input[type="range"]'));
        const inputs = Array.from(document.querySelectorAll('#split-details input[type="number"]'));
        return sliders.map((slider, i) => ({
            id: String(slider.dataset.friendId || ''),
            slider,
            input: inputs[i]
        }));
    }

    function syncPair(pair, cents, totalCents) {
        const value = Math.max(0, roundToCents(fromCents(cents)));
        pair.slider.value = value.toFixed(2);
        if (pair.input) {
            pair.input.value = value.toFixed(2);
            if (pair.input.percentDisplay) {
                const p = totalCents > 0 ? Math.round((cents / totalCents) * 100) : 0;
                pair.input.percentDisplay.textContent = `${p}%`;
            }
        }
    }

    function rebalanceSlidersToTotal(opts = {}) {
        const { activeId = null, activeCents = null, lockActive = false } = opts;
        const pairs = getSliderPairs();
        let totalAmount = calculateTotal();
        if (!Number.isFinite(totalAmount) || totalAmount < 0) totalAmount = 0;
        const totalCents = Math.max(0, toCents(totalAmount));

        if (pairs.length === 0) return;

        const values = new Map();
        pairs.forEach((p) => {
            const raw = parseFloat(p.slider.value);
            values.set(p.id, Math.max(0, toCents(Number.isFinite(raw) ? raw : 0)));
        });

        const activeKey = activeId != null ? String(activeId) : null;
        if (activeKey && lockActive) lockId(activeKey);

        // Gdy wszyscy są "locked", zmiana aktywnej osoby nie ma gdzie się zbilansować,
        // więc UI wygląda jakby suwak był zablokowany (wartość natychmiast wraca).
        // Rozwiązanie: w tej iteracji traktujemy jedną INNĄ osobę jako balansującą
        // (tymczasowo "odmrażamy" ją), żeby aktywny suwak dało się zmniejszać/zwiększać.
        const effectiveLocked = new Set(lockedFriendIds);
        if (pairs.length > 1 && effectiveLocked.size === pairs.length) {
            const fallbackId = pairs.find((p) => p.id !== activeKey)?.id || null;
            const balancingId = lockOrder.find((id) => id !== activeKey) || fallbackId;
            if (balancingId) effectiveLocked.delete(String(balancingId));
        }

        if (activeKey && activeCents != null) {
            const v = Math.max(0, Math.min(Number(activeCents) || 0, totalCents));
            values.set(activeKey, v);
        }

        // Suma "zamrożonych" (efektywnie; z ewentualnym balansującym wyjątkiem)
        const lockedIds = Array.from(effectiveLocked);
        let lockedSum = 0;
        lockedIds.forEach((id) => {
            lockedSum += values.get(id) || 0;
        });

        // Jeśli pula się nie domyka (np. po zmianie rachunku) i locki przekraczają total,
        // obcinamy ostatnio ustawianą osobę (najczęściej bieżącą).
        if (lockedSum > totalCents) {
            const overshoot = lockedSum - totalCents;
            const adjustId = activeKey || (lockOrder.length ? lockOrder[lockOrder.length - 1] : null);
            if (adjustId && values.has(adjustId)) {
                const current = values.get(adjustId) || 0;
                const next = Math.max(0, current - overshoot);
                values.set(adjustId, next);
            }
            // przelicz ponownie po korekcie
            lockedSum = 0;
            lockedIds.forEach((id) => {
                lockedSum += values.get(id) || 0;
            });
        }

        let remaining = totalCents - lockedSum;
        if (remaining < 0) remaining = 0;

        const unlocked = pairs.filter((p) => !effectiveLocked.has(p.id));

        if (unlocked.length > 0) {
            const currentUnlockedSum = unlocked.reduce((sum, p) => sum + (values.get(p.id) || 0), 0);

            if (currentUnlockedSum <= 0) {
                // Jeśli wszystko ma 0, rozdziel równo
                const n = unlocked.length;
                const per = n > 0 ? Math.floor(remaining / n) : 0;
                let used = 0;
                for (let i = 0; i < n - 1; i++) {
                    values.set(unlocked[i].id, per);
                    used += per;
                }
                values.set(unlocked[n - 1].id, Math.max(0, remaining - used));
            } else {
                // Proporcjonalnie do dotychczasowych wartości (brak efektu "resetu")
                let used = 0;
                for (let i = 0; i < unlocked.length - 1; i++) {
                    const id = unlocked[i].id;
                    const base = values.get(id) || 0;
                    const v = Math.floor((remaining * base) / currentUnlockedSum);
                    values.set(id, v);
                    used += v;
                }
                const lastId = unlocked[unlocked.length - 1].id;
                values.set(lastId, Math.max(0, remaining - used));
            }
        } else {
            // Wszyscy są "locked" – domknij sumę na aktywnym/ostatnim locked, jeśli potrzeba.
            const diff = totalCents - lockedSum;
            if (diff !== 0) {
                const adjustId = activeKey || (lockOrder.length ? lockOrder[lockOrder.length - 1] : null);
                if (adjustId && values.has(adjustId)) {
                    values.set(adjustId, Math.max(0, (values.get(adjustId) || 0) + diff));
                }
            }
        }

        // Zapisz na UI
        pairs.forEach((p) => {
            syncPair(p, values.get(p.id) || 0, totalCents);
        });
    }

    function balanceRevolutStyle(activeSlider, friendsList) {
        const friendId = String(activeSlider.dataset.friendId || '');
        const raw = parseFloat(activeSlider.value);
        const v = Math.max(0, toCents(Number.isFinite(raw) ? raw : 0));

        // Aktywnie ustawiana osoba staje się "locked" (kumulacyjnie), a reszta dopasowuje się do pozostałej puli.
        rebalanceSlidersToTotal({ activeId: friendId, activeCents: v, lockActive: true });
    }

    // --- WYSYŁANIE ---
    function handleFormSubmit(event) {
        event.preventDefault();
        const submitBtn = form.querySelector('button, input[type="submit"]');
        if (submitBtn && submitBtn.disabled) return;

        const inputs = Array.from(document.querySelectorAll('#split-details input[type="number"]'));
        let currentSum = inputs.reduce((sum, i) => sum + parseFloat(i.value), 0);
        let total = calculateTotal();

        if (Math.abs(currentSum - total) > 0.5) {
            showToast(`Suma (${currentSum.toFixed(2)}) nie zgadza się z rachunkiem (${total.toFixed(2)})!`, "error");
            return;
        }

        if (submitBtn) submitBtn.disabled = true;
        createSpill(submitBtn);
    }

    function createSpill(submitBtn) {
        const amount = amountInput.value;
        const tip = tipInput.value;
        // 1. POBIERAMY NAZWĘ Z INPUTA (który przywróciłem w HTML)
        const descriptionInput = document.getElementById('bill-name');
        const description = descriptionInput ? descriptionInput.value : "Rachunek";

        let customSplits = [];
        const sliders = document.querySelectorAll('#split-details input[type="range"]');
        sliders.forEach(s => {
            customSplits.push({
                id: s.dataset.friendId,
                amount: s.value
            });
        });

        const selectedFriendsIds = Array.from(document.querySelectorAll('#selected-friends li')).map(li => li.dataset.id);
        const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();

        if (!csrftoken) {
            showToast("Błąd CSRF!", "error");
            if (submitBtn) submitBtn.disabled = false;
            return;
        }

        $.ajax({
            url: '/create_spill/',
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            mode: 'same-origin',
            data: {
                'amount': amount,
                'tip': tip,
                'description': description, // 2. Wysyłamy nazwę
                'friends[]': selectedFriendsIds,
                'custom_splits': JSON.stringify(customSplits)
            },
            success: function (response) {
                showToast("✅ Rachunek utworzony pomyślnie!", "success");

                // Czyścimy wszystko
                if (descriptionInput) descriptionInput.value = '';
                amountInput.value = '';
                tipInput.value = '';
                splitDetails.innerHTML = '';
                selectedFriendsContainer.innerHTML = '';
                if (submitBtn) submitBtn.disabled = false;

                // Odśwież, żeby od razu zobaczyć nowy rachunek w prawym panelu
                setTimeout(() => window.location.reload(), 700);
            },
            error: function (xhr) {
                showToast("❌ Błąd: " + xhr.status + " " + xhr.responseText, "error");
                if (submitBtn) submitBtn.disabled = false;
            }
        });
    }

});

// --- FUNKCJE GLOBALNE ---
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) {
        alert(message);
        return;
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 5000);
}

// Pokazuj komunikaty Django (messages) jako toasty na dashboardzie
(function () {
    const items = window.__DJANGO_MESSAGES__;
    if (!Array.isArray(items) || items.length === 0) return;

    const toType = (tags) => {
        const t = String(tags || '');
        if (t.includes('error')) return 'error';
        if (t.includes('success')) return 'success';
        return 'info';
    };

    items.forEach((m) => {
        if (!m || !m.text) return;
        showToast(m.text, toType(m.tags));
    });

    // zabezpieczenie przed ponownym pokazaniem po navigacji
    window.__DJANGO_MESSAGES__ = [];
})();

function selectGroupMembers(selectElement) {
    const checkboxes = document.querySelectorAll('#popup-friends-list input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);

    const idsString = selectElement.value;
    if (!idsString) {
        if (checkboxes.length > 0) checkboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
        return;
    }

    const idsToSelect = idsString.split(',').filter(id => id);
    idsToSelect.forEach(id => {
        const cb = document.querySelector(`#popup-friends-list input[value="${id}"]`);
        if (cb) cb.checked = true;
    });

    const firstChecked = document.querySelector('#popup-friends-list input[type="checkbox"]:checked');
    if (firstChecked) {
        firstChecked.dispatchEvent(new Event('change', { bubbles: true }));
    }
}