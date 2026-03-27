PYTHON ?= python
UV ?= uv

.PHONY: sync install run test lint format check pre-commit-install pre-commit-run

sync:
	$(UV) sync --extra dev

install: sync

run:
	$(UV) run opcua-tui

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check src tests

format:
	$(UV) run ruff format src tests

check:
	$(UV) run ruff check --fix src tests
	$(UV) run ruff format src tests
	$(UV) run pytest

pre-commit-install:
	$(UV) run pre-commit install --install-hooks

pre-commit-run:
	$(UV) run pre-commit run --all-files
