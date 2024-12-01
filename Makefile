.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help install db-up db-down migrate revision seed dev check clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install the API dependencies
	uv sync --locked

db-up: ## Start Postgres
	docker compose -f infra/docker-compose.yml up -d --wait

db-down: ## Stop Postgres, keep the data
	docker compose -f infra/docker-compose.yml down

migrate: ## Apply migrations to the development database
	uv run alembic upgrade head

revision: ## Generate a migration: make revision m="add employees"
	uv run alembic revision --autogenerate -m "$(m)"

seed: ## Load the demo agency
	uv run python -m cleared.seed

dev: ## Run the API with reload on :8000
	uv run uvicorn cleared.main:app --reload --port 8000

check: ## Run everything CI runs
	uv run ruff check .
	uv run ruff format --check .
	uv run pyright
	uv run pytest -q

clean: ## Remove caches and the virtual environment
	rm -rf .venv .pytest_cache .ruff_cache .coverage
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
