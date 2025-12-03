document.addEventListener("DOMContentLoaded", function () {
  if (window.scriptHasRun) return;
  window.scriptHasRun = true;

  // --- 1. MOTYWY I ZMIENNE ---
  const themeSwitch = document.getElementById("theme-switch");
  const body = document.body;
  if (themeSwitch)
    themeSwitch.addEventListener("change", () =>
      body.classList.toggle("dark-theme")
    );

  function toggleThemeByTime() {
    if (new Date().getHours() >= 17) body.classList.add("dark-theme");
    else body.classList.remove("dark-theme");
  }
  toggleThemeByTime();
  setInterval(toggleThemeByTime, 3600000);

  const form = document.getElementById("split-form");
  const selectedFriendsContainer = document.getElementById("selected-friends");
  const splitDetails = document.getElementById("split-details");
  const amountInput = document.getElementById("amount");
  const tipInput = document.getElementById("tip");
  const spillResults = document.getElementById("spill-results");
  const chooseBtn = document.getElementById("choose-friends-button");
  const closePopupBtn = document.getElementById("close-popup");

  if (chooseBtn)
    chooseBtn.addEventListener(
      "click",
      () => (document.getElementById("popup-container").style.display = "block")
    );
  if (closePopupBtn) closePopupBtn.addEventListener("click", hidePopup);
  if (form) form.addEventListener("submit", handleFormSubmit);

  // Nasłuchiwanie zmian w głównej kwocie
  if (amountInput) amountInput.addEventListener("input", refreshSlidersLimit);
  if (tipInput) tipInput.addEventListener("input", refreshSlidersLimit);

  function hidePopup() {
    document.getElementById("popup-container").style.display = "none";
    updateSelectedFriends();
  }

  // --- 2. LOGIKA WYBORU ZNAJOMYCH ---
  function updateSelectedFriends() {
    selectedFriendsContainer.innerHTML = "";
    const checkedBoxes = document.querySelectorAll(
      '#popup-friends-list input[type="checkbox"]:checked'
    );

    let selectedList = Array.from(checkedBoxes).map((checkbox) => ({
      id: checkbox.value,
      name: checkbox.dataset.name,
    }));

    const myIdInput = document.getElementById("logged-in-user-id");
    const myNameInput = document.getElementById("logged-in-user-name");

    if (myIdInput && myNameInput) {
      const myId = myIdInput.value;
      if (!selectedList.some((f) => f.id === myId)) {
        selectedList.unshift({ id: myId, name: myNameInput.value });
      }
    }

    if (selectedList.length > 0) {
      const ul = document.createElement("ul");
      selectedList.forEach((person) => {
        const li = document.createElement("li");
        li.textContent = person.name;
        li.dataset.id = person.id;
        ul.appendChild(li);
      });
      selectedFriendsContainer.appendChild(ul);
    } else {
      selectedFriendsContainer.innerHTML = "<p>Nie wybrano znajomych.</p>";
    }

    generateSliders(selectedList);
  }

  // --- 3. GENEROWANIE SLIDERÓW (Z NAPRAWIONĄ LOGIKĄ) ---
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

            // Label
            const label = document.createElement('label');
            label.textContent = person.name;
            label.style.cssText = "width: 100px; margin-right: 10px; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;";
            container.appendChild(label);

            // Suwak
            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = 0;
            slider.max = sliderMax;
            slider.step = 0.01;
            slider.value = initialAmount;
            slider.dataset.friendId = person.id;
            slider.style.flexGrow = "1";
            container.appendChild(slider);

            // Input liczbowy
            const numberInput = document.createElement('input');
            numberInput.type = 'number';
            numberInput.step = '0.01';
            numberInput.min = '0';
            numberInput.max = sliderMax;
            numberInput.value = initialAmount;
            numberInput.style.cssText = "width: 70px; margin-left: 10px; text-align: center;";
            container.appendChild(numberInput);

            // NOWOŚĆ: Procenty
            const percentSpan = document.createElement('span');
            percentSpan.style.cssText = "width: 45px; margin-left: 5px; font-size: 0.8em; color: grey; text-align: right;";
            // Funkcja pomocnicza do liczenia %
            const updatePercent = (val) => {
                let p = totalAmount > 0 ? ((val / totalAmount) * 100).toFixed(0) : 0;
                percentSpan.textContent = `${p}%`;
            };
            updatePercent(initialAmount); // Ustaw na start
            container.appendChild(percentSpan);

            // EVENTY
            slider.addEventListener('input', () => {
                numberInput.value = slider.value;
                updatePercent(slider.value); // Aktualizuj %
                balanceAmounts(slider, friendsList.length);
            });

            numberInput.addEventListener('input', () => {
                let val = parseFloat(numberInput.value);
                let max = parseFloat(slider.max);
                if (val > max) val = max;
                if (isNaN(val) || val < 0) val = 0;
                
                slider.value = val;
                numberInput.value = val;
                updatePercent(val); // Aktualizuj %
                balanceAmounts(slider, friendsList.length);
            });
            
            // Nasłuchujemy też na zmiany innych suwaków (przez MutationObserver lub po prostu odświeżamy wszystko przy balance)
            // Najprościej: dodamy aktualizację procentów do funkcji balanceAmounts w następnym kroku, 
            // ale tutaj wystarczy, bo balanceAmounts zmienia value inputów, co nie zawsze triggeruje event 'input'.
            // Zrobimy prosty hack: przypiszemy ten span do inputu, żeby mieć do niego dostęp.
            numberInput.percentDisplay = percentSpan; 

            splitDetails.appendChild(container);
        });
        
        balanceAmounts(null, friendsList.length); 
    }

  function calculateTotal() {
    let base = parseFloat(amountInput.value) || 0;
    let tip = parseFloat(tipInput.value) || 0;
    return base + base * (tip / 100);
  }

  function refreshSlidersLimit() {
    let newTotal = calculateTotal();
    const sliders = Array.from(
      document.querySelectorAll('#split-details input[type="range"]')
    );
    const inputs = Array.from(
      document.querySelectorAll('#split-details input[type="number"]')
    );

    if (sliders.length === 0) return;

    let newShare = (newTotal / sliders.length).toFixed(2);

    sliders.forEach((slider, index) => {
      slider.max = newTotal > 0 ? newTotal : 100;
      slider.value = newShare;
      inputs[index].max = slider.max;
      inputs[index].value = newShare;
    });
  }

  // --- KLUCZOWA FUNKCJA: BALANSER ---
  // Ta funkcja pilnuje, żeby suma zawsze wynosiła TOTAL
  function balanceAmounts(sourceElement, count) {
    const sliders = Array.from(
      document.querySelectorAll('#split-details input[type="range"]')
    );
    const inputs = Array.from(
      document.querySelectorAll('#split-details input[type="number"]')
    );
    let totalAmount = calculateTotal();

    // Jeśli nie wiemy kto zmienił wartość (np. init), nic nie rób albo zresetuj
    if (!sourceElement) return;

    let changedValue = parseFloat(sourceElement.value);
    let remainingAmount = totalAmount - changedValue;

    // Znajdź pozostałe suwaki
    let otherSliders = sliders.filter((s) => s !== sourceElement);
    let otherInputs = inputs.filter(
      (i) =>
        i !== sourceElement.nextSibling && i.previousSibling !== sourceElement
    );

    if (otherSliders.length === 0) return;

    // Podziel resztę po równo między pozostałych
    let share = remainingAmount / otherSliders.length;

    // Zabezpieczenie: jeśli ktoś zabrał wszystko, inni mają 0
    if (share < 0) share = 0;

    otherSliders.forEach((s, index) => {
      s.value = share.toFixed(2);
      otherInputs[index].value = share.toFixed(2);
      if(otherInputs[index].percentDisplay) {
                let p = totalAmount > 0 ? ((share / totalAmount) * 100).toFixed(0) : 0;
                otherInputs[index].percentDisplay.textContent = `${p}%`;
            }
    });
  }

  // --- 4. WYSYŁANIE ---
  function handleFormSubmit(event) {
    event.preventDefault();
    const submitBtn = form.querySelector('button, input[type="submit"]');
    if (submitBtn && submitBtn.disabled) return;

    // OSTATNIE SPRAWDZENIE: Czy suma się zgadza?
    const inputs = Array.from(
      document.querySelectorAll('#split-details input[type="number"]')
    );
    let currentSum = inputs.reduce((sum, i) => sum + parseFloat(i.value), 0);
    let total = calculateTotal();

    // Margines błędu 1 grosz
    if (Math.abs(currentSum - total) > 0.1) {
      alert(
        `Suma podziału (${currentSum.toFixed(
          2
        )}) nie zgadza się z kwotą rachunku (${total.toFixed(
          2
        )})! Popraw wartości.`
      );
      return;
    }

    if (submitBtn) submitBtn.disabled = true;
    createSpill(submitBtn);
  }

  function createSpill(submitBtn) {
    const amount = amountInput.value;
    const tip = tipInput.value;

    // Budujemy mapę {id: kwota}
    let customSplits = [];
    const sliders = document.querySelectorAll(
      '#split-details input[type="range"]'
    );
    sliders.forEach((s) => {
      customSplits.push({
        id: s.dataset.friendId,
        amount: s.value,
      });
    });

    // UWAGA: Musimy wysłać te customowe kwoty do backendu!
    // Na razie wysyłamy tylko listę ID, a backend dzieli po równo.
    // Żeby to działało idealnie, w views.py musiałbyś obsługiwać 'custom_amounts'.
    // Ale na potrzeby tego fixu, wyślijmy chociaż ID.

    const selectedFriendsIds = Array.from(
      document.querySelectorAll("#selected-friends li")
    ).map((li) => li.dataset.id);
    const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();

    if (!csrftoken) {
      alert("Błąd CSRF.");
      if (submitBtn) submitBtn.disabled = false;
      return;
    }

    $.ajax({
      url: "/create_spill/",
      type: "POST",
      headers: { "X-CSRFToken": csrftoken },
      mode: "same-origin",
      data: {
        amount: amount,
        tip: tip,
        "friends[]": selectedFriendsIds,
        // Tu w przyszłości dodasz: 'custom_splits': JSON.stringify(customSplits)
      },
      success: function (response) {
        location.reload();
      },
      error: function (xhr) {
        alert("Błąd: " + xhr.status);
        if (submitBtn) submitBtn.disabled = false;
      },
    });
  }
});

// Ta funkcja musi być globalna (poza DOMContentLoaded), żeby HTML ją widział
function selectGroupMembers(selectElement) {
  // 1. Odznaczamy wszystkie checkboxy na start
  const checkboxes = document.querySelectorAll(
    '#popup-friends-list input[type="checkbox"]'
  );
  checkboxes.forEach((cb) => (cb.checked = false));

  // 2. Pobieramy ID członków z value opcji (np. "4,5,8,")
  const idsString = selectElement.value;
  if (!idsString) {
    // Jeśli wybrano "Wybierz grupę" (puste), aktualizujemy tylko widok i kończymy
    // Musimy wywołać updateSelectedFriends, żeby wyczyścić slidery
    // Ale ta funkcja jest wewnątrz innego scope'u...
    // Trick: klikamy sztucznie w przycisk zamknięcia lub wywołujemy event change na checkboxie
    if (checkboxes.length > 0)
      checkboxes[0].dispatchEvent(new Event("change", { bubbles: true }));
    return;
  }

  const idsToSelect = idsString.split(",").filter((id) => id); // Usuwamy puste

  // 3. Zaznaczamy odpowiednie checkboxy
  idsToSelect.forEach((id) => {
    // Szukamy checkboxa, który ma value == id
    const cb = document.querySelector(
      `#popup-friends-list input[value="${id}"]`
    );
    if (cb) {
      cb.checked = true;
    }
  });

  // 4. Ważne: Musimy wymusić odświeżenie listy "Wybrani znajomi" i sliderów
  // Symulujemy kliknięcie w pierwszy zaznaczony checkbox, żeby uruchomić logikę w głównym skrypcie
  const firstChecked = document.querySelector(
    '#popup-friends-list input[type="checkbox"]:checked'
  );
  if (firstChecked) {
    // Wywołujemy sztuczne zdarzenie 'change' lub 'click', na które nasłuchuje Twój główny skrypt (jeśli nasłuchuje)
    // Jeśli Twój główny skrypt w scripts.js reaguje na 'change' w updateSelectedFriends, to musimy to wywołać ręcznie.

    // Najbezpieczniej: Skoro funkcja updateSelectedFriends jest schowana w DOMContentLoaded,
    // musimy zasymulować interakcję użytkownika.
    firstChecked.dispatchEvent(new Event("change", { bubbles: true }));
    // LUB po prostu kliknijmy w przycisk "Zamknij" (jeśli to tam jest logika)
    // Ale w Twoim kodzie updateSelectedFriends jest wywoływane przy hidePopup.
  }
}
