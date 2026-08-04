#!/usr/bin/env bash
# Render build step — runs on every deploy, before the new version goes live.
set -o errexit

pip install -r requirements.txt

npm install
npm run build

python manage.py collectstatic --no-input
python manage.py migrate
