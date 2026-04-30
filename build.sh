#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input

# THE FIX: Tell Render to dynamically detect new columns
python manage.py makemigrations

python manage.py migrate
python manage.py createsuperuser --noinput || true