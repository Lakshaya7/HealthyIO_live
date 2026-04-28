#!/usr/bin/env bash
# exit on error
set -o errexit

# Install required packages
pip install -r requirements.txt

# Bundle static files for the internet
python manage.py collectstatic --no-input

# Setup the PostgreSQL database automatically!
python manage.py makemigrations core
python manage.py migrate