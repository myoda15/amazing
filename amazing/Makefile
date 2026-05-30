# A-Maze-ing Makefile
# Override the interpreter with: make run PYTHON=python3.12

PYTHON ?= python3
CONFIG ?= config.txt

.PHONY: help install run debug clean lint lint-strict build

help:
	@echo "Available targets:"
	@echo "  install      Install dev dependencies (flake8, mypy, build)"
	@echo "  run          Run the maze generator on $(CONFIG)"
	@echo "  debug        Run under the pdb debugger"
	@echo "  clean        Remove caches and build artifacts"
	@echo "  lint         Run flake8 and mypy (mandatory flags)"
	@echo "  lint-strict  Run flake8 and mypy --strict"
	@echo "  build        Build the mazegen pip package"

install:
	$(PYTHON) -m pip install --upgrade flake8 mypy build

run:
	$(PYTHON) a_maze_ing.py $(CONFIG)

debug:
	$(PYTHON) -m pdb a_maze_ing.py $(CONFIG)

clean:
	rm -rf __pycache__ */__pycache__ .mypy_cache .pytest_cache
	rm -rf build dist *.egg-info

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

build:
	$(PYTHON) -m build
