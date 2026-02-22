.PHONY: help start lint clean db install dev build test

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "  install              Install all dependencies (Python + Node)"
	@echo "  dev                  Start development servers (backend + frontend)"
	@echo "  start [target]       Start application (local|docker|app)"
	@echo "  build                Build frontend"
	@echo "  lint [target]        Run linters (all|py|js|format)"
	@echo "  test [target]        Run tests (all|py|js)"
	@echo "  db [action]          Database operations (migrate|blank|migration)"
	@echo "  clean                Clean build artifacts and dependencies"
	@echo ""
	@echo "Examples:"
	@echo "  make install"
	@echo "  make start target=local"
	@echo "  make lint target=all"
	@echo "  make db action=migrate"

# Install all dependencies
install:
	@echo "Installing Python dependencies..."
	uv sync --group dev
	@echo "Installing Node dependencies..."
	cd frontend && npm ci
	@echo "Done!"

# Development mode
dev:
	@echo "Starting development servers..."
	@echo "Backend: http://127.0.0.1:8000"
	@echo "Frontend: http://127.0.0.1:5173"
	@echo ""
	@echo "Run backend manually:"
	@echo "  PYTHONPATH=backend uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
	@echo ""
	@echo "Run frontend manually:"
	@echo "  cd frontend && npm run dev"

# Start application
# Usage: make start target=local|docker|app
start:
ifeq ($(target),local)
	@echo "Starting backend locally..."
	PYTHONPATH=backend uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
else ifeq ($(target),docker)
	@echo "Starting with Docker..."
	docker-compose up --build
else ifeq ($(target),app)
	@echo "Starting Tauri app..."
	cd frontend && npm run tauri:dev
else
	@echo "Error: target not specified or invalid"
	@echo "Usage: make start target=local|docker|app"
	@exit 1
endif

# Linting
# Usage: make lint target=all|py|js|format
lint:
ifeq ($(target),all)
	@echo "Running all linters..."
	uv run --group dev ruff check backend tests
	uv run --group dev ruff format --check backend tests
	cd frontend && npm run lint
	cd frontend && npm run format:check
else ifeq ($(target),py)
	@echo "Running Python linters..."
	uv run --group dev ruff check backend tests
	uv run --group dev ruff format --check backend tests
else ifeq ($(target),js)
	@echo "Running JavaScript linters..."
	cd frontend && npm run lint
	cd frontend && npm run format:check
else ifeq ($(target),format)
	@echo "Formatting code..."
	uv run --group dev ruff format backend tests
	cd frontend && npm run format:write
else
	@echo "Error: target not specified or invalid"
	@echo "Usage: make lint target=all|py|js|format"
	@exit 1
endif

# Testing
# Usage: make test target=all|py|js
test:
ifeq ($(target),all)
	@echo "Running all tests..."
	uv run pytest tests/backend
	cd frontend && npm test
else ifeq ($(target),py)
	@echo "Running Python tests..."
	uv run pytest tests/backend
else ifeq ($(target),js)
	@echo "Running JavaScript tests..."
	cd frontend && npm test
else
	@echo "Error: target not specified or invalid"
	@echo "Usage: make test target=all|py|js"
	@exit 1
endif

# Database operations
# Usage: make db action=migrate|blank|migration
db:
ifeq ($(action),migrate)
	@echo "Running migrations..."
	PYTHONPATH=backend uv run alembic -c alembic.ini upgrade head
else ifeq ($(action),blank)
	@echo "Creating blank migration..."
	PYTHONPATH=backend uv run alembic -c alembic.ini revision --autogenerate -m "$(or $(message),auto migration)"
else ifeq ($(action),migration)
	@echo "Creating new migration..."
	PYTHONPATH=backend uv run alembic -c alembic.ini revision -m "$(or $(message),new migration)"
else
	@echo "Error: action not specified or invalid"
	@echo "Usage: make db action=migrate|blank|migration [message=\"Your message\"]"
	@exit 1
endif

# Build frontend
build:
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Frontend synced to templates/index.html and static/assets/"

# Clean build artifacts and dependencies
clean:
	@echo "Cleaning build artifacts..."
	rm -rf dist
	rm -rf static/assets
	rm -f templates/index.html
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .data/*.sqlite3
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete!"

# Clean dependencies (use with caution)
clean-deps:
	@echo "Removing dependencies..."
	rm -rf .venv
	rm -rf node_modules
	rm -rf frontend/node_modules
	@echo "Dependencies removed. Run 'make install' to reinstall."
