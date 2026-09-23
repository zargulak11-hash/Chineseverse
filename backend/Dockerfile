FROM python:3.12-slim

WORKDIR /app

# curl only for the container healthcheck below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=6 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# No --reload here (dev-only) and no separate migration step: app.main's
# lifespan already runs `alembic upgrade head` on startup (see
# _run_migrations() in app/main.py), so this just needs to serve.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
