# PAIEP — stack lifecycle (M0) + RAG workflow shortcuts (M2–M4).
# Run from repo root:  make -C docker <target>   (or `cd docker && make <target>`)
# Requires Docker Desktop + Compose v2 (see ../docs/setup/environment.md).

COMPOSE ?= docker compose
PROFILE ?= core
PROJECT ?= paiep
ARGS    ?=

.DEFAULT_GOAL := help
.PHONY: help config up down ps logs health restart clean nuke \
        build qdrant-init ingest ask eval bench test memory migrate

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

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

# --- RAG workflow (M2–M4) ----------------------------------------------------

build: ## Rebuild the ingest/rag image (needed after rag/ or scripts/ code changes)
	$(COMPOSE) --profile ingest build ingest

qdrant-init: ## Create Qdrant collections + payload indexes (M2). ARGS=--verify for smoke test
	../scripts/qdrant-init.sh $(ARGS)

ingest: ## Ingest the corpus (M3). e.g. ARGS="knowledge --prune" (default: knowledge)
	$(COMPOSE) --profile ingest run --rm ingest $(ARGS)

ask: ## Grounded RAG answer (M4). Q="question" [ARGS="--scope global --json"]
	@if [ -z "$(Q)" ]; then echo 'Usage: make ask Q="your question" [ARGS=...]'; exit 1; fi
	$(COMPOSE) --profile rag run --rm rag "$(Q)" $(ARGS)

eval: ## Retrieval recall@k eval (M4). ARGS="--k 4 --json" / "--answers"
	$(COMPOSE) --profile rag run --rm --entrypoint python rag /app/benchmarks/m4/eval.py $(ARGS)

bench: ## Inference benchmark (M1). ARGS="<model> <runs>"
	../benchmarks/m1/run-bench.sh $(ARGS)

memory: ## Memory CLI (M5). ARGS='recall "query" --scope project:x' (see: ARGS=--help)
	$(COMPOSE) --profile memory run --rm memory $(ARGS)

migrate: ## Memory schema migrations (M5). ARGS=status|up|down (default: status)
	$(COMPOSE) --profile memory run --rm memory migrate $(or $(ARGS),status)

test: ## Lint + offline unit tests (host; pip install -r requirements-dev.txt first)
	cd .. && ruff check . && pytest
