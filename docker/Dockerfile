ARG APP_TAG=${APP_TAG}
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    SERVER_PORT=${SERVER_PORT} \
    HOME=/app \
    XDG_CACHE_HOME=/app/.cache

WORKDIR $APP_HOME

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        fonts-dejavu \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip

RUN mkdir -p /app/logs /app/.cache \
    && chmod -R 777 /app/logs /app/.cache

RUN pip install --no-cache-dir uv \
    && uv --version

COPY pyproject.toml ./

RUN python -m venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install -r pyproject.toml

COPY . .

EXPOSE ${SERVER_PORT}
CMD ["python", "-m", "src.pipeline.server"]