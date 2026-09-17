#!/usr/bin/env bash
# Cloud Run container entrypoint. Unlike Render's build.sh, migrate and the
# superuser bootstrap can't run at image-build time here -- DATABASE_URL is a
# runtime secret (Cloud Run env var), not available to `docker build`. Both
# steps are idempotent, so running them on every container start (including
# cold starts of concurrent instances) is safe.
set -o errexit

python manage.py migrate --no-input

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

exec gunicorn entryrecorder.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 60
