#!/usr/bin/env bash
# Vercel build step (vercel.json's buildCommand). Vercel installs
# requirements.txt and runs collectstatic automatically for a detected
# Django project -- do NOT call collectstatic here, only the JS bundling
# step it depends on, plus migrate/superuser bootstrap (same idempotent
# pattern as build.sh's Render build step).
set -o errexit

npm install
npm run build

python manage.py migrate

# Same bootstrap as build.sh (Render): safe to run on every deploy, only
# creates the superuser if DJANGO_SUPERUSER_USERNAME doesn't already exist.
# No-ops harmlessly if the env vars aren't set (e.g. a fresh DB isn't in play).
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ['DJANGO_SUPERUSER_USERNAME']
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
password = os.environ['DJANGO_SUPERUSER_PASSWORD']
if User.objects.filter(username__iexact=username).exists():
    print(f'Superuser {username!r} already exists, skipping')
else:
    User.objects.create_superuser(username, email, password)
    print(f'Created superuser {username!r}')
"
fi
