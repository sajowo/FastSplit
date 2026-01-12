#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${1:-8000}"
VENV_DIR="${FASTSPLIT_VENV_DIR:-"$HOME/.venvs/fastsplit"}"
"./scripts/setup.sh" >/dev/null

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python manage.py runserver "$PORT"
