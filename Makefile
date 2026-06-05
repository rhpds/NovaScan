.PHONY: test test-cov lint clean install

PYTHONPATH := src
export PYTHONPATH

test:
	python3 -m pytest tests/ -v

test-cov:
	python3 -m pytest tests/ -v --cov=novascan --cov-report=term-missing

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .coverage htmlcov dist build

install:
	pip install -e ".[dev]"
