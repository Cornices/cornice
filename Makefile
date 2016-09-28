HERE = $(shell pwd)
VENV = $(HERE)/venv
BIN = $(VENV)/bin
PYTHON = $(BIN)/python
VIRTUALENV = virtualenv
INSTALL = $(BIN)/pip install --no-deps
DOC_STAMP = $(VENV)/.doc_env_installed.stamp

.PHONY: all test docs build_extras

all: build

$(PYTHON):
	$(VIRTUALENV) $(VENV)

build: $(PYTHON)
	$(PYTHON) setup.py develop

clean:
	rm -rf $(VENV)

test_dependencies:
	$(BIN)/pip install tox

test: build test_dependencies
	$(BIN)/tox

docs:
	cd docs && $(MAKE) html SPHINXBUILD=$(VENV)/bin/sphinx-build
