#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py createcachetable  # creates django_cache_table for DB cache backend

python manage.py createsuperuser --no-input || true
