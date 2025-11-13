FROM python:3.11-slim

ENV POETRY_VERSION=1.6.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY services/calendar/pyproject.toml ./pyproject.toml
COPY services/calendar/README.md ./README.md
RUN poetry install --no-root --only main

COPY services/calendar/app ./app

EXPOSE 7132

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7132"]
