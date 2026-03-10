.PHONY: help install test lint format clean

help:
@echo "Available commands:"
@echo "  make install    Install dependencies"
@echo "  make test       Run tests"
@echo "  make lint       Run linters"
@echo "  make format     Format code"
@echo "  make clean      Clean build artifacts"

install:
uv pip install -e ".[dev]"

test:
pytest tests/ -v --cov=src

lint:
ruff check src/ tests/
mypy src/

format:
black src/ tests/
isort src/ tests/

clean:
rm -rf build/
rm -rf dist/
rm -rf *.egg-info
rm -rf .pytest_cache/
rm -rf .mypy_cache/
rm -rf .ruff_cache/
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
