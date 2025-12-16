compose := docker compose -f infra/docker-compose.yml
compose-dev := docker compose -f infra/docker-compose.dev.yml

.PHONY: up up-dev down down-dev logs logs-dev test lint format migrate seed

up:
	$(compose) up --build -d

up-dev:
	$(compose-dev) up --build -d

down:
	$(compose) down

down-dev:
	$(compose-dev) down

logs:
	$(compose) logs -f

logs-dev:
	$(compose-dev) logs -f

test:
	cd backend && pytest -q

lint:
	cd backend && python -m py_compile app/**/*.py

format:
	cd backend && python -m black app || true

migrate:
	cd migrations && alembic upgrade head || alembic revision --autogenerate -m "init" && alembic upgrade head

seed:
	python scripts/seed.py
