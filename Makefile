# Virtual environment settings
VENV_DIR := venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
VENV_MARKER := $(VENV_DIR)/bin/activate

.DEFAULT_GOAL := help

# Check and create venv if needed
venv-check:
	@if [ ! -f $(VENV_MARKER) ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV_DIR); \
		echo "✓ Virtual environment created at ./$(VENV_DIR)"; \
		echo "  Upgrading pip..."; \
		$(PIP) install --upgrade pip --quiet; \
		echo "✓ Virtual environment ready"; \
	fi
.PHONY: venv-check

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
.PHONY: help

# Installation
install: venv-check ## Install production dependencies
	$(PIP) install .
.PHONY: install

install-dev: venv-check ## Install development dependencies (testing, linting, formatting)
	$(PIP) install -e .[dev]
	@echo ""
	@echo "✓ Development dependencies installed"
	@echo "  You can now run: make ci, make test, make lint, make format"
.PHONY: install-dev

test: venv-check ## Run tests
	@$(PYTHON) -c "import pytest" 2>/dev/null || \
		(echo "Error: pytest not found. Run 'make install-dev' first." && exit 1)
	$(PYTHON) -m pytest
.PHONY: test

test-cov: venv-check ## Run tests with coverage report
	@$(PYTHON) -c "import pytest" 2>/dev/null || \
		(echo "Error: pytest not found. Run 'make install-dev' first." && exit 1)
	$(PYTHON) -m pytest --cov=. --cov-report=term-missing --cov-report=html
.PHONY: test-cov

lint: venv-check ## Run linting with ruff
	@$(PYTHON) -c "import ruff" 2>/dev/null || \
		(echo "Error: ruff not found. Run 'make install-dev' first." && exit 1)
	$(PYTHON) -m ruff check .
	@$(PYTHON) -c "import black" 2>/dev/null || \
		(echo "Error: black not found. Run 'make install-dev' first." && exit 1)
	$(PYTHON) -m black --check .
	@echo "✓ All code quality checks passed"
.PHONY: lint

lint-fix: venv-check ## Auto fix linting issues with ruff and black
	@$(PYTHON) -c "import ruff" 2>/dev/null || \
		(echo "Error: ruff not found. Run 'make install-dev' first." && exit 1)
	$(PYTHON) -m ruff check . --fix
	@$(PYTHON) -c "import black" 2>/dev/null || \
		(echo "Error: black not found. Run 'make install-dev' first." && exit 1)
	$(PYTHON) -m black .
.PHONY: lint-fix

# Running locally
run: venv-check ## Run application with Hypercorn (production-like)
	MEMORIAL_STRIP_PORT=true $(PYTHON) -m hypercorn memorial:app --bind 0.0.0.0:8080
.PHONY: run

run-dev: venv-check ## Run Quart development server
	QUART_DEBUG=true MEMORIAL_STRIP_PORT=true $(PYTHON) memorial.py
.PHONY: run-dev

# Docker
docker-build: ## Build Docker image
	docker build -t memorial .
.PHONY: docker-build

docker-run: ## Run Docker container
	docker run -d --name memorial -p 127.0.0.1:8080:8080 memorial
.PHONY: docker-run

docker-stop: ## Stop and remove Docker container
	docker stop memorial || true
	docker rm memorial || true
.PHONY: docker-stop

# Docker Compose
docker-compose-up: ## Start services with docker-compose
	docker-compose up -d
.PHONY: docker-compose-up

docker-compose-down: ## Stop services with docker-compose
	docker-compose down
.PHONY: docker-compose-down

docker-compose-logs: ## Show docker-compose logs
	docker-compose logs -f
.PHONY: docker-compose-logs

docker-compose-build: ## Build services with docker-compose
	docker-compose build
.PHONY: docker-compose-build

# CI/CD - Run all checks
ci: lint test ## Run all CI checks (lint, test)
	@echo ""
	@echo "=================================="
	@echo "✓ All CI checks passed!"
	@echo "=================================="
.PHONY: ci

# Cleanup
clean: ## Remove build artifacts and cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf build/ dist/ 2>/dev/null || true
	@echo "✓ Cleaned up build artifacts and cache files"
.PHONY: clean

clean-all: clean ## Remove venv and all build artifacts
	rm -rf $(VENV_DIR)
	@echo "✓ Removed virtual environment"
.PHONY: clean-all
