FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Build-time only key so collectstatic can load settings; the real key is
# provided at runtime by Cloud Run
RUN SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput

RUN useradd --create-home appuser
USER appuser

# Cloud Run sends traffic to $PORT
CMD exec gunicorn jobportal.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 --threads 4 --timeout 60 \
    --access-logfile -
