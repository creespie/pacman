CONFIG ?= config.json
PYTHON ?= uv run python

.PHONY: install run debug clean lint lint-strict test package

install:
	uv sync

run:
	$(PYTHON) pac-man.py $(CONFIG)

debug:
	$(PYTHON) -m pdb pac-man.py $(CONFIG)

test:
	uv run pytest -q

clean:
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache build dist src/*.egg-info

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any \
	              --warn-unused-ignores \
	              --ignore-missing-imports \
	              --disallow-untyped-defs \
	              --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

package:
	uv run pyinstaller pac-man.spec --noconfirm
