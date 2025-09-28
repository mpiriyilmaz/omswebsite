#!/usr/bin/env bash
# Opsiyonel güvenlik: DB_RESET=1 değilse atla
if [ "${DB_RESET:-0}" != "1" ]; then
  echo "[SKIP] DB reset atlandı (DB_RESET=1 değil)."
  exit 0
fi

set -euo pipefail
echo "[WARN] Veritabanı SIFIRLANACAK: arasoms"

# DB kullanıcısı garanti
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = 'postgres'" | grep -q 1           || sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'oms123456';"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'oms123456';"

# Drop + Create
sudo -u postgres dropdb --if-exists arasoms
sudo -u postgres createdb -O postgres arasoms

# Django migrate + superuser
cd /opt/omswebsite
source .venv/bin/activate
python manage.py migrate --noinput

# .env'deki DJANGO_ADMIN_* değerlerini ortama al ve superuser oluştur
python - <<'PY'
import os, django, pathlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

env_file = pathlib.Path('/opt/omswebsite/.env')
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8', errors='ignore').splitlines():
        s = line.strip()
        if s and not s.startswith('#') and '=' in s:
            k, v = s.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()

username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin')
email    = os.environ.get('DJANGO_ADMIN_EMAIL',    'admin@example.com')
password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'sifre1234')

u, created = User.objects.get_or_create(
    username=username,
    defaults={'email': email}
)
u.is_active = True
u.is_staff = True
u.is_superuser = True
u.email = email
u.set_password(password)
u.save()
print(f"[OK] Superuser: {username} (şifre .env veya varsayılan)")
PY

python manage.py collectstatic --noinput || true
systemctl reload gunicorn_v1 || systemctl restart gunicorn_v1

echo "[OK] DB reset + superuser tamam."
