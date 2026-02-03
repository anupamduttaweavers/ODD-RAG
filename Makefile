.PHONY: help install dev run test lint format clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make install       - Install production dependencies"
	@echo "  make dev           - Install development dependencies"
	@echo "  make run           - Run the FastAPI server via uvicorn"
	@echo "  make test          - Run tests with coverage"
	@echo "  make lint          - Run code quality checks"
	@echo "  make format        - Format code"
	@echo "  make clean         - Clean cache files"

# Install production dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Install development dependencies
dev: install
	pip install -e .

# Run the FastAPI server via uvicorn
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests with coverage
test:
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

# Run linting
lint:
	flake8 app/ tests/
	mypy app/
	isort --check-only app/ tests/
	black --check app/ tests/

# Format code
format:
	isort app/ tests/
	black app/ tests/

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
