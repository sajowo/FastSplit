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
                listItem.dataset.id = friend; // Dodanie atrybutu data-id
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
        let totalAmount = parseFloat(amountInput.value) + (parseFloat(amountInput.value) * (parseFloat(tipInput.value || 0) / 100));
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

    function handleFormSubmit(event) {
        event.preventDefault();
        createSpill();
    }

    function createSpill() {
        const amount = amountInput.value;
        const tip = tipInput.value;
        const selectedFriends = Array.from(selectedFriendsContainer.querySelectorAll('li')).map(li => li.dataset.id); // Użycie data-id

        $.ajax({
            url: '{% url "create_spill" %}',
            type: 'POST',
            data: {
                'amount': amount,
                'tip': tip,
                'friends': selectedFriends,
                'csrfmiddlewaretoken': '{{ csrf_token }}'
            },
            success: function (response) {
                spillResults.innerHTML = response;
            },
            error: function (response) {
                alert('Error creating spill');
            }
        });
    }



    initializeEventListeners();
});