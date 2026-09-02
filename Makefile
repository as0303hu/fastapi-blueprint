# Makefile
SHELL := /bin/bash
.DEFAULT_GOAL := help
VENV := .venv
VENV_MARKER := $(VENV)/.marker

.PHONY: help
help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1,$$2}'

# -- Environment -------------------------------------------------------------

.PHONY: venv
venv: $(VENV_MARKER) ## Create virtual environment and install dependencies

$(VENV_MARKER): pyproject.toml
	uv sync
	@touch $(VENV_MARKER)

# -- Code Quality ------------------------------------------------------------

.PHONY: format
format: ## Format code with ruff
	uv run ruff format .
	uv run ruff check --select I --fix .

.PHONY: lint
lint: ## Run linters (ruff + pyright)
	uv run ruff check .
	uv run pyright src/

.PHONY: lint-fix
lint-fix: ## Auto-fix lint issues
	uv run ruff check --fix .

# -- Testing -----------------------------------------------------------------

.PHONY: test
test: ## Run unit tests
	uv run pytest tests/ -m "not integration and not e2e" -v

.PHONY: test_integration
test_integration: ## Run integration tests (requires Docker)
	uv run pytest tests/ -m integration -v -s

.PHONY: test_e2e
test_e2e: ## Run end-to-end tests
	uv run pytest tests/ -m e2e -v -s

.PHONY: test_all
test_all: ## Run all tests
	uv run pytest tests/ -v

.PHONY: coverage
coverage: ## Run tests with coverage report
	uv run coverage run -a pytest tests/ -m "not integration and not e2e"
	uv run coverage report -m
	uv run coverage html
	uv run coverage xml

# -- Database ----------------------------------------------------------------

.PHONY: migrate
migrate: ## Run database migrations
	uv run alembic upgrade head

.PHONY: migrate-create
migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	uv run alembic revision --autogenerate -m "$(msg)"

.PHONY: migrate-rollback
migrate-rollback: ## Rollback last migration
	uv run alembic downgrade -1

# -- Docker ------------------------------------------------------------------

.PHONY: up
up: ## Start local infrastructure (Postgres + LocalStack)
	docker compose up -d

.PHONY: down
down: ## Stop local infrastructure
	docker compose down

.PHONY: logs
logs: ## Tail infrastructure logs
	docker compose logs -f

.PHONY: build
build: ## Build Docker image
	docker build -t fastapi-blueprint:latest .

# -- Application -------------------------------------------------------------

.PHONY: run
run: ## Start the application locally
	uv run python main.py

.PHONY: clean
clean: ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage coverage.xml .ruff_cache
