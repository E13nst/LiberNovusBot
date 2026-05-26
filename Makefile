COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yaml
API_SERVICE := mini_app_api
DATA_DIR := $(abspath $(CURDIR)/../mini-app-data)

export COMPOSE_FILE

.PHONY: help up down stop start restart build ps logs logs-api logs-bot shell recreate down-v pull data-dirs

.DEFAULT_GOAL := help

help: ## Показать эту справку
	@echo "LiberNovusBot — управление Docker Compose"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

data-dirs: ## Создать каталоги для bind-mount volumes (../mini-app-data)
	mkdir -p $(DATA_DIR)/{redis-data,rabbitmq-data,rabbitmq-logs,prometheus-data,grafana-data,pgdata}

up: data-dirs ## Запустить все сервисы (сборка + фон)
	$(COMPOSE) up --build -d

start: up ## То же, что up

down: ## Остановить и удалить контейнеры
	$(COMPOSE) down

stop: down ## То же, что down

restart: ## Перезапустить стек
	$(COMPOSE) down
	$(COMPOSE) up --build -d

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
