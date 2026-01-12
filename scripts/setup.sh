#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

VENV_DIR="${FASTSPLIT_VENV_DIR:-"$HOME/.venvs/fastsplit"}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.11+ first." >&2
  exit 1
fi

mkdir -p "$(dirname "$VENV_DIR")"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install -U pip >/dev/null
python -m pip install -r requirements.txt >/dev/null

mkdir -p static
python manage.py migrate

echo "OK: environment ready"
