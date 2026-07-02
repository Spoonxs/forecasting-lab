from datetime import date

from forecasting_lab.pipeline import Pipeline, render_digest, write_dated_note
from forecasting_lab.pipeline.digest import dated_note_path
from forecasting_lab.utils.cache import DiskCache


def test_render_digest_structure():
    md = render_digest(
        "Title", {"Section A": "body a", "Section B": "body b"},
        on=date(2026, 6, 28), disclaimer="be careful",
    )
    assert "# Title" in md
    assert "## Section A" in md and "## Section B" in md
    assert "2026-06-28" in md
    assert "*be careful*" in md


def test_write_dated_note(tmp_path):
    path = write_dated_note("market-divergence", "hello", on=date(2026, 6, 28), out_dir=tmp_path)
    assert path.name == "2026-06-28-market-divergence.md"
    assert path.read_text(encoding="utf-8") == "hello"
    assert dated_note_path("x", on=date(2026, 1, 1), out_dir=tmp_path).name == "2026-01-01-x.md"


def test_pipeline_subclass_runs(tmp_path):
    class Dummy(Pipeline):
        slug = "dummy"

        def fetch(self):
            return [1, 2, 3]

        def process(self, raw):
            return f"sum={sum(raw)}"

    path = Dummy().run(on=date(2026, 6, 28), out_dir=tmp_path)
    assert path.read_text(encoding="utf-8") == "sum=6"


def test_disk_cache_ttl(tmp_path):
    cache = DiskCache("ns", ttl=100, root=tmp_path)
    cache.set("k", {"v": 1}, now=1000.0)
    assert cache.get("k", now=1050.0) == {"v": 1}  # within TTL
    assert cache.get("k", now=2000.0) is None  # expired
    # namespaces are isolated
    other = DiskCache("other", ttl=100, root=tmp_path)
    assert other.get("k", now=1050.0) is None
