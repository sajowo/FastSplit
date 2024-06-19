document.addEventListener('DOMContentLoaded', function () {
    const themeSwitch = document.getElementById('theme-switch');
    const body = document.body;

    themeSwitch.addEventListener('change', function () {
        body.classList.toggle('dark-theme');
    });

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

    const form = document.getElementById('split-form');
    const selectedFriendsContainer = document.getElementById('selected-friends');
    const splitDetails = document.getElementById('split-details');
    const amountInput = document.getElementById('amount');
    const tipInput = document.getElementById('tip');
    const spillResults = document.getElementById('spill-results');

    function initializeEventListeners() {
        document.getElementById('choose-friends-button').addEventListener('click', showPopup);
        document.getElementById('close-popup').addEventListener('click', hidePopup);
        form.addEventListener('submit', handleFormSubmit);
    }

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

        const loggedInUser = document.getElementById('logged-in-user').value;
        if (!selectedFriends.includes(loggedInUser)) {
            selectedFriends.unshift(loggedInUser);
        }

        if (selectedFriends.length > 0) {
            const friendsList = document.createElement('ul');
            selectedFriends.forEach(friend => {
                const listItem = document.createElement('li');
                listItem.textContent = friend;
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
        let totalAmount = parseFloat(amountInput.value) + (parseFloat(amountInput.value) * (parseFloat(tipInput.value || 0) / 100));
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
            slider.max = totalAmount;
            slider.step = 0.01;
            slider.value = initialAmount;
            slider.classList.add('amount-slider');
            slider.addEventListener('input', updateSliders);
            sliderContainer.appendChild(slider);

            const amountInputField = document.createElement('input');
            amountInputField.type = 'number';
            amountInputField.step = 0.01;
            amountInputField.min = 0;
            amountInputField.value = initialAmount;
            amountInputField.classList.add('amount-input');
            amountInputField.addEventListener('input', updateSlidersFromInput);
            sliderContainer.appendChild(amountInputField);

            splitDetails.appendChild(sliderContainer);
        });

        updateSliders();
    }

    function updateSliders() {
        const sliders = Array.from(document.querySelectorAll('.amount-slider'));
        const inputs = Array.from(document.querySelectorAll('.amount-input'));
        let total = 0;
        let remainingAmount = parseFloat(amountInput.value) + (parseFloat(amountInput.value) * (parseFloat(tipInput.value || 0) / 100));

        sliders.forEach((slider, index) => {
            const value = parseFloat(slider.value);
            total += value;
            inputs[index].value = value.toFixed(2);
        });

        if (total > remainingAmount) {
            const excess = total - remainingAmount;
            const adjustPerSlider = excess / sliders.length;

            sliders.forEach((slider, index) => {
                slider.value -= adjustPerSlider;
                inputs[index].value = parseFloat(slider.value).toFixed(2);
            });

            total = remainingAmount;
        }

        sliders.forEach(slider => {
            slider.nextElementSibling.value = slider.value;
        });

        displayResults();
    }

    function updateSlidersFromInput() {
        const inputs = Array.from(document.querySelectorAll('.amount-input'));
        const sliders = Array.from(document.querySelectorAll('.amount-slider'));
        let total = 0;
        let remainingAmount = parseFloat(amountInput.value) + (parseFloat(amountInput.value) * (parseFloat(tipInput.value || 0) / 100));

        inputs.forEach((input, index) => {
            const value = parseFloat(input.value);
            total += value;
            sliders[index].value = value;
        });

        if (total > remainingAmount) {
            const excess = total - remainingAmount;
            const adjustPerInput = excess / inputs.length;

            inputs.forEach((input, index) => {
                input.value -= adjustPerInput;
                sliders[index].value = parseFloat(input.value).toFixed(2);
            });

            total = remainingAmount;
        }

        displayResults();
    }

    function displayResults() {
        spillResults.innerHTML = '<h3>Rozliczenie:</h3>';
        const resultList = document.createElement('ul');

        const friends = Array.from(document.querySelectorAll('#popup-friends-list input[type="checkbox"]:checked')).map(checkbox => checkbox.value);
        const loggedInUser = document.getElementById('logged-in-user').value;
        if (!friends.includes(loggedInUser)) {
            friends.unshift(loggedInUser);
        }

        const amounts = Array.from(document.querySelectorAll('.amount-input')).map(input => parseFloat(input.value));
        const totalAmount = parseFloat(amountInput.value);
        const totalTip = totalAmount * (parseFloat(tipInput.value || 0) / 100);

        friends.forEach((friend, index) => {
            const amount = amounts[index];
            const tipShare = (amount / totalAmount) * totalTip;
            const totalToPay = amount + tipShare;
            const resultItem = document.createElement('li');
            resultItem.textContent = `${friend}: $${totalToPay.toFixed(2)} (incl. tip $${tipShare.toFixed(2)})`;
            resultList.appendChild(resultItem);
        });

        spillResults.appendChild(resultList);
    }

    function handleFormSubmit(event) {
        event.preventDefault();
        updateSelectedFriends();
        alert('Split created successfully!');
        resetForm();
    }

    function resetForm() {
        selectedFriendsContainer.innerHTML = '';
        splitDetails.innerHTML = '';
        amountInput.value = '';
        tipInput.value = '';
        spillResults.innerHTML = '';
        const checkboxes = document.querySelectorAll('#popup-friends-list input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
    }

    initializeEventListeners();
});
