.PHONY: sync lint test eval

sync:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

eval:
	uv run python evals/run_evals.py
