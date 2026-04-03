#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Clear any stale staticfiles before collecting fresh
rm -rf staticfiles/
python manage.py collectstatic --noinput

# Use DIRECT_URL for migrations if set (bypasses pgBouncer transaction mode limitation)
# Falls back to DATABASE_URL if DIRECT_URL is not set
if [ -n "$DIRECT_URL" ]; then
    DATABASE_URL=$DIRECT_URL python manage.py migrate
    DATABASE_URL=$DIRECT_URL python manage.py createcachetable
else
    python manage.py migrate
    python manage.py createcachetable
fi

python manage.py createsuperuser --no-input || true
