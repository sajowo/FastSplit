document.addEventListener('DOMContentLoaded', function () {
    
    // --- ZABEZPIECZENIE PRZED PODWÓJNYM ŁADOWANIEM ---
    // Jeśli skrypt załaduje się 2 razy, ta linijka go zatrzyma za drugim razem.
    if (window.scriptHasRun) return;
    window.scriptHasRun = true;

    // --- SEKCJA 1: MOTYWY ---
    const themeSwitch = document.getElementById('theme-switch');
    const body = document.body;

    if (themeSwitch) {
        themeSwitch.addEventListener('change', function () {
            body.classList.toggle('dark-theme');
        });
    }

    function toggleThemeByTime() {
        const currentHour = new Date().getHours();
        if (currentHour >= 17) {
            body.classList.add('dark-theme');
        } else {
            body.classList.remove('dark-theme');
        }
    }

    toggleThemeByTime();
    setInterval(toggleThemeByTime, 3600000);

    // --- SEKCJA 2: ZMIENNE FORMULARZA ---
    const form = document.getElementById('split-form');
    const selectedFriendsContainer = document.getElementById('selected-friends');
    const splitDetails = document.getElementById('split-details');
    const amountInput = document.getElementById('amount');
    const tipInput = document.getElementById('tip');
    const spillResults = document.getElementById('spill-results');

    // --- SEKCJA 3: EVENT LISTENERY ---
    function initializeEventListeners() {
        const chooseBtn = document.getElementById('choose-friends-button');
        const closePopupBtn = document.getElementById('close-popup');
        
        if (chooseBtn) chooseBtn.addEventListener('click', showPopup);
        if (closePopupBtn) closePopupBtn.addEventListener('click', hidePopup);
        
        // Tutaj podpinamy wysyłanie formularza
        if (form) form.addEventListener('submit', handleFormSubmit);
    }

    // --- SEKCJA 4: LOGIKA POPUPÓW I SLIDERÓW ---
    function showPopup() {
        document.getElementById('popup-container').style.display = 'block';
    }

    function hidePopup() {
        document.getElementById('popup-container').style.display = 'none';
        updateSelectedFriends();
    }

    function updateSelectedFriends() {
        selectedFriendsContainer.innerHTML = '';
        const selectedFriends = Array.from(document.querySelectorAll('#popup-friends-list input[type="checkbox"]:checked')).map(checkbox => checkbox.value);

        const loggedInUserInput = document.getElementById('logged-in-user');
        if (loggedInUserInput) {
             const loggedInUser = loggedInUserInput.value;
             if (!selectedFriends.includes(loggedInUser)) {
                selectedFriends.unshift(loggedInUser);
            }
        }

        if (selectedFriends.length > 0) {
            const friendsList = document.createElement('ul');
            selectedFriends.forEach(friend => {
                const listItem = document.createElement('li');
                listItem.textContent = friend;
                // friend to nazwa użytkownika (np. "admin")
                listItem.dataset.id = friend; 
                friendsList.appendChild(listItem);
            });
            selectedFriendsContainer.appendChild(friendsList);
        } else {
            selectedFriendsContainer.innerHTML = '<p>Nie wybrano znajomych.</p>';
        }

        generateSliders(selectedFriends);
    }

    function generateSliders(friends) {
        splitDetails.innerHTML = '';
        let baseAmount = parseFloat(amountInput.value) || 0;
        let tipPercent = parseFloat(tipInput.value) || 0;
        let totalAmount = baseAmount + (baseAmount * (tipPercent / 100));
        
        if (friends.length === 0) return;
        
        const initialAmount = (totalAmount / friends.length).toFixed(2);

        friends.forEach(friend => {
            const sliderContainer = document.createElement('div');
            sliderContainer.classList.add('slider-container');

            const nameLabel = document.createElement('label');
            nameLabel.textContent = friend + ':';
            sliderContainer.appendChild(nameLabel);

            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = 0;
            slider.max = totalAmount + 1;
            slider.step = 0.01;
            slider.value = initialAmount;
            slider.dataset.friend = friend;
            sliderContainer.appendChild(slider);

            const sliderValue = document.createElement('span');
            sliderValue.textContent = initialAmount;
            sliderContainer.appendChild(sliderValue);

            slider.addEventListener('input', () => {
                sliderValue.textContent = slider.value;
                updateSliderValues();
            });

            splitDetails.appendChild(sliderContainer);
        });
    }

    function updateSliderValues() {
        const sliders = Array.from(document.querySelectorAll('#split-details input[type="range"]'));
        let baseAmount = parseFloat(amountInput.value) || 0;
        let tipPercent = parseFloat(tipInput.value) || 0;
        let totalAmount = baseAmount + (baseAmount * (tipPercent / 100));
        
        let totalSelected = sliders.reduce((total, slider) => total + parseFloat(slider.value), 0);

        if (totalSelected > totalAmount) {
            let excess = totalSelected - totalAmount;
            sliders.forEach(slider => {
                let value = parseFloat(slider.value);
                if (value > 0 && excess > 0) {
                    let reduction = Math.min(value, excess);
                    slider.value = (value - reduction).toFixed(2);
                    slider.nextSibling.textContent = slider.value;
                    excess -= reduction;
                }
            });
        }
    }

    // --- SEKCJA 5: NAPRAWIONE ZABEZPIECZENIE PRZED DUPLIKATAMI ---
    function handleFormSubmit(event) {
        event.preventDefault();

        // 1. Znajdujemy przycisk, który wysyła formularz
        const submitBtn = form.querySelector('button, input[type="submit"]');

        // 2. Jeśli przycisk jest już zablokowany, to znaczy, że ktoś klika jak szalony -> przerywamy
        if (submitBtn && submitBtn.disabled) {
            return; 
        }

        // 3. Blokujemy przycisk, żeby nie dało się kliknąć drugi raz
        if (submitBtn) {
            submitBtn.disabled = true;
            // Opcjonalnie: zmieniamy tekst, żeby user widział reakcję
            // submitBtn.innerText = "Przetwarzanie..."; 
        }

        // 4. Dopiero teraz wywołujemy funkcję tworzącą
        createSpill(submitBtn);
    }

    function createSpill(submitBtn) {
        const amount = amountInput.value;
        const tip = tipInput.value;
        
        // Pobieranie nazw użytkowników (np. "admin", "testowy")
        const selectedFriends = Array.from(selectedFriendsContainer.querySelectorAll('li')).map(li => li.dataset.id);

        // Pobieranie tokena CSRF z HTML
        const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();

        if (!csrftoken) {
            alert("Błąd: Nie znaleziono tokena CSRF. Odśwież stronę.");
            if (submitBtn) submitBtn.disabled = false; // Odblokuj przycisk w razie błędu
            return;
        }

        $.ajax({
            url: '/create_spill/',
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            mode: 'same-origin',
            data: {
                'amount': amount,
                'tip': tip,
                'friends[]': selectedFriends
            },
            success: function (response) {
                if(spillResults) spillResults.innerHTML = "Udało się stworzyć rachunek!";
                location.reload(); // Odświeżenie strony (to też odblokuje przycisk)
            },
            error: function (xhr, status, error) {
                alert('Error creating spill: ' + xhr.status + ' ' + xhr.responseText);
                // Jeśli wystąpił błąd, musimy odblokować przycisk, żeby user mógł spróbować ponownie
                if (submitBtn) {
                    submitBtn.disabled = false;
                    // submitBtn.innerText = "Create Spill";
                }
            }
        });
    }

    initializeEventListeners();
});