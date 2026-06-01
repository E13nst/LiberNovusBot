# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    POETRY_REQUESTS_TIMEOUT=120

EXPOSE 8000

WORKDIR /api

COPY ./pyproject.toml ./poetry.lock /api/

RUN --mount=type=cache,target=/root/.cache/pip \
  --mount=type=cache,target=/root/.cache/pypoetry \
  pip install "poetry==1.8.2" wheel virtualenv \
  && poetry config virtualenvs.create false \
  && poetry install --no-root --no-interaction

COPY . ./