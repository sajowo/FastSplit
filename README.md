# FastSplit

Aplikacja webowa (Django) do dzielenia rachunków i rozliczeń między znajomymi.

## Wymagania

- Git
- Python **3.11** (zgodnie z `Pipfile`)
- `pipenv`

> Uwaga: projekt używa SQLite (`db.sqlite3`) i działa lokalnie bez dodatkowej bazy.

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
- W `manage.py` jest ustawione `PYTHONHTTPSVERIFY=0` (obejście problemów SSL na macOS przy reCAPTCHA). To też jest typowo dev-only.

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
