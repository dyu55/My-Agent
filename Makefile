.PHONY: install test lint check demo build
install:
	uv sync --extra dev
test:
	uv run pytest --cov=myagent --cov-report=term-missing --cov-fail-under=85
lint:
	uv run ruff check .
	uv run ruff format --check .
check: lint test
demo:
	uv run myagent demo --workspace /tmp/myagent-demo
build:
	uv run python -m build
