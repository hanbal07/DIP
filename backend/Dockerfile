# Backend: FastAPI + Celery worker + document processing.
# Uses supervisord to run both API and worker in one container.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for PyMuPDF, OpenCV, optional OCR, and supervisord.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app \
    && mkdir -p /var/log/supervisor \
    && chown -R appuser:appuser /var/log/supervisor

USER appuser

ENV PORT=8000
EXPOSE $PORT

# Run migrations, then start supervisord (API + worker).
CMD ["sh", "-c", "alembic upgrade head && supervisord -c supervisord.conf"]
