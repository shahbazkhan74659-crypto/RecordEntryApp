#!/usr/bin/env bash
# Render build step — runs on every deploy, before the new version goes live.
set -o errexit

pip install -r requirements.txt

npm install
npm run build

python manage.py collectstatic --no-input
python manage.py migrate

# Free-tier Render has no Shell access, so `createsuperuser` can't be run
# interactively there — bootstrap one here instead, from env vars, only if
# it doesn't already exist (safe to run on every deploy).
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
