document.addEventListener('DOMContentLoaded', function () {
    if (window.scriptHasRun) return;
    window.scriptHasRun = true;

    // --- 1. ZMIENNE POMOCNICZE ---
    // Zbiór ID użytkowników, którzy byli edytowani ręcznie (Auto-Lock)
    let touchedUserIds = new Set(); 

    const themeSwitch = document.getElementById('theme-switch');
    const body = document.body;
    if (themeSwitch) themeSwitch.addEventListener('change', () => body.classList.toggle('dark-theme'));

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

    // Resetujemy logikę auto-locka przy zmianie kwoty całkowitej
    if (amountInput) amountInput.addEventListener('input', () => {
        touchedUserIds.clear(); // Nowa kwota = resetujemy "pamięć" blokad
        refreshSlidersLimit();
    });
    if (tipInput) tipInput.addEventListener('input', () => {
        touchedUserIds.clear();
        refreshSlidersLimit();
    });

    function hidePopup() {
        document.getElementById('popup-container').style.display = 'none';
        updateSelectedFriends();
    }

    // --- 2. WYBÓR ZNAJOMYCH ---
    function updateSelectedFriends() {
        selectedFriendsContainer.innerHTML = '';
        const checkedBoxes = document.querySelectorAll('#popup-friends-list input[type="checkbox"]:checked');
        
        // 1. Pobieramy znajomych z checkboxów
        let selectedList = Array.from(checkedBoxes).map(checkbox => ({
            id: checkbox.value,
            name: checkbox.dataset.name
        }));

        // 2. NOWOŚĆ: Dodajemy SIEBIE na początek listy
        const myIdInput = document.getElementById('logged-in-user-id');
        const myNameInput = document.getElementById('logged-in-user-name');

        if (myIdInput && myNameInput) {
            // Unshift dodaje element na początek tablicy
            selectedList.unshift({
                id: myIdInput.value,
                name: myNameInput.value + " (Ja)" // Dodajemy dopisek, żebyś wiedział, że to Ty
            });
        }

        // Resetujemy pamięć blokad (bo zmieniła się liczba osób)
        if (typeof touchedUserIds !== 'undefined') touchedUserIds.clear();

        // 3. Generujemy listę (HTML) i suwaki
        if (selectedList.length > 0) {
            const ul = document.createElement('ul');
            selectedList.forEach(person => {
                // Opcjonalnie: Nie wyświetlaj siebie na liście tekstowej "Wybrani:", 
                // ale suwak musi być. Tutaj wyświetlamy wszystkich.
                const li = document.createElement('li');
                li.textContent = person.name;
                li.dataset.id = person.id;
                ul.appendChild(li);
            });
            selectedFriendsContainer.appendChild(ul);
        } else {
            // Jeśli jakimś cudem lista jest pusta (nawet bez Ciebie)
            selectedFriendsContainer.innerHTML = '<p>Nie wybrano nikogo.</p>';
        }

        generateSliders(selectedList);
    }

    // --- 3. GENEROWANIE SLIDERÓW (LOGIKA REVOLUTA) ---
    function generateSliders(friendsList) {
        splitDetails.innerHTML = '';
        let totalAmount = calculateTotal();
        let sliderMax = totalAmount > 0 ? totalAmount : 100;
        
        if (friendsList.length === 0) return;
        
        const initialAmount = totalAmount > 0 ? (totalAmount / friendsList.length).toFixed(2) : 0;

        friendsList.forEach(person => {
            const container = document.createElement('div');
            container.classList.add('slider-container');
            container.style.cssText = "display: flex; align-items: center; margin-bottom: 10px;";

            // 1. Nazwa
            const label = document.createElement('label');
            label.textContent = person.name;
            label.style.cssText = "width: 100px; margin-right: 10px; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;";
            container.appendChild(label);

            // 2. Suwak
            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = 0;
            slider.max = sliderMax;
            slider.step = 0.01;
            slider.value = initialAmount;
            slider.dataset.friendId = person.id;
            slider.style.flexGrow = "1";
            container.appendChild(slider);

            // 3. Input liczbowy
            const numberInput = document.createElement('input');
            numberInput.type = 'number';
            numberInput.step = '0.01';
            numberInput.min = '0';
            numberInput.max = sliderMax;
            numberInput.value = initialAmount;
            numberInput.style.cssText = "width: 70px; margin-left: 10px; text-align: center;";
            container.appendChild(numberInput);

            // 4. Procenty
            const percentSpan = document.createElement('span');
            percentSpan.style.cssText = "width: 45px; margin-left: 5px; font-size: 0.8em; color: grey; text-align: right;";
            
            const updatePercent = (val) => {
                let p = totalAmount > 0 ? ((val / totalAmount) * 100).toFixed(0) : 0;
                percentSpan.textContent = `${p}%`;
            };
            updatePercent(initialAmount);
            container.appendChild(percentSpan);
            numberInput.percentDisplay = percentSpan; 

            // --- EVENTY (AUTO LOCK) ---
            
            const handleInput = (val) => {
                // 1. Dodajemy aktualną osobę do listy "dotkniętych" (zablokowanych)
                touchedUserIds.add(person.id);

                // 2. Sprawdźmy, czy nie zablokowaliśmy WSZYSTKICH
                // Jeśli ruszam ostatnią niezablokowaną osobą, to system musi "odblokować" resztę,
                // żeby mieć skąd brać pieniądze. (Revolut Soft Reset)
                if (touchedUserIds.size === friendsList.length) {
                    touchedUserIds.clear();
                    touchedUserIds.add(person.id); // Zostawiamy tylko tę, którą teraz trzymam
                }

                // 3. Aktualizacja UI
                numberInput.value = val;
                slider.value = val;
                updatePercent(val);

                // 4. Balansowanie reszty
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
        
        // Nie wywołujemy balanceAmounts na starcie, bo start jest równy
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
        
        let newShare = (newTotal / sliders.length).toFixed(2);

        sliders.forEach((slider, index) => {
            slider.max = newTotal > 0 ? newTotal : 100;
            slider.value = newShare;
            inputs[index].max = slider.max;
            inputs[index].value = newShare;
            if(inputs[index].percentDisplay) inputs[index].percentDisplay.textContent = newTotal > 0 ? ((newShare/newTotal)*100).toFixed(0)+'%' : '0%';
        });
    }

    // --- LOGIKA REVOLUTA (BALANSER) ---
    function balanceRevolutStyle(activeSlider, friendsList) {
        const sliders = Array.from(document.querySelectorAll('#split-details input[type="range"]'));
        const inputs = Array.from(document.querySelectorAll('#split-details input[type="number"]'));
        let totalAmount = calculateTotal();

        // 1. Obliczamy sumę zablokowanych (tych w touchedUserIds), ale BEZ aktywnego slidera
        // (Aktywny slider traktujemy jako "Master", a reszta touched to "Locked")
        let lockedSum = 0;
        let activeValue = parseFloat(activeSlider.value);
        let unlockedSliders = [];
        let unlockedInputs = [];

        sliders.forEach((s, index) => {
            // Jeśli to ten suwak, którym ruszam - pomiń w sumowaniu (już mamy activeValue)
            if (s === activeSlider) return;

            let fId = s.dataset.friendId;

            // Jeśli jest na liście dotkniętych -> jest ZABLOKOWANY (nie zmieniaj go)
            if (touchedUserIds.has(fId)) {
                lockedSum += parseFloat(s.value);
            } else {
                // Jeśli nie był dotykany -> to on przyjmie zmianę
                unlockedSliders.push(s);
                unlockedInputs.push(inputs[index]);
            }
        });

        // 2. Ile zostało do rozdania dla "dziewiczych" (niedotykanych) suwaków?
        // Reszta = Total - (To co trzymam) - (To co zablokowane u innych)
        let remainingForUntouched = totalAmount - activeValue - lockedSum;

        // Jeśli nie ma komu oddać (wszyscy zablokowani) - logika wyżej (Soft Reset) powinna była zadziałać.
        // Ale dla bezpieczeństwa:
        if (unlockedSliders.length === 0) return;

        // 3. Dzielimy resztę po równo
        let share = remainingForUntouched / unlockedSliders.length;
        
        // Zabezpieczenie matematyczne (żeby nie wyszło -0.01)
        if (share < 0) share = 0;

        // 4. Aplikujemy zmiany
        unlockedSliders.forEach((s, i) => {
            s.value = share.toFixed(2);
            unlockedInputs[i].value = share.toFixed(2);

            if(unlockedInputs[i].percentDisplay) {
                let p = totalAmount > 0 ? ((share / totalAmount) * 100).toFixed(0) : 0;
                unlockedInputs[i].percentDisplay.textContent = `${p}%`;
            }
        });
    }

    // --- 4. WYSYŁANIE ---
    function handleFormSubmit(event) {
        event.preventDefault();
        const submitBtn = form.querySelector('button, input[type="submit"]');
        if (submitBtn && submitBtn.disabled) return;
        
        const inputs = Array.from(document.querySelectorAll('#split-details input[type="number"]'));
        let currentSum = inputs.reduce((sum, i) => sum + parseFloat(i.value), 0);
        let total = calculateTotal();
        
        if (Math.abs(currentSum - total) > 0.5) { // Tolerancja 50gr
            alert(`Suma podziału (${currentSum.toFixed(2)}) nie zgadza się z kwotą rachunku (${total.toFixed(2)})!`);
            return;
        }

        if (submitBtn) submitBtn.disabled = true;
        createSpill(submitBtn);
    }

    function createSpill(submitBtn) {
        const amount = amountInput.value;
        const tip = tipInput.value;
        
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
                'friends[]': selectedFriendsIds,
                'custom_splits': JSON.stringify(customSplits)
            },
            success: function (response) {
                location.reload();
            },
            error: function (xhr) {
                alert('Błąd: ' + xhr.status + ' ' + xhr.responseText);
                if (submitBtn) submitBtn.disabled = false;
            }
        });
    }

});

function selectGroupMembers(selectElement) {
    const checkboxes = document.querySelectorAll('#popup-friends-list input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);

    const idsString = selectElement.value;
    if (!idsString) {
        if(checkboxes.length > 0) checkboxes[0].dispatchEvent(new Event('change', {bubbles: true}));
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