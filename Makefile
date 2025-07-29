.PHONY: help install test lint format typecheck clean run dev setup

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linter"
	@echo "  make format     - Format code"
	@echo "  make typecheck  - Run type checker"
	@echo "  make clean      - Clean cache files"
	@echo "  make run        - Run the application (requires ORG and PROJECT)"
	@echo "  make dev        - Run in development mode with mock data"
	@echo "  make setup      - Initial project setup"

install:
	pip install -r requirements.txt

test:
	pytest -v

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

lint:
	ruff check src tests

format:
	black src tests

typecheck:
	mypy src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf htmlcov

run:
	@if [ -z "$(ORG)" ] || [ -z "$(PROJECT)" ]; then \
		echo "Usage: make run ORG='Organization Name' PROJECT='project-slug'"; \
		exit 1; \
	fi
	python -m src.main "$(ORG)" "$(PROJECT)"

dev:
	python -m src.main "Test Organization" "test-project"

setup:
	@echo "Setting up project..."
	cp .env.example .env
	make install
	@echo "Setup complete! Edit .env file to add your API keys."