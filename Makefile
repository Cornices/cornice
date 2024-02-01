VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python
SPHINX_BUILD = $(shell realpath ${VENV})/bin/sphinx-build
INSTALL_STAMP = $(VENV)/.install.stamp

.PHONY: all
all: install

install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) pyproject.toml requirements.txt
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install -r docs/requirements.txt
	$(VENV)/bin/pip install -e ".[dev]"
	touch $(INSTALL_STAMP)

$(PYTHON):
	python3 -m venv $(VENV)

requirements.txt: requirements.in
	pip-compile

.PHONY: test
test: install
	$(VENV)/bin/pytest --cov-report term-missing --cov-fail-under 100 --cov cornice

.PHONY: lint
lint: install
	$(VENV)/bin/ruff check src tests
	$(VENV)/bin/ruff format --check src tests

.PHONY: format
format: install
	$(VENV)/bin/ruff check --fix src tests
	$(VENV)/bin/ruff format src tests

docs: install
	cd docs && $(MAKE) html SPHINXBUILD=$(SPHINX_BUILD)

.IGNORE: clean
clean:
	find src -name '__pycache__' -type d -exec rm -fr {} \;
	find tests -name '__pycache__' -type d -exec rm -fr {} \;
	rm -rf .venv .coverage *.egg-info .pytest_cache .ruff_cache build dist
