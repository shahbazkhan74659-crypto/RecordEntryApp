# --- Stage 1: build JS assets (esbuild bundle -> static/js/dist) ---
FROM node:20-slim AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY static/js/src ./static/js/src
RUN npm run build

# --- Stage 2: Python runtime ---
FROM python:3.11-slim
WORKDIR /app

# psycopg2-binary needs libpq at runtime; build tools removed after pip install.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=assets /app/static/js/dist ./static/js/dist

# collectstatic needs a SECRET_KEY to load settings.py but talks to no
# database (STORAGES/manifest generation only) -- a build-time placeholder
# is fine since it's never used to serve real traffic.
RUN SECRET_KEY=build-only-placeholder python manage.py collectstatic --no-input

RUN chmod +x entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
