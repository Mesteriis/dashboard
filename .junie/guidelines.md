### Project Guidelines

#### 1. Build & Configuration

The project is a full-stack application consisting of a FastAPI backend and a Vue 3 frontend. It uses `uv` for Python dependency management and `npm` for the frontend.

**Backend Setup:**
- Ensure `uv` is installed.
- Set up the environment variables (see `README.md` for the full list).
- Run the backend locally:
  ```bash
  export DATABASE_URL=postgresql+asyncpg://oko:oko@localhost:5432/oko
  export BROKER_URL=amqp://oko:oko@localhost:5672/
  export OKO_RUNTIME_ROLE=backend
  PYTHONPATH=backend uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- Use `docker-compose -f docker-compose.deps.yml up -d` to start dependencies (Postgres, RabbitMQ) for local development.

**Frontend Setup:**
- Navigate to the `frontend` directory.
- Install dependencies: `npm ci`.
- Start the development server: `npm run dev`.
- The frontend proxies `/api` requests to `http://127.0.0.1:8000` by default.

#### 2. Testing Information

**Backend Tests:**
- Uses `pytest`.
- To run tests, set `PYTHONPATH=backend`.
- Commands:
  - Run all tests: `PYTHONPATH=backend uv run pytest`
  - Run a specific test file: `PYTHONPATH=backend uv run pytest tests/backend/core/test_core_api.py`
  - Run without coverage (to avoid failure due to coverage thresholds): `PYTHONPATH=backend uv run pytest <path_to_test> --no-cov`
- **Adding Tests**: Place new backend tests in the `tests/backend/` directory. Use the `test_*.py` naming convention.

**Frontend Tests:**
- Uses Node.js's built-in test runner with `tsx`.
- Commands (from the `frontend` directory):
  - Run all tests: `npm run test`
  - Run a specific test file: `node --import tsx --test ../tests/frontend/some.test.mjs`
- **Adding Tests**: Place new frontend tests in the `tests/frontend/` directory. Use the `*.test.mjs` naming convention.

**Demonstration Tests:**
To verify the testing environment, you can run these simple tests:
- Backend: `PYTHONPATH=backend uv run pytest tests/backend/test_demo.py --no-cov`
- Frontend: `cd frontend && node --import tsx --test ../tests/frontend/demo.test.mjs`

#### 3. Additional Development Information

- **Code Style**: 
  - Backend: Follows standard Python (PEP 8) and FastAPI patterns. Async/await is used extensively.
  - Frontend: Vue 3 with Composition API (`<script setup>`) and TypeScript. Styles are managed with SCSS.
- **Project Structure**:
  - `backend/`: FastAPI application code.
  - `frontend/src/`: Vue application source.
  - `tests/`: Unified test directory for both backend and frontend.
  - `scripts/`: Utility scripts for build, deployment, and development.
- **Migrations**: Alembic is used for database migrations (`alembic/` directory).
- **Tauri**: The project includes configuration for building a desktop app using Tauri (`tauri/` directory).
