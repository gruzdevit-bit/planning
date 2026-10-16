FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data \
    NEWS_URL=https://lenta.ru/rss/news \
    NEWS_TTL=300 \
    NEWS_TIMEOUT=5

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app app
COPY docs docs
COPY tests tests

RUN mkdir -p /data

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "1", "--threads", "4", "app.main:app"]
