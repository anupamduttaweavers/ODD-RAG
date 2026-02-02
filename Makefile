.PHONY: help install dev run test lint format clean docker-build docker-up docker-down migrate

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make dev          - Install development dependencies"
	@echo "  make run          - Run the FastAPI server locally"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with black and isort"
	@echo "  make clean        - Clean up cache files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make migrate      - Run database migrations"

# Install production dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Install development dependencies
dev: install
	pip install -e .

# Run the FastAPI server
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

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database migrations
migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"
