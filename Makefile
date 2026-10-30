PYTHON ?= python
PNPM ?= pnpm

.PHONY: setup test build run
setup:
	$(PYTHON) -m pip install -r sistema-estudo/requirements.txt
	cd sistema-estudo && $(PNPM) install --frozen-lockfile

test:
	$(PYTHON) -m unittest discover -s sistema-estudo/tests -v

build:
	cd sistema-estudo && $(PNPM) run build

run: build
	cd sistema-estudo && $(PYTHON) scripts/inicializar.py
	cd sistema-estudo && $(PYTHON) -m estudo
