#!/bin/sh
set -e

echo "[entrypoint] Aplicando migraciones..."
python manage.py migrate --noinput

echo "[entrypoint] Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear >/dev/null

echo "[entrypoint] Asegurando admin (si QUEAI_ADMIN_USER está definido)..."
python manage.py ensure_admin

if [ "${QUEAI_DEV:-false}" = "true" ]; then
  echo "[entrypoint] Modo dev: arrancando runserver con auto-reload..."
  exec python manage.py runserver 0.0.0.0:8000
fi

WORKERS="${QUEAI_GUNICORN_WORKERS:-3}"
THREADS="${QUEAI_GUNICORN_THREADS:-2}"
TIMEOUT="${QUEAI_GUNICORN_TIMEOUT:-120}"

echo "[entrypoint] Arrancando gunicorn (workers=${WORKERS}, threads=${THREADS}, timeout=${TIMEOUT}s)..."
exec gunicorn core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${WORKERS}" \
  --threads "${THREADS}" \
  --timeout "${TIMEOUT}" \
  --access-logfile - \
  --error-logfile -
