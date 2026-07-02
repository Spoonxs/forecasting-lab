# Convenience targets. On Windows without `make`, run the commands directly
# (see README "Quickstart") or use Git Bash / WSL.

.PHONY: install dev test lint demo clean

install:        ## install core + all extras in editable mode
	pip install -e ".[all]"

dev: install    ## alias for install

test:           ## run the test suite
	pytest

lint:           ## lint with ruff
	ruff check src tests

demo:           ## run the headline Elo calibration backtest on synthetic data
	python -m forecasting_lab.cli.elo_backtest --synthetic

clean:          ## remove caches and build artifacts
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
