# PAIEP — M0 baseline lifecycle.
# Run from repo root:  make -C docker <target>   (or `cd docker && make <target>`)
# Requires Docker Desktop + Compose v2 (see ../docs/setup/environment.md).

COMPOSE ?= docker compose
PROFILE ?= core
PROJECT ?= paiep

.DEFAULT_GOAL := help
.PHONY: help config up down ps logs health restart clean nuke

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-9s\033[0m %s\n", $$1, $$2}'

config: ## Validate the Compose file (lint)
	$(COMPOSE) config -q && echo "compose config OK"

up: ## Start the stack for PROFILE (default: core)
	$(COMPOSE) --profile $(PROFILE) up -d

down: ## Stop the stack (keeps named volumes / data)
	$(COMPOSE) --profile "*" down

ps: ## Show service status
	$(COMPOSE) --profile "*" ps

logs: ## Follow logs for PROFILE
	$(COMPOSE) --profile $(PROFILE) logs -f

health: ## Show health/status of PAIEP containers
	docker ps --filter "name=$(PROJECT)_" \
	  --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

restart: down up ## Restart the stack

clean: ## Preview volume removal (safe: dry run)
	@echo "Would remove volumes:"; docker volume ls -q --filter "name=$(PROJECT)_"

nuke: ## DESTRUCTIVE: stop and remove volumes (data loss). Requires CONFIRM=yes
	@if [ "$(CONFIRM)" != "yes" ]; then echo "Refusing: re-run with CONFIRM=yes"; exit 1; fi
	$(COMPOSE) --profile "*" down -v
