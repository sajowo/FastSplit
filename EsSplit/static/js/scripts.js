const themeSwitch = document.getElementById('theme-switch');
const body = document.body;

themeSwitch.addEventListener('change', function () {
    body.classList.toggle('dark-theme');
});

// Funkcja do automatycznego przełączania na ciemny motyw po godzinie 17
function toggleThemeByTime() {
    const currentHour = new Date().getHours();
    if (currentHour >= 17) {
        body.classList.add('dark-theme');
    } else {
        body.classList.remove('dark-theme');
    }
}

// Uruchom funkcję po raz pierwszy, aby ustawić początkowy motyw
toggleThemeByTime();

// Uruchom funkcję co godzinę, aby aktualizować motyw
setInterval(toggleThemeByTime, 3600000); // 3600000 milisekund = 1 godzina

// Pobierz elementy formularza
const form = document.querySelector('form');
const participantList = document.getElementById('participant-list');
const splitDetails = document.getElementById('split-details');
const amountInput = document.getElementById('amount');
const spillResults = document.getElementById('spill-results');

// Dodaj obsługę zdarzeń dla zmiany liczby uczestników
generateParticipantList();

function generateParticipantList() {
    participantList.innerHTML = '';
    const selectedParticipants = [
        'Person 1',
        'Person 2',
        'Person 3'
        // Dodaj więcej uczestników według potrzeby
    ];

    selectedParticipants.forEach(participant => {
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'participant';
        checkbox.value = participant;
        checkbox.id = participant;

        const label = document.createElement('label');
        label.htmlFor = participant;
        label.textContent = participant;

        participantList.appendChild(checkbox);
        participantList.appendChild(label);
        participantList.appendChild(document.createElement('br'));
    });

    // Dodaj obsługę zdarzeń dla zmiany liczby uczestników
    participantList.addEventListener('change', generateSliders);
}

// Funkcja do generowania suwaków dla uczestników
function generateSliders() {
    // Wyczyść poprzednie suwaki
    splitDetails.innerHTML = '';

    // Pobierz wybrane osoby
    const selectedParticipants = Array.from(participantList.querySelectorAll('input[type="checkbox"]:checked')).map(checkbox => checkbox.value);

    let remainingAmount = parseFloat(amountInput.value);

    // Dla każdej wybranej osoby, wygeneruj suwak
    selectedParticipants.forEach(participant => {
        const sliderContainer = document.createElement('div');
        sliderContainer.classList.add('slider-container');

        const nameLabel = document.createElement('label');
        nameLabel.textContent = participant + ':';
        sliderContainer.appendChild(nameLabel);

        const slider = document.createElement('input');
        slider.type = 'range';
        slider.min = 0;
        slider.max = remainingAmount;
        slider.step = 0.01;
        slider.value = 0;
        slider.dataset.max = remainingAmount; // Zachowaj początkowy maksymalny zakres
        sliderContainer.appendChild(slider);

        const amountLabel = document.createElement('span');
        amountLabel.textContent = '$' + slider.value;
        sliderContainer.appendChild(amountLabel);

<<<<<<< Updated upstream
        slider.addEventListener('input', function () {
            amountLabel.textContent = '$' + slider.value;
            updateSliders(slider);
        });

        splitDetails.appendChild(sliderContainer);
    });
}

// Funkcja do aktualizacji zakresów suwaków
function updateSliders(currentSlider) {
    const sliders = Array.from(splitDetails.querySelectorAll('input[type="range"]'));
    const currentIndex = sliders.indexOf(currentSlider);

    let totalAssigned = 0;
    for (let i = 0; i <= currentIndex; i++) {
        totalAssigned += parseFloat(sliders[i].value);
    }

    const remainingAmount = parseFloat(amountInput.value) - totalAssigned;
    for (let i = currentIndex + 1; i < sliders.length; i++) {
        sliders[i].max = remainingAmount + parseFloat(sliders[i].value); // Dostosuj maksymalny zakres
    }
}

// Dodaj obsługę zdarzenia dla przesyłania formularza
form.addEventListener('submit', function (event) {
    event.preventDefault();

    // Oblicz sumę wszystkich wybranych kwot
    const totalAmount = calculateTotal();

    // Wyświetl procentową kwotę dla każdego uczestnika
    const selectedParticipants = Array.from(participantList.querySelectorAll('input[type="checkbox"]:checked')).map(checkbox => checkbox.value);
    const sliders = splitDetails.querySelectorAll('input[type="range"]');
    const results = selectedParticipants.map((participant, index) => {
        const percentage = ((parseFloat(sliders[index].value) / parseFloat(amountInput.value)) * 100).toFixed(2);
        return `${participant}: ${percentage}%`;
    });

    spillResults.innerHTML = results.join('<br>');
});

// Funkcja do obliczania sumy wszystkich wybranych kwot
function calculateTotal() {
    const totalAmount = Array.from(splitDetails.querySelectorAll('input[type="range"]')).reduce((acc, slider) => acc + parseFloat(slider.value), 0);
    return totalAmount;
}

// Generuj suwaki na podstawie domyślnej liczby uczestników
generateSliders();


// heder zwijany
document.addEventListener('DOMContentLoaded', function () {
    const menuToggle = document.getElementById('menuToggle');
    const menuContent = document.getElementById('menuContent');

    menuToggle.addEventListener('click', function () {
        menuContent.classList.toggle('show');
    });

    // Opcjonalnie zamknij rozwijane menu po kliknięciu poza nim
    document.addEventListener('click', function (event) {
        if (!menuToggle.contains(event.target) && !menuContent.contains(event.target)) {
            menuContent.classList.remove('show');
        }
    });
=======
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
>>>>>>> Stashed changes
});
