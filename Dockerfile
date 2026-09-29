# Single production image: the API also serves the built frontend, so the browser talks to
# one origin and the refresh cookie stays SameSite=lax with no CORS in the request path.

FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /build/dist ./static

RUN useradd --create-home --uid 10001 maf && chown -R maf:maf /app
USER maf

EXPOSE 8000
# PORT is read by Python rather than expanded by the shell, so a host that sets it (Render
# does) is checked on the port uvicorn is actually listening on.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health')"

# Migrations run before the first request, so a deploy can never serve an older schema.
# SEED_DEMO_DATA fills the public demo with a worked fortnight; it is idempotent, and unset
# everywhere that holds real data.
CMD ["sh", "-c", "alembic upgrade head && if [ \"$SEED_DEMO_DATA\" = \"true\" ]; then python -m app.seed; fi && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
