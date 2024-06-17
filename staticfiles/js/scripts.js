const themeSwitch = document.getElementById('theme-switch');

themeSwitch.addEventListener('change', function () {
    document.body.classList.toggle('dark-theme');
});

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
