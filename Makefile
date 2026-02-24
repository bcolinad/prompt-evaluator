.PHONY: setup dev test lint format migrate docker-up docker-down docker-reset docker-dev docker-prod docker-dev-down docker-prod-down clean

# ── Setup ─────────────────────────────────────────────
setup: docker-up
	uv sync --extra dev
	cp -n .env.example .env || true
	uv run alembic upgrade head
	@echo "✅ Setup complete. Run 'make dev' to start."

# ── Docker (infrastructure only) ─────────────────────
docker-up:
	docker compose -f docker/docker-compose.yml down -v && docker compose -f docker/docker-compose.yml up --build

docker-down:
	docker compose -f docker/docker-compose.yml down -v

docker-reset:
	docker compose -f docker/docker-compose.yml down -v
	docker compose -f docker/docker-compose.yml up -d

# ── Docker (full stack with app) ─────────────────────
docker-dev:
	docker compose -f docker/docker-compose.yml --profile dev up --build

docker-dev-down:
	docker compose -f docker/docker-compose.yml --profile dev down

docker-prod:
	docker compose -f docker/docker-compose.yml --profile prod up --build -d

docker-prod-down:
	docker compose -f docker/docker-compose.yml --profile prod down

# ── Development (local, no Docker app) ───────────────
dev:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .files/
	rm -rf htmlcov/ .coverage
	find .chainlit -mindepth 1 ! -name 'config.toml' -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Chainlit cache cleared (config.toml preserved)"
	uv run python run.py run src/app.py

# ── Database ──────────────────────────────────────────
migrate:
	uv run alembic upgrade head

migration:
	@read -p "Migration message: " msg; \
	uv run alembic revision --autogenerate -m "$$msg"

# ── Quality ───────────────────────────────────────────
test:
	uv run pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=80

test-unit:
	uv run pytest tests/unit/ -v -m unit

test-integration:
	uv run pytest tests/integration/ -v -m integration

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

format:
	uv run ruff check src/ tests/ --fix
	uv run ruff format src/ tests/

# ── Cleanup ───────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .files/
	rm -rf htmlcov/ .coverage
	find .chainlit -mindepth 1 ! -name 'config.toml' -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Chainlit cache cleared (config.toml preserved)"
