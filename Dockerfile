# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

ENV PIP_DEFAULT_TIMEOUT=60 \
    PIP_RETRIES=5 \
    POETRY_REQUESTS_TIMEOUT=60

EXPOSE 8000

WORKDIR /api

RUN --mount=type=cache,target=/root/.cache/pip \
  pip install "poetry==1.8.2" wheel virtualenv

COPY ./pyproject.toml ./poetry.lock /api/

RUN --mount=type=cache,target=/root/.cache/pip \
  --mount=type=cache,target=/root/.cache/pypoetry \
  poetry export --without-hashes --format=requirements.txt --output=requirements.txt \
  && pip install -r requirements.txt

COPY . ./
