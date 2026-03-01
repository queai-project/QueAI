#!/bin/sh

echo "Aplicando migraciones..."
python manage.py migrate --noinput

echo "Iniciando servidor..."
python manage.py runserver 0.0.0.0:8000