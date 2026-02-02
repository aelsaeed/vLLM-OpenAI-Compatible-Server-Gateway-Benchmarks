COMPOSE_FILE=infra/docker-compose.yml
PROFILE?=gpu

ifeq ($(USE_GPU),0)
PROFILE=cpu
endif

.PHONY: up bench test lint

up:
	docker compose -f $(COMPOSE_FILE) --profile $(PROFILE) up --build

bench:
	python -m bench.run_bench

test:
	pytest

lint:
	ruff check .
	mypy gateway bench
