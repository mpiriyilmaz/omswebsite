#!/usr/bin/env bash
# DigitalOcean Ubuntu - Sunucu: 161.35.207.104
set -euo pipefail

# ---------------------------------------- Bilgiler ----------------------------------------
SERVER_IP="161.35.207.104"
GITHUB_HESAP="mpiriyilmaz"
GITHUB_REPO="omswebsite"
DB_NAME="arasoms"
DB_USER="postgres"
DB_PASSWORD="oms123456"
DJANGO_PROJE_ADI="core"

# ---------------------------------------- Sistem Paketleri ----------------------------------------
sudo apt update
python3 --version || true
sudo apt install -y git curl ca-certificates python3-venv python3-pip nginx iproute2
sudo apt install -y build-essential libpq-dev || true

# ---------------------------------------- SSH key (Enter bekler) ----------------------------------------
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "server-key" -f ~/.ssh/id_ed25519 -N "" || true
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null || true

echo "==== PUBLIC KEY ===="
cat ~/.ssh/id_ed25519.pub || true
echo "===================="
echo
echo "[AKSIYON] Yukarıdaki public key'i GitHub hesabına ekle:"
echo "         - Kişisel anahtar: https://github.com/settings/keys"
echo "         - veya repo > Settings > Deploy Keys"
echo
read -r -p 'Ekleme bittiğinde Enter basın; SSH testi yapılacak... ' _

echo "[TEST] GitHub ile SSH bağlantısı deneniyor..."
ssh -T git@github.com || true

# ---------------------------------------- Repo ----------------------------------------
set -euo pipefail
cd /opt

if [ ! -d "/opt/omswebsite/.git" ]; then
  echo "[INFO] SSH ile klon deneniyor..."
  if git clone git@github.com:mpiriyilmaz/omswebsite.git; then
    :
  else
    echo "[WARN] SSH klon başarısız. HTTPS fallback denenecek."
    if [ -n "${GITHUB_PAT:-}" ]; then
      git clone https://mpiriyilmaz:${GITHUB_PAT}@github.com/mpiriyilmaz/omswebsite.git
    else
      echo "[ERROR] Repo klonlanamadı. Deploy key ekleyin ya da GITHUB_PAT ortam değişkeni verin."
      exit 1
    fi
  fi
else
  echo "[INFO] Repo mevcut, güncelleniyor…"
  git -C "/opt/omswebsite" pull --rebase || true
fi

git config --global --add safe.directory /opt/omswebsite || true

# manage.py repo kökünde
ls -la "/opt/omswebsite/manage.py" || true

# ---------------------------------------- venv & paketler ----------------------------------------
cd /opt/omswebsite
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# manage.py repo kökünde
cd /opt/omswebsite

if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  pip install "Django>=5.2,<5.3" django-environ gunicorn psycopg2-binary
fi

# ---------------------------------------- .env ----------------------------------------
cd /opt/omswebsite

SECRET_KEY=$(python3 - <<'PY'
import secrets
print('django-insecure-' + secrets.token_urlsafe(50))
PY
)

cat > .env <<EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=161.35.207.104,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://161.35.207.104,https://161.35.207.104,http://161.35.207.104:8000
DATABASE_URL=postgres://postgres:oms123456@localhost:5432/arasoms
DJANGO_ADMIN_USERNAME=piri
DJANGO_ADMIN_EMAIL=piri@arasedas.com
DJANGO_ADMIN_PASSWORD=arAs*+1981
EOF

chmod 600 .env
echo ".env olusturuldu:"
cat .env

# ---------------------------------------- PostgreSQL ----------------------------------------
dpkg -l | grep postgresql || true
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql

# Kullanıcı yoksa oluştur, varsa şifre ver
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = 'postgres'" | grep -q 1           || sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'oms123456';"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'oms123456';"

# DB yoksa oluştur ve owner yap
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'arasoms'" | grep -q 1           || sudo -u postgres createdb -O postgres arasoms

# Test
PGPASSWORD='oms123456' psql "host=localhost dbname=arasoms user=postgres" -c "select current_database(), current_user;"

# ---------------------------------------- migrate/superuser/static ----------------------------------------
cd /opt/omswebsite
source .venv/bin/activate
cd /opt/omswebsite

# Migrasyonlar
python manage.py migrate --noinput

# Superuser / staff kullanıcı oluştur ya da düzelt
python - <<'PY'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()
username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin')
email    = os.environ.get('DJANGO_ADMIN_EMAIL',    'admin@arasedas.com')
password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'sifre1234')

u, created = User.objects.get_or_create(
    username=username,
    defaults={'email': email, 'is_active': True, 'is_staff': True, 'is_superuser': True}
)

if created:
    u.set_password(password)
    u.save()
    print("Superuser created.")
else:
    changed = False
    if not u.is_active:
        u.is_active = True; changed = True
    if not u.is_staff:
        u.is_staff = True; changed = True
    if not u.is_superuser:
        u.is_superuser = True; changed = True
    if changed:
        u.save(); print("User elevated to staff/superuser.")
    else:
        print("Superuser already exists.")

try:
    g = Group.objects.get(name='Admin')
    g.user_set.add(u)
except Group.DoesNotExist:
    pass
PY

# Statikler
python manage.py collectstatic --noinput || true

# ---------------------------------------- Gunicorn (systemd) ----------------------------------------
cd /opt/omswebsite
source .venv/bin/activate

cat > /etc/systemd/system/gunicorn_v1.service <<'EOF'
[Unit]
Description=Gunicorn for omswebsite
After=network-online.target
Wants=network-online.target

[Service]
User=root
Group=www-data
WorkingDirectory=/opt/omswebsite
Environment="PATH=/opt/omswebsite/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings"
ExecStart=/opt/omswebsite/.venv/bin/gunicorn --workers 3 --timeout 120 --umask 007 --bind unix:/run/gunicorn_v1/gunicorn.sock core.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
KillMode=mixed

RuntimeDirectory=gunicorn_v1
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now gunicorn_v1
systemctl status gunicorn_v1 --no-pager || true

# kısa bekleme: soketin yetişmesi için
for i in {1..10}; do
  [ -S /run/gunicorn_v1/gunicorn.sock ] && break
  sleep 1
done
ls -l /run/gunicorn_v1/gunicorn.sock || (echo "[ERROR] Gunicorn soketi oluşmadı." && exit 1)

# ---------------------------------------- Nginx ----------------------------------------
set -euo pipefail

sudo tee /etc/nginx/sites-available/omswebsite.conf > /dev/null <<'NGINX'
server {
    listen 80;
    listen [::]:80;
    server_name _;

    client_max_body_size 20m;

    # STATIC_ROOT: /opt/omswebsite/staticfiles/
    location /static/ {
        alias /opt/omswebsite/staticfiles/;
        access_log off;
        expires 30d;
    }

    location / {
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://unix:/run/gunicorn_v1/gunicorn.sock;
    }
}
NGINX

# Etkinleştir
sudo ln -sf /etc/nginx/sites-available/omswebsite.conf /etc/nginx/sites-enabled/omswebsite.conf
sudo rm -f /etc/nginx/sites-enabled/default || true

# Güvenlik: conf.d altındaki olası default_server kalıntılarını da temizleyelim (opsiyonel)
sudo sed -i 's/default_server//g' /etc/nginx/conf.d/*.conf 2>/dev/null || true

sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

if ! ss -ltnp | grep -q ':80'; then
  echo "[ERROR] Nginx 80 portunu dinlemiyor!"
  sudo tail -n 100 /var/log/nginx/error.log || true
  exit 1
fi

curl --unix-socket /run/gunicorn_v1/gunicorn.sock http://localhost -I || true

# ---------------------------------------- UFW ----------------------------------------
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
ufw status

# ---------------------------------------- Doğrulamalar ----------------------------------------
echo "== Durum Kontrolleri =="
systemctl is-active nginx || true
systemctl is-active gunicorn_v1 || true
ss -ltnp | grep ':80' || true
ls -l /run/gunicorn_v1/gunicorn.sock || true
curl -I http://127.0.0.1 || true
