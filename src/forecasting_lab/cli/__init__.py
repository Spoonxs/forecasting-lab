"""Command-line entry points.

Each module exposes ``main(argv=None)`` and is wired as a console script in
``pyproject.toml``. They are also runnable directly, e.g.::

    python -m forecasting_lab.cli.elo_backtest --synthetic
"""
