HERE = $(shell pwd)
VENV = $(HERE)/.venv
BIN = $(VENV)/bin
PYTHON = $(BIN)/python
VIRTUALENV = virtualenv

.PHONY: all test docs

all: build

$(PYTHON):
	$(VIRTUALENV) $(VENV)

build: $(PYTHON)
	$(PYTHON) setup.py develop

clean:
	rm -rf $(VENV)

test_dependencies: build
	$(BIN)/pip install tox

test: test_dependencies
	$(BIN)/tox

docs_dependencies: $(PYTHON)
	$(BIN)/pip install -r docs/requirements.txt

docs: docs_dependencies
	cd docs && $(MAKE) html SPHINXBUILD=$(VENV)/bin/sphinx-build
