# FastSplit

Aplikacja webowa (Django) do dzielenia rachunków i rozliczeń między znajomymi.

## Deployment na Render (Produkcja)

FastSplit można łatwo wdrożyć na [Render](https://render.com) używając Blueprint.

### Szybkie wdrożenie (1 klik)

1. Fork tego repozytorium na swoje konto GitHub
2. Zaloguj się na [Render](https://render.com)
3. Kliknij **New** → **Blueprint**
4. Połącz swoje konto GitHub i wybierz fork FastSplit
5. Render automatycznie wykryje `render.yaml` i wdroży aplikację

### Konfiguracja zmiennych środowiskowych

Po wdrożeniu, ustaw następujące zmienne w Render Dashboard:

**Wymagane:**
- `DJANGO_ALLOWED_HOSTS` - Twoja domena Render, np. `fastsplit.onrender.com`
- `CSRF_TRUSTED_ORIGINS` - URL z https, np. `https://fastsplit.onrender.com`

**Opcjonalne (dla dodatkowego bezpieczeństwa):**
- `RECAPTCHA_PUBLIC_KEY` - Klucz publiczny Google reCAPTCHA v2
- `RECAPTCHA_PRIVATE_KEY` - Klucz prywatny Google reCAPTCHA v2

**Automatycznie generowane przez Render:**
- `DJANGO_SECRET_KEY` - Render wygeneruje bezpieczny klucz
- `DJANGO_DEBUG` - Ustawione na `0` (False) w produkcji

### Pierwsze uruchomienie

Po wdrożeniu aplikacji, uruchom migracje i utwórz konto admina:

1. Otwórz **Shell** w Render Dashboard dla swojego serwisu
2. Uruchom migracje:
   ```bash
   python manage.py migrate
   ```
3. Utwórz konto superusera:
   ```bash
   python manage.py createsuperuser
   ```

### Architektura wdrożenia

- **Web Service**: Działa na gunicorn, obsługuje requesty Django
- **Static Files**: Serwowane przez WhiteNoise bezpośrednio z aplikacji
- **Database**: SQLite (tylko dla demo; dla produkcji zalecane PostgreSQL)

### Uwagi produkcyjne

- Free tier Render ma spin-down po bezczynności (opóźnienie pierwszego requesta)
- Dla produkcji zalecamy:
  - Plan Starter lub wyższy (bez spin-down)
  - PostgreSQL zamiast SQLite
  - Własną domenę + SSL (automatyczny na Render)

---

## Najszybciej (1 komenda)

Projekt da się uruchomić jedną komendą – skrypt sam tworzy `.venv`, instaluje zależności, robi migracje i odpala serwer.

Skrypt tworzy środowisko w katalogu domowym (domyślnie `~/.venvs/fastsplit`), żeby działało niezależnie od ścieżki projektu.
Możesz zmienić lokalizację przez zmienną `FASTSPLIT_VENV_DIR`.

macOS / Linux:

```bash
chmod +x scripts/run.sh
./scripts/run.sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1
```

Domyślnie serwer startuje na http://127.0.0.1:8000/.

Jeśli port 8000 jest zajęty:

```bash
./scripts/run.sh 8001
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1 -Port 8001
```

> Uwaga: projekt używa SQLite (`db.sqlite3`) i działa lokalnie bez dodatkowej bazy.

## Jeszcze szybciej w VS Code (bez komend)

- `Terminal → Run Task…` → `FastSplit: Run (8000)`
- albo `F5` i wybierz `Django: runserver (8000)`

## Wymagania

- Git
- Python **3.11** (zgodnie z `Pipfile`)

Opcjonalnie:
- `pipenv` (jeśli wolisz Pipenv zamiast `.venv`)

## Szybki start (macOS / Linux)

```bash
git clone <URL_DO_REPO>
cd FastSplit

# (jeśli nie masz pipenv)
python3 -m pip install --user pipenv

# utwórz środowisko na Pythonie 3.11 i zainstaluj zależności
pipenv --python 3.11
pipenv install

# katalog wymagany przez STATICFILES_DIRS (czasem nie jest w repo)
mkdir -p static

# migracje
pipenv run python manage.py migrate

# uruchomienie
pipenv run python manage.py runserver
```

Wejdź w przeglądarce: http://127.0.0.1:8000/

Jeśli port 8000 jest zajęty:

```bash
pipenv run python manage.py runserver 8001
```

## Szybki start (Windows)

W PowerShell / CMD:

```powershell
git clone <URL_DO_REPO>
cd FastSplit

py -3.11 -m pip install --user pipenv

pipenv --python 3.11
pipenv install

# katalog wymagany przez STATICFILES_DIRS
mkdir static

pipenv run python manage.py migrate
pipenv run python manage.py runserver
```

Wejdź w przeglądarce: http://127.0.0.1:8000/

## Alternatywa: instalacja przez requirements.txt (bez Pipenv)

Jeśli wolisz standardowe środowisko `venv` + `pip`:

macOS / Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt

mkdir -p static
python manage.py migrate
python manage.py runserver
```

Windows (PowerShell):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt

mkdir static
python manage.py migrate
python manage.py runserver
```

## Konto admina (opcjonalnie)

Jeśli chcesz wejść do panelu Django admin:

```bash
pipenv run python manage.py createsuperuser
```

Potem: http://127.0.0.1:8000/admin/

## Ważne uwagi dot. konfiguracji

- `FastSplit/settings.py` ma `DEBUG = True` i klucz `SECRET_KEY` wpisany na stałe — to OK do zajęć/dev, nie do produkcji.
- Projekt ma zainstalowane:
  - `django-axes` (`axes`) – mechanizmy blokady logowania (w tym branchu `AXES_ENABLED = False`).
  - `django-recaptcha` (`django_recaptcha`) – reCAPTCHA (w ustawieniach są **testowe klucze Google** + wyciszony check).
- Jeśli masz problem z SSL na macOS przy reCAPTCHA, możesz ustawić `PYTHONHTTPSVERIFY_DISABLE=1` (dev-only).

## Zabezpieczenia haseł

W aplikacji zastosowano mechanizm walidacji haseł oparty na wbudowanych walidatorach frameworka Django.

### Zastosowane walidatory:

- **UserAttributeSimilarityValidator**  
  Zabrania używania haseł podobnych do nazwy użytkownika czy adresu e-mail.

- **MinimumLengthValidator** (min. 8 znaków)  
  Wymusza minimalną długość hasła (zwiększa odporność na brute force).

- **CommonPasswordValidator**  
  Blokuje popularne i łatwe do odgadnięcia hasła (np. 123456, password).

- **NumericPasswordValidator**  
  Zabrania używania haseł składających się wyłącznie z cyfr.

### Dodatkowe wymagania:

- Hasło musi zawierać co najmniej jedną **wielką literę** (A-Z)
- Hasło musi zawierać co najmniej jeden **znak specjalny** (np. !, @, #, $)

Wszystkie walidacje są wykonywane zarówno po stronie serwera (Django), jak i w formularzu rejestracji.

## Zmienne środowiskowe (opcjonalnie)

Możesz skopiować `.env.example` do `.env` i ustawić własne wartości. Najważniejsze:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `RECAPTCHA_PUBLIC_KEY`, `RECAPTCHA_PRIVATE_KEY`

## Najczęstsze problemy

### 1) `ModuleNotFoundError: No module named 'axes'` / `'django_recaptcha'`

Zwykle oznacza, że projekt uruchamiasz **poza** środowiskiem Pipenv.

Uruchamiaj tak:

```bash
pipenv run python manage.py runserver
```

albo aktywuj shell:

```bash
pipenv shell
python manage.py runserver
```

### 2) Pipenv używa złego Pythona

Sprawdź:

```bash
pipenv --py
```

Jeśli to nie Python 3.11, ustaw jawnie:

```bash
pipenv --rm
pipenv --python 3.11
pipenv install
```

### 3) Ostrzeżenie: `STATICFILES_DIRS ... does not exist`

Utwórz folder:

```bash
mkdir -p static
```

### 4) Port 8000 zajęty

Odpal na innym porcie:

```bash
pipenv run python manage.py runserver 8001
```

## Struktura projektu (skrót)

- `FastSplit/` – konfiguracja projektu Django (settings/urls/wsgi)
- `EsSplit/` – aplikacja Django (modele, widoki, szablony, statyki)
- `db.sqlite3` – lokalna baza SQLite

---

Jeśli chcesz, mogę dopisać sekcję „Deploy” (gunicorn/whitenoise), ale na potrzeby uruchamiania na dowolnym komputerze (dev) powyższe kroki są wystarczające.
