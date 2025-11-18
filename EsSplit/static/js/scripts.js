document.addEventListener('DOMContentLoaded', function () {
    
    if (window.scriptHasRun) return;
    window.scriptHasRun = true;

    // --- 1. MOTYWY ---
    const themeSwitch = document.getElementById('theme-switch');
    const body = document.body;
    if (themeSwitch) {
        themeSwitch.addEventListener('change', () => body.classList.toggle('dark-theme'));
    }
    function toggleThemeByTime() {
        if (new Date().getHours() >= 17) body.classList.add('dark-theme');
        else body.classList.remove('dark-theme');
    }
    toggleThemeByTime();
    setInterval(toggleThemeByTime, 3600000);

    // --- 2. ZMIENNE ---
    const form = document.getElementById('split-form');
    const selectedFriendsContainer = document.getElementById('selected-friends');
    const splitDetails = document.getElementById('split-details');
    const amountInput = document.getElementById('amount');
    const tipInput = document.getElementById('tip');
    const spillResults = document.getElementById('spill-results');

    // --- 3. EVENT LISTENERY ---
    const chooseBtn = document.getElementById('choose-friends-button');
    const closePopupBtn = document.getElementById('close-popup');
    
    if (chooseBtn) chooseBtn.addEventListener('click', () => document.getElementById('popup-container').style.display = 'block');
    if (closePopupBtn) closePopupBtn.addEventListener('click', hidePopup);
    if (form) form.addEventListener('submit', handleFormSubmit);

    function hidePopup() {
        document.getElementById('popup-container').style.display = 'none';
        updateSelectedFriends();
    }

    // --- 4. LOGIKA WYBORU ZNAJOMYCH (ZMIENIONA) ---
    function updateSelectedFriends() {
        selectedFriendsContainer.innerHTML = '';
        
        // Pobieramy zaznaczone checkboxy i tworzymy obiekty {id, name}
        const checkedBoxes = document.querySelectorAll('#popup-friends-list input[type="checkbox"]:checked');
        let selectedList = Array.from(checkedBoxes).map(checkbox => {
            return {
                id: checkbox.value,              // ID z value
                name: checkbox.dataset.name      // Nazwa z data-name
            };
        });

        // Dodajemy zalogowanego użytkownika (Ciebie) do listy
        const myIdInput = document.getElementById('logged-in-user-id');
        const myNameInput = document.getElementById('logged-in-user-name');

        if (myIdInput && myNameInput) {
            const myId = myIdInput.value;
            const myName = myNameInput.value;
            
            // Sprawdzamy czy już nie jesteś na liście (dla pewności)
            const alreadyInList = selectedList.some(f => f.id === myId);
            if (!alreadyInList) {
                selectedList.unshift({ id: myId, name: myName });
            }
        }

        // Generowanie listy wizualnej (pod formularzem)
        if (selectedList.length > 0) {
            const ul = document.createElement('ul');
            selectedList.forEach(person => {
                const li = document.createElement('li');
                li.textContent = person.name;   // Wyświetlamy NAZWĘ
                li.dataset.id = person.id;      // Przechowujemy ID ukryte
                ul.appendChild(li);
            });
            selectedFriendsContainer.appendChild(ul);
        } else {
            selectedFriendsContainer.innerHTML = '<p>Nie wybrano znajomych.</p>';
        }

        generateSliders(selectedList);
    }

    function generateSliders(friendsList) {
        splitDetails.innerHTML = '';
        let baseAmount = parseFloat(amountInput.value) || 0;
        let tipPercent = parseFloat(tipInput.value) || 0;
        let totalAmount = baseAmount + (baseAmount * (tipPercent / 100));
        
        if (friendsList.length === 0) return;
        
        const initialAmount = (totalAmount / friendsList.length).toFixed(2);

        friendsList.forEach(person => {
            const container = document.createElement('div');
            container.classList.add('slider-container');

            const label = document.createElement('label');
            label.textContent = person.name + ':'; // Wyświetlamy NAZWĘ
            container.appendChild(label);

            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = 0;
            slider.max = totalAmount + 1;
            slider.step = 0.01;
            slider.value = initialAmount;
            // dataset przechowuje ID do ewentualnej logiki JS, ale backend i tak dostanie ID z listy <li>
            slider.dataset.friendId = person.id; 
            container.appendChild(slider);

            const valDisplay = document.createElement('span');
            valDisplay.textContent = initialAmount;
            container.appendChild(valDisplay);

            slider.addEventListener('input', () => {
                valDisplay.textContent = slider.value;
                updateSliderValues();
            });

            splitDetails.appendChild(container);
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
                let val = parseFloat(slider.value);
                if (val > 0 && excess > 0) {
                    let reduction = Math.min(val, excess);
                    slider.value = (val - reduction).toFixed(2);
                    slider.nextSibling.textContent = slider.value;
                    excess -= reduction;
                }
            });
        }
    }

    // --- 5. WYSYŁANIE (AJAX) ---
    function handleFormSubmit(event) {
        event.preventDefault();
        const submitBtn = form.querySelector('button, input[type="submit"]');
        if (submitBtn && submitBtn.disabled) return;
        if (submitBtn) submitBtn.disabled = true;
        createSpill(submitBtn);
    }

    function createSpill(submitBtn) {
        const amount = amountInput.value;
        const tip = tipInput.value;
        
        // KLUCZOWA ZMIANA: Pobieramy ID z atrybutu data-id elementów <li>
        const selectedFriendsIds = Array.from(selectedFriendsContainer.querySelectorAll('li'))
                                        .map(li => li.dataset.id);

        const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();

        if (!csrftoken) {
            alert("Błąd CSRF.");
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
                'friends[]': selectedFriendsIds // Wysyłamy listę ID (np. ["1", "5"])
            },
            success: function (response) {
                location.reload();
            },
            error: function (xhr) {
                alert('Błąd: ' + xhr.status);
                if (submitBtn) submitBtn.disabled = false;
            }
        });
    }
});