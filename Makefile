.PHONY: api web test lint docker-up docker-down

api:
	cd apps/api && uvicorn app.main:app --reload

web:
	npm --workspace apps/web run dev

test:
	cd apps/api && pytest

lint:
	cd apps/api && ruff check .
	npm --workspace apps/web run lint

docker-up:
	docker compose -f infra/docker/docker-compose.yml up --build

docker-down:
	docker compose -f infra/docker/docker-compose.yml down