document.addEventListener('DOMContentLoaded', function () {
    if (window.scriptHasRun) return;
    window.scriptHasRun = true;

    // --- ZMIENNE POMOCNICZE ---
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

    // Reset auto-locka przy zmianie kwot
    if (amountInput) amountInput.addEventListener('input', () => {
        touchedUserIds.clear(); 
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

        touchedUserIds.clear();

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
                touchedUserIds.add(person.id);
                if (touchedUserIds.size === friendsList.length) {
                    touchedUserIds.clear();
                    touchedUserIds.add(person.id);
                }
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
        
        let newShare = (newTotal / sliders.length).toFixed(2);

        sliders.forEach((slider, index) => {
            slider.max = newTotal > 0 ? newTotal : 100;
            slider.value = newShare;
            inputs[index].max = slider.max;
            inputs[index].value = newShare;
            if(inputs[index].percentDisplay) inputs[index].percentDisplay.textContent = newTotal > 0 ? ((newShare/newTotal)*100).toFixed(0)+'%' : '0%';
        });
    }

    function balanceRevolutStyle(activeSlider, friendsList) {
        const sliders = Array.from(document.querySelectorAll('#split-details input[type="range"]'));
        const inputs = Array.from(document.querySelectorAll('#split-details input[type="number"]'));
        let totalAmount = calculateTotal();

        let lockedSum = 0;
        let activeValue = parseFloat(activeSlider.value);
        let unlockedSliders = [];
        let unlockedInputs = [];

        sliders.forEach((s, index) => {
            if (s === activeSlider) return;
            let fId = s.dataset.friendId;
            if (touchedUserIds.has(fId)) {
                lockedSum += parseFloat(s.value);
            } else {
                unlockedSliders.push(s);
                unlockedInputs.push(inputs[index]);
            }
        });

        let remainingForUntouched = totalAmount - activeValue - lockedSum;
        if (unlockedSliders.length === 0) return;

        let share = remainingForUntouched / unlockedSliders.length;
        if (share < 0) share = 0;

        unlockedSliders.forEach((s, i) => {
            s.value = share.toFixed(2);
            unlockedInputs[i].value = share.toFixed(2);
            if(unlockedInputs[i].percentDisplay) {
                let p = totalAmount > 0 ? ((share / totalAmount) * 100).toFixed(0) : 0;
                unlockedInputs[i].percentDisplay.textContent = `${p}%`;
            }
        });
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
                if(descriptionInput) descriptionInput.value = '';
                amountInput.value = '';
                tipInput.value = '';
                splitDetails.innerHTML = '';
                selectedFriendsContainer.innerHTML = '';
                if (submitBtn) submitBtn.disabled = false;
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
    setTimeout(() => { toast.remove(); }, 3000);
}

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