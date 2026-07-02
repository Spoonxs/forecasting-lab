"""Project paths and configuration.

Resolution order for the project root:
1. ``$FLAB_ROOT`` environment variable, if set.
2. The nearest ancestor directory containing ``pyproject.toml``.
3. The current working directory (last resort).

Directories (``data/``, ``cache/``, ``inputs/``) are created on first access so
nothing in the codebase has to ``mkdir`` defensively.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

# Load a .env file if python-dotenv is available; otherwise rely on real env.
try:  # pragma: no cover - trivial optional import
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def _find_root() -> Path:
    env = os.environ.get("FLAB_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd().resolve()


PROJECT_ROOT: Path = _find_root()


def _dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class Paths:
    """Canonical project locations. Access creates the directory if missing."""

    root: Path = PROJECT_ROOT

    @property
    def data(self) -> Path:
        return _dir(self.root / "data")

    @property
    def cache(self) -> Path:
        return _dir(self.root / "cache")

    @property
    def inputs(self) -> Path:
        """Where the pipeline files dated research digests (see master-index.md)."""
        return _dir(self.root / "inputs")

    @property
    def config_file(self) -> Path:
        return self.root / "config" / "config.yaml"


PATHS = Paths()


@dataclass(frozen=True)
class Settings:
    """Runtime knobs, overridable via config/config.yaml and the environment."""

    # HTTP client
    user_agent: str = "forecasting-lab/0.1 (research; contact via repo)"
    http_timeout: float = 20.0
    http_max_retries: int = 4
    http_backoff: float = 0.5

    # Cache TTLs (seconds) — public market endpoints are flaky, cache aggressively.
    cache_ttl_markets: int = 300

    # Kalshi rate limit (~10 req/s per key; stay under it).
    kalshi_min_interval: float = 0.12

    # Secrets pulled from the environment (never hard-code).
    kalshi_api_key_id: str | None = field(default_factory=lambda: os.environ.get("KALSHI_API_KEY_ID"))
    kalshi_private_key_path: str | None = field(
        default_factory=lambda: os.environ.get("KALSHI_PRIVATE_KEY_PATH")
    )
    quiver_api_key: str | None = field(default_factory=lambda: os.environ.get("QUIVER_API_KEY"))

    extra: dict[str, Any] = field(default_factory=dict)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings, layering config/config.yaml over the defaults."""
    base: dict[str, Any] = {}
    cfg = PATHS.config_file
    if cfg.exists():
        try:
            import yaml

            loaded = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                base = loaded
        except Exception:  # pragma: no cover - bad config shouldn't crash imports
            base = {}
    known = {f.name for f in Settings.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    kwargs = {k: v for k, v in base.items() if k in known}
    extra = {k: v for k, v in base.items() if k not in known}
    return Settings(extra=extra, **kwargs)
