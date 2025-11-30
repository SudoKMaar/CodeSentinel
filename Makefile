.PHONY: install test lint format clean run-api run-cli help

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make run-api    - Run API server"
	@echo "  make run-cli    - Run CLI help"

install:
	pip install -e .
	pip install -e ".[dev]"

test:
	pytest -v

test-cov:
	pytest --cov=. --cov-report=html --cov-report=term

lint:
	ruff check .
	mypy .

format:
	black .
	ruff check --fix .

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run-api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

run-cli:
	code-review-agent --help
