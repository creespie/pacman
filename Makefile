CONFIG ?= config.json

.PHONY: install run debug clean lint

install:
	uv sync

run:
	uv run pacman $(CONFIG)

debug:
	uv run python -m pdb -m pacman $(CONFIG)

clean:
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
	rm -rf .mypy_cache build dist src/*.egg-info

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any \
	              --warn-unused-ignores \
	              --ignore-missing-imports \
	              --disallow-untyped-defs \
	              --check-untyped-defs
