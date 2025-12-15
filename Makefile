compose := docker compose -f infra/docker-compose.yml

.PHONY: up down logs test lint format migrate seed

up:
	$(compose) up --build -d

down:
	$(compose) down

logs:
	$(compose) logs -f

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
