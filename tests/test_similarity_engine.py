"""Tests for the similarity algorithms, scoring and configuration."""
import pytest

from analyzer.file_processor import SourceFile
from analyzer.report_generator import build_csv, build_html, build_json
from analyzer.similarity_engine import (
    AnalysisConfig, combine_scores, compare_sources, run_analysis, similarity_matrix,
)
from utils.helpers import Thresholds, classify_score

BASE = '''
def average(numbers):
    total = 0
    for value in numbers:
        total += value
    return total / len(numbers)

print(average([1, 2, 3]))
'''

REFORMATTED = '''
# Computes the mean.


def average(numbers):
  # accumulate
  total = 0

  for value in numbers:
      total += value   # add it

  return total / len(numbers)


print(average([1, 2, 3]))   # demo
'''

RENAMED = BASE.replace("average", "mean_of").replace("numbers", "data").replace("total", "acc").replace("value", "x")

DIFFERENT = '''
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

class Stack:
    def __init__(self):
        self.items = []
    def push(self, item):
        self.items.append(item)
'''


# Test 1
def test_identical_code_scores_100():
    p = compare_sources(BASE, BASE)
    assert (p.token, p.tfidf, p.ast, p.combined) == (100.0, 100.0, 100.0, 100.0)
    assert p.classification == "Very High Similarity"


# Test 2
def test_formatting_and_comment_differences_do_not_matter():
    p = compare_sources(BASE, REFORMATTED)
    assert p.combined >= 95
    assert p.token == 100.0 and p.ast == 100.0


# Test 3
def test_variable_renaming_needs_normalization():
    plain = compare_sources(BASE, RENAMED)
    normalized = compare_sources(BASE, RENAMED, AnalysisConfig(normalize_identifiers=True))
    assert normalized.token == 100.0 and normalized.ast == 100.0
    assert normalized.combined > plain.combined


# Test 4
def test_different_programs_score_low():
    p = compare_sources(BASE, DIFFERENT)
    assert p.combined < 40
    assert p.classification in ("Low Similarity", "Moderate Similarity")


# Test 5
def test_invalid_syntax_is_reported_without_crashing():
    files = [SourceFile.from_text("good.py", BASE, 0), SourceFile.from_text("bad.py", "def x(:\n", 1)]
    result = run_analysis(files)
    assert [f.name for f in result.failed_files] == ["bad.py"]
    pair = result.pairs[0]
    assert pair.status == "skipped" and pair.combined is None and "bad.py" in pair.note


# Test 7
def test_five_files_give_ten_pairs_and_symmetric_matrix():
    sources = [BASE, REFORMATTED, RENAMED, DIFFERENT, "x = 1\nprint(x)\n"]
    files = [SourceFile.from_text(f"s{i}.py", s, i) for i, s in enumerate(sources)]
    result = run_analysis(files)
    assert len(result.pairs) == 10
    assert len({frozenset((p.file_a, p.file_b)) for p in result.pairs}) == 10
    names, matrix = similarity_matrix(result)
    assert len(names) == 5
    assert (matrix == matrix.T).all()
    assert all(matrix[i, i] == 100 for i in range(5))


def test_scores_are_not_random_and_are_repeatable():
    assert compare_sources(BASE, DIFFERENT) == compare_sources(BASE, DIFFERENT)


def test_combined_uses_default_weights():
    assert combine_scores({"token": 100, "tfidf": 0, "ast": 50}, {"token": 30, "tfidf": 20, "ast": 50}) == 55.0
    cfg = AnalysisConfig()
    assert cfg.effective_weights() == {"token": 30.0, "tfidf": 20.0, "ast": 50.0}


def test_missing_component_never_becomes_zero():
    assert combine_scores({"token": 80, "tfidf": None, "ast": 80}, {"token": 30, "tfidf": 20, "ast": 50}) is None


def test_disabled_methods_renormalize_weights():
    cfg = AnalysisConfig(use_tfidf=False)
    weights = cfg.effective_weights()
    assert set(weights) == {"token", "ast"}
    assert sum(weights.values()) == pytest.approx(100.0)
    assert weights["token"] == pytest.approx(37.5)
    p = compare_sources(BASE, DIFFERENT, cfg)
    assert p.tfidf is None and p.combined is not None


def test_all_methods_disabled_is_blocked():
    cfg = AnalysisConfig(use_token=False, use_tfidf=False, use_ast=False)
    assert cfg.validate()
    with pytest.raises(ValueError):
        compare_sources(BASE, BASE, cfg)


def test_thresholds_have_no_gaps_or_overlaps():
    t = Thresholds()
    assert [classify_score(s, t) for s in (0, 24.99, 25, 49.99, 50, 74.99, 75, 100)] == [
        "Low Similarity", "Low Similarity", "Moderate Similarity", "Moderate Similarity",
        "High Similarity", "High Similarity", "Very High Similarity", "Very High Similarity",
    ]
    assert Thresholds(moderate=60, high=50, very_high=75).validate()
    assert classify_score(55, Thresholds(moderate=10, high=20, very_high=30)) == "Very High Similarity"


def test_reports_contain_expected_fields_and_no_source():
    files = [SourceFile.from_text("=evil.py", BASE + "\nSECRET_MARKER = 1\n", 0), SourceFile.from_text("b.py", DIFFERENT, 1)]
    result = run_analysis(files)
    csv_text, json_text, html_text = build_csv(result), build_json(result), build_html(result)
    assert "combined_similarity" in csv_text and "'=evil.py" in csv_text
    assert '"thresholds"' in json_text and '"effective_weights"' in json_text and '"analysis_timestamp"' in json_text
    assert "<table>" in html_text and "Limitations" in html_text
    for text in (csv_text, json_text, html_text):
        assert "SECRET_MARKER" not in text
