from datetime import date

from forecasting_lab.pipeline.research import (
    ResearchPipeline,
    parse_atom,
    score_paper,
)

_ATOM_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2501.00001v1</id>
    <title>Calibration of  Prediction Market
      Forecasts</title>
    <summary>We study Brier score calibration and walk-forward validation of
      prediction market probabilities.</summary>
    <published>2026-06-28T00:00:00Z</published>
    <category term="q-fin.TR"/>
    <category term="stat.ML"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2501.00002v1</id>
    <title>A Note on Categorical Homotopy Theory</title>
    <summary>Pure mathematics, nothing about markets at all.</summary>
    <published>2026-06-27T00:00:00Z</published>
    <category term="math.CT"/>
  </entry>
</feed>"""


def test_parse_atom_normalizes_whitespace_and_fields():
    papers = parse_atom(_ATOM_SAMPLE)
    assert len(papers) == 2
    p = papers[0]
    assert p["title"] == "Calibration of Prediction Market Forecasts"
    assert p["published"] == "2026-06-28"
    assert "q-fin.TR" in p["categories"]
    assert parse_atom(b"not xml") == []


def test_score_paper_is_explainable():
    papers = parse_atom(_ATOM_SAMPLE)
    score, hits = score_paper(papers[0])
    # calibration + brier + prediction market + walk-forward + forecast all hit
    assert score >= 10
    assert "calibration" in hits and "walk-forward" in hits
    irrelevant_score, irrelevant_hits = score_paper(papers[1])
    assert irrelevant_score == 0 and irrelevant_hits == []


def test_score_respects_word_boundaries():
    # "elo" must not fire inside "developed"; "brier" not inside "sobriery"-like words
    paper = {"title": "We developed a new method", "summary": "It is developed further."}
    score, hits = score_paper(paper)
    assert "elo" not in hits and score == 0
    real = {"title": "An Elo rating study", "summary": ""}
    _, real_hits = score_paper(real)
    assert "elo" in real_hits


class _StubFetcher:
    def recent(self, categories, max_results=60):
        return _ATOM_SAMPLE


def test_pipeline_ranks_and_files_digest(tmp_path):
    pipe = ResearchPipeline(fetcher=_StubFetcher(), top=5)
    path = pipe.run(on=date(2026, 7, 1), out_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path.name == "2026-07-01-research-digest.md"
    assert "Calibration of Prediction Market Forecasts" in text
    assert "relevance" in text and "via [" in text  # explainable ranking
    # the homotopy paper is filtered out, and the count says so
    assert "Categorical Homotopy" not in text
    assert "1 relevant of 2 fetched" in text


def test_pipeline_handles_empty_feed(tmp_path):
    class _Empty:
        def recent(self, categories, max_results=60):
            return b"<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'></feed>"

    path = ResearchPipeline(fetcher=_Empty()).run(on=date(2026, 7, 1), out_dir=tmp_path)
    assert "no relevant papers" in path.read_text(encoding="utf-8")
