COMPOSE_FILE ?= infra/docker-compose.yml
PROFILE ?= gpu
PYTHON ?= python

ifeq ($(USE_GPU),0)
PROFILE = cpu
endif

.PHONY: setup lint typecheck test fmt demo smoke up up-gpu up-cpu bench clean

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]
	$(PYTHON) -m pip install pre-commit
	pre-commit install

lint:
	ruff check .

fmt:
	ruff format .
	ruff check --fix .

typecheck:
	mypy gateway bench

test:
	pytest

smoke:
	bash scripts/smoke_test.sh

demo:
	bash scripts/demo.sh

up:
	docker compose -f $(COMPOSE_FILE) --profile $(PROFILE) up --build

up-gpu:
	docker compose -f $(COMPOSE_FILE) --profile gpu up --build

up-cpu:
	docker compose -f $(COMPOSE_FILE) --profile cpu up --build

bench:
	bash scripts/bench.sh

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
