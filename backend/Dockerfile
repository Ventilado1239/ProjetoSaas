FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/runtime-data \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser . .
RUN chmod 0555 /app/docker-entrypoint.sh

USER appuser

EXPOSE 8000

CMD ["./docker-entrypoint.sh"]
