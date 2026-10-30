PYTHON ?= python
PNPM ?= pnpm

.PHONY: setup test lint build run
setup:
	$(PYTHON) -m pip install -e ".[dev,extract]"
	cd sistema-estudo && $(PNPM) install --frozen-lockfile

test:
	$(PYTHON) -m unittest discover -s tests/pipeline -v
	$(PYTHON) sistema-estudo/tests/run_demo_suite.py
	cd sistema-estudo && $(PNPM) test

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) tools/check_repository.py
	cd sistema-estudo && $(PNPM) run lint

build:
	cd sistema-estudo && $(PNPM) run build

run: build
	cd sistema-estudo && $(PYTHON) scripts/inicializar.py
	cd sistema-estudo && $(PYTHON) -m estudo
