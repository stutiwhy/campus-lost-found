# ---- base: runtime dependencies + app code -------------------------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/lost_found.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY init_db.py .
COPY templates/ templates/
COPY static/ static/

# ---- test: adds pytest/selenium + the test files (never shipped) ----------
FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY test_app.py test_selenium.py ./

CMD ["python", "-m", "pytest", "-v"]

# ---- runtime: the image that gets deployed (last stage = default target) --
FROM base AS runtime

RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /data \
    && chown app:app /data

USER app

EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2)"

CMD ["sh", "-c", "python init_db.py && exec gunicorn --bind 0.0.0.0:5000 --workers 2 --access-logfile - app:app"]