PYTHON ?= python
PNPM ?= pnpm
FRONTEND := packages/estudo/frontend
PLAN ?= plans/apofp-2026/roadmap.json
PIPELINE_ARGS ?= --help
PYTHON_PACKAGES := -e packages/contracts -e packages/pipeline -e packages/estudo/backend

.PHONY: setup test lint build run pipeline test-e2e test-packages
setup:
	$(PYTHON) -m pip install $(PYTHON_PACKAGES) -e ".[dev,extract]"
	$(PNPM) --dir $(FRONTEND) install --frozen-lockfile

test:
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) -m unittest discover -s packages/pipeline/tests -v
	$(PYTHON) packages/estudo/backend/tests/run_demo_suite.py
	$(PNPM) --dir $(FRONTEND) test

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) tools/check_repository.py
	$(PNPM) --dir $(FRONTEND) run lint

build:
	$(PNPM) --dir $(FRONTEND) run build

run: build
	$(PYTHON) -m estudo init --plan $(PLAN)
	$(PYTHON) -m estudo

pipeline:
	$(PYTHON) -m concurso_pipeline $(PIPELINE_ARGS)

test-e2e: build
	$(PNPM) --dir $(FRONTEND) run test:e2e

test-packages:
	$(PYTHON) tools/check_packages.py
