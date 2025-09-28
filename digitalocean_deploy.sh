#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/omswebsite"
BRANCH="${1:-$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)}"

echo "[INFO] Deploy başlıyor: $REPO_DIR (branch: $BRANCH)"
git -C "$REPO_DIR" fetch --all --prune
git -C "$REPO_DIR" reset --hard "origin/$BRANCH" || git -C "$REPO_DIR" pull --ff-only origin "$BRANCH"

source "$REPO_DIR/.venv/bin/activate"
[ -f "$REPO_DIR/requirements.txt" ] && pip install -r "$REPO_DIR/requirements.txt"

cd "$REPO_DIR"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

systemctl reload gunicorn_v1 || systemctl restart gunicorn_v1
echo "[OK] Deploy tamamlandı."
