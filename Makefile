COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yaml
API_SERVICE := mini_app_api
DATA_DIR := $(abspath $(CURDIR)/../mini-app-data)
TEST_DATABASE_URL ?= postgresql+asyncpg://postgres:password@localhost:5433/mini_app_db_test

export COMPOSE_FILE

.PHONY: help up down stop start restart build ps logs logs-api logs-bot shell recreate down-v pull data-dirs \
	test test-smoke test-services test-db openai-smoke openai-runtime-smoke openai-e2e-smoke local-up api-only runtime worker worker-only prod-check reset-db \
	cleanup-legacy-sessions

.DEFAULT_GOAL := help

help: ## Показать эту справку
	@echo "LiberNovusBot — управление Docker Compose"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

data-dirs: ## Создать каталоги для bind-mount volumes (../mini-app-data)
	mkdir -p $(DATA_DIR)/{redis-data,rabbitmq-data,rabbitmq-logs,prometheus-data,grafana-data,pgdata}

test-db: ## Создать тестовую БД в контейнере Postgres
	$(COMPOSE) exec db createdb -U postgres mini_app_db_test || true

test: ## Запустить все тесты (ENV_MODE=test, offline mock)
	ENV_MODE=test TEST_DATABASE_URL=$(TEST_DATABASE_URL) poetry run pytest -v

test-smoke: ## Smoke guard-тесты offline (без OpenAI)
	ENV_MODE=test TEST_DATABASE_URL=$(TEST_DATABASE_URL) poetry run pytest tests/smoke/ -v

define OPENAI_SMOKE_RUN
bash -euo pipefail -c '\
	[ -f .env ] || { echo "error: .env not found"; exit 1; }; \
	set -a; source ./.env; set +a; \
	[ -n "$${OPENAI_API_KEY:-}" ] || { echo "error: OPENAI_API_KEY is not set in .env"; exit 1; }; \
	case "$${OPENAI_API_KEY}" in sk-test-should-be-ignored|"") \
		echo "error: OPENAI_API_KEY looks like a placeholder"; exit 1;; esac; \
	export RUN_OPENAI_SMOKE=true ENV_MODE=local LLM_PROVIDER=openai; \
	export TEST_DATABASE_URL="$(TEST_DATABASE_URL)"; \
	$(1)'
endef

define OPENAI_E2E_RUN
bash -euo pipefail -c '\
	[ -f .env ] || { echo "error: .env not found"; exit 1; }; \
	set -a; source ./.env; set +a; \
	[ -n "$${OPENAI_API_KEY:-}" ] || { echo "error: OPENAI_API_KEY is not set in .env"; exit 1; }; \
	case "$${OPENAI_API_KEY}" in sk-test-should-be-ignored|"") \
		echo "error: OPENAI_API_KEY looks like a placeholder"; exit 1;; esac; \
	export RUN_OPENAI_E2E=true ENV_MODE=local LLM_PROVIDER=openai; \
	export TEST_DATABASE_URL="$(TEST_DATABASE_URL)"; \
	$(1)'
endef

openai-smoke: ## Live OpenAI smoke: orchestrator + async runtime paths
	@$(call OPENAI_SMOKE_RUN,poetry run pytest tests/smoke/ -m openai_smoke -v -s)

openai-runtime-smoke: ## Live OpenAI smoke: async runtime worker path only
	@$(call OPENAI_SMOKE_RUN,poetry run pytest tests/smoke/test_openai_runtime_smoke.py -m openai_smoke -v -s)

openai-e2e-smoke: ## Live OpenAI E2E: webhook intake -> worker -> contract -> fake delivery
	@$(call OPENAI_E2E_RUN,poetry run pytest tests/smoke/test_openai_e2e_pipeline.py -m openai_e2e -v -s)

test-services: ## Запустить service integration tests
	ENV_MODE=test TEST_DATABASE_URL=$(TEST_DATABASE_URL) poetry run pytest tests/services/ -v

local-up: data-dirs ## Запустить стек в local-режиме
	ENV_MODE=local $(COMPOSE) up --build -d

api-only: data-dirs ## API без in-process runtime worker
	ENV_MODE=local ANALYSIS_RUNTIME_ENABLED=false $(COMPOSE) up --build -d $(API_SERVICE)

runtime: data-dirs ## API с in-process runtime worker (текущая архитектура)
	ENV_MODE=local ANALYSIS_RUNTIME_ENABLED=true $(COMPOSE) up --build -d $(API_SERVICE)

worker: runtime ## Alias: worker = in-process runtime mode, не отдельный service

worker-only: data-dirs ## То же что runtime; отдельного worker service пока нет
	@echo "NOT A SEPARATE SERVICE YET"
	@echo "Runs API container with ANALYSIS_RUNTIME_ENABLED=true (in-process worker)"
	ENV_MODE=local ANALYSIS_RUNTIME_ENABLED=true $(COMPOSE) up --build -d $(API_SERVICE)

prod-check: ## Проверить prod-конфигурацию (pure validation, без запуска API)
	ENV_MODE=prod poetry run python -c "import main; main.validate_startup()"

reset-db: ## Пересоздать только Postgres volume
	$(COMPOSE) down -v
	$(COMPOSE) up -d db

cleanup-legacy-sessions: ## Dry-run удаления сессий без policy traces (legacy pre-#026)
	PYTHONPATH=. poetry run python scripts/cleanup_legacy_sessions.py

cleanup-legacy-sessions-execute: ## Удалить сессии без policy traces и связанные dreams/jobs/analyses
	PYTHONPATH=. poetry run python scripts/cleanup_legacy_sessions.py --execute

up: local-up ## Запустить все сервисы (alias на local-up)

start: up ## То же, что up

down: ## Остановить и удалить контейнеры
	$(COMPOSE) down

stop: down ## То же, что down

restart: ## Перезапустить стек
	$(COMPOSE) down
	ENV_MODE=local $(COMPOSE) up --build -d

build: ## Только пересобрать образ API
	$(COMPOSE) build $(API_SERVICE)

pull: ## Скачать образы без запуска
	$(COMPOSE) pull

ps: ## Статус контейнеров
	$(COMPOSE) ps -a

logs: ## Логи всех сервисов (follow)
	$(COMPOSE) logs -f --tail=100

logs-api: ## Логи только API
	$(COMPOSE) logs -f --tail=100 $(API_SERVICE)

logs-bot: ## Логи Telegram-бота
	$(COMPOSE) logs -f --tail=100 telegram_bot

shell: ## Bash в контейнере API
	$(COMPOSE) exec $(API_SERVICE) bash

recreate: ## Пересоздать контейнеры без удаления volumes
	$(COMPOSE) up --build -d --force-recreate

down-v: ## Остановить и удалить volumes (данные БД/Redis)
	@echo "Внимание: удалятся данные в volumes проекта."
	$(COMPOSE) down -v
