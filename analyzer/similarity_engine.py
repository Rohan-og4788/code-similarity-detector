"""Similarity algorithms, configuration and the pairwise analysis pipeline.

Three measurements, each on a 0-100 scale:

* Token similarity  - Dice coefficient over token 3-grams (shingles).
* TF-IDF similarity - cosine similarity of TF-IDF vectors of token 1/2-grams.
* AST similarity    - weighted Jaccard over structural AST features.

The combined score is a weighted average of the *enabled* methods, with the
weights re-normalized so they always add up to 100%.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from typing import Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from analyzer.ast_analyzer import AstAnalysisError, AstProfile, build_profile
from analyzer.file_processor import SourceFile
from analyzer.tokenizer import TokenizationError, extract_tokens
from utils.helpers import Thresholds, classify_score, utc_now_iso

logger = logging.getLogger(__name__)

METHODS = ("token", "tfidf", "ast")
METHOD_LABELS = {"token": "Token similarity", "tfidf": "TF-IDF similarity", "ast": "AST similarity"}
DEFAULT_WEIGHTS = {"token": 30.0, "tfidf": 20.0, "ast": 50.0}
NGRAM_SIZE = 3


@dataclass
class AnalysisConfig:
    """User-adjustable analysis settings."""

    use_token: bool = True
    use_tfidf: bool = True
    use_ast: bool = True
    normalize_identifiers: bool = False
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    thresholds: Thresholds = field(default_factory=Thresholds)

    def enabled_methods(self) -> list[str]:
        flags = {"token": self.use_token, "tfidf": self.use_tfidf, "ast": self.use_ast}
        return [m for m in METHODS if flags[m]]

    def validate(self) -> list[str]:
        errors: list[str] = []
        enabled = self.enabled_methods()
        if not enabled:
            errors.append("Enable at least one similarity method.")
        if any(self.weights.get(m, 0) < 0 for m in METHODS):
            errors.append("Weights cannot be negative.")
        elif enabled and sum(self.weights.get(m, 0) for m in enabled) <= 0:
            errors.append("The weights of the enabled methods must add up to more than 0.")
        errors.extend(self.thresholds.validate())
        return errors

    def effective_weights(self) -> dict[str, float]:
        """Weights of enabled methods, re-normalized to total exactly 100."""
        errors = [e for e in self.validate() if "weight" in e.lower() or "method" in e.lower()]
        if errors:
            raise ValueError(errors[0])
        enabled = self.enabled_methods()
        total = sum(self.weights[m] for m in enabled)
        return {m: self.weights[m] / total * 100.0 for m in enabled}


# --------------------------------------------------------------------------- #
# Algorithms
# --------------------------------------------------------------------------- #
def token_ngrams(tokens: Sequence[str], n: int = NGRAM_SIZE) -> Counter:
    """Multiset of token n-grams (a very short file uses one shorter gram)."""
    if not tokens:
        return Counter()
    if len(tokens) < n:
        return Counter([tuple(tokens)])
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def token_similarity(grams_a: Counter, grams_b: Counter) -> float:
    """Dice coefficient of two n-gram multisets, 0-100."""
    total = sum(grams_a.values()) + sum(grams_b.values())
    if total == 0:
        return 0.0
    shared = sum((grams_a & grams_b).values())
    return 100.0 * 2 * shared / total


def _tfidf_analyzer(tokens: list[str]) -> list[str]:
    """Unigrams + bigrams so operators and short names are kept."""
    return tokens + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


def tfidf_similarity_matrix(token_lists: list[list[str]]) -> np.ndarray:
    """Cosine similarity (0-100) between TF-IDF vectors of all documents.

    A custom analyzer is used instead of the default word tokenizer, which
    would drop operators and one-letter identifiers. Raises ValueError if the
    corpus has no usable tokens.
    """
    vectorizer = TfidfVectorizer(analyzer=_tfidf_analyzer, sublinear_tf=True)
    matrix = vectorizer.fit_transform(token_lists)
    return np.clip(cosine_similarity(matrix) * 100.0, 0.0, 100.0)


def weighted_jaccard(a: Counter, b: Counter) -> float:
    """sum(min) / sum(max) over two feature multisets (1.0 = identical)."""
    keys = a.keys() | b.keys()
    denominator = sum(max(a[k], b[k]) for k in keys)
    if denominator == 0:
        return 1.0
    return sum(min(a[k], b[k]) for k in keys) / denominator


def ast_similarity(a: AstProfile, b: AstProfile) -> float:
    """Structural similarity of two AST profiles, 0-100."""
    return 100.0 * weighted_jaccard(a.features, b.features)


def combine_scores(components: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """Weighted combination. Returns None if any enabled component is missing."""
    total = 0.0
    for method, weight in weights.items():
        score = components.get(method)
        if score is None:
            return None
        total += score * weight / 100.0
    return round(total, 2)


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
@dataclass
class FileAnalysis:
    """Per-file analysis state. ``text`` stays in memory for the session only."""

    name: str
    size: int
    line_count: int
    text: str
    status: str = "ok"                      # "ok" or "failed"
    error: str | None = None
    tokens: list[str] = field(default_factory=list)
    grams: Counter = field(default_factory=Counter)
    ast_profile: AstProfile | None = None


@dataclass
class PairResult:
    file_a: str
    file_b: str
    token: float | None = None
    tfidf: float | None = None
    ast: float | None = None
    combined: float | None = None
    classification: str | None = None
    status: str = "ok"                      # "ok", "skipped" or "incomplete"
    note: str = ""

    def component(self, method: str) -> float | None:
        return getattr(self, method)


@dataclass
class AnalysisResult:
    analysis_id: str
    created_at: str
    duration_s: float
    config: AnalysisConfig
    files: list[FileAnalysis]
    pairs: list[PairResult]
    warnings: list[str] = field(default_factory=list)

    @property
    def analyzed_files(self) -> list[FileAnalysis]:
        return [f for f in self.files if f.status == "ok"]

    @property
    def failed_files(self) -> list[FileAnalysis]:
        return [f for f in self.files if f.status != "ok"]

    @property
    def scored_pairs(self) -> list[PairResult]:
        return [p for p in self.pairs if p.combined is not None]

    def file(self, name: str) -> FileAnalysis | None:
        return next((f for f in self.files if f.name == name), None)

    def pair(self, name_a: str, name_b: str) -> PairResult | None:
        for p in self.pairs:
            if {p.file_a, p.file_b} == {name_a, name_b}:
                return p
        return None


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def analyze_file(source: SourceFile, config: AnalysisConfig) -> FileAnalysis:
    """Extract tokens and AST features. Failures are recorded, never raised."""
    analysis = FileAnalysis(source.name, source.size, source.line_count, source.text)
    try:
        analysis.ast_profile = build_profile(source.text, config.normalize_identifiers)
        analysis.tokens = extract_tokens(source.text, config.normalize_identifiers)
        if not analysis.tokens:
            raise TokenizationError("File contains no code tokens.")
        analysis.grams = token_ngrams(analysis.tokens)
    except (AstAnalysisError, TokenizationError) as exc:
        analysis.status, analysis.error = "failed", str(exc)
    except Exception as exc:  # last resort; never leak tracebacks or source text
        logger.warning("Unexpected %s while analyzing %s", type(exc).__name__, source.name)
        analysis.status = "failed"
        analysis.error = "Unexpected internal error while analyzing this file."
    return analysis


def run_analysis(files: Sequence[SourceFile], config: AnalysisConfig | None = None) -> AnalysisResult:
    """Compare every unique pair of files. Raises ValueError for bad settings."""
    config = config or AnalysisConfig()
    errors = config.validate()
    if errors:
        raise ValueError(" ".join(errors))
    if len(files) < 2:
        raise ValueError("At least two files are required.")

    started = time.perf_counter()
    weights = config.effective_weights()
    analyses = [analyze_file(f, config) for f in files]
    valid = [a for a in analyses if a.status == "ok"]
    notes: list[str] = []

    tfidf_matrix: np.ndarray | None = None
    tfidf_index = {a.name: i for i, a in enumerate(valid)}
    if config.use_tfidf and len(valid) >= 2:
        try:
            tfidf_matrix = tfidf_similarity_matrix([a.tokens for a in valid])
        except ValueError:
            notes.append("TF-IDF could not run (no usable tokens); affected pairs are marked incomplete.")

    pairs: list[PairResult] = []
    for a, b in combinations(analyses, 2):
        pair = PairResult(a.name, b.name)
        bad = [x for x in (a, b) if x.status != "ok"]
        if bad:
            pair.status = "skipped"
            pair.note = "; ".join(f"{x.name}: {x.error}" for x in bad)
            pairs.append(pair)
            continue

        components: dict[str, float | None] = {}
        if config.use_token:
            components["token"] = round(token_similarity(a.grams, b.grams), 2)
        if config.use_tfidf:
            if tfidf_matrix is not None:
                components["tfidf"] = round(float(tfidf_matrix[tfidf_index[a.name], tfidf_index[b.name]]), 2)
            else:
                components["tfidf"] = None
        if config.use_ast and a.ast_profile and b.ast_profile:
            components["ast"] = round(ast_similarity(a.ast_profile, b.ast_profile), 2)
        pair.token = components.get("token")
        pair.tfidf = components.get("tfidf")
        pair.ast = components.get("ast")

        pair.combined = combine_scores(components, weights)
        if pair.combined is None:
            pair.status = "incomplete"
            missing = [METHOD_LABELS[m] for m, s in components.items() if s is None]
            pair.note = "Combined score not computed; missing: " + ", ".join(missing)
        else:
            pair.classification = classify_score(pair.combined, config.thresholds)
        pairs.append(pair)

    return AnalysisResult(
        analysis_id=uuid.uuid4().hex[:8],
        created_at=utc_now_iso(),
        duration_s=round(time.perf_counter() - started, 3),
        config=config,
        files=analyses,
        pairs=pairs,
        warnings=notes,
    )


def compare_sources(text_a: str, text_b: str, config: AnalysisConfig | None = None) -> PairResult:
    """Convenience helper: compare two source strings (used by tests)."""
    files = [SourceFile.from_text("a.py", text_a, 0), SourceFile.from_text("b.py", text_b, 1)]
    return run_analysis(files, config).pairs[0]


def similarity_matrix(result: AnalysisResult) -> tuple[list[str], np.ndarray]:
    """Symmetric matrix of combined scores for analyzed files (diagonal = 100).

    Cells without a complete score are NaN, never 0.
    """
    names = [f.name for f in result.analyzed_files]
    matrix = np.full((len(names), len(names)), np.nan)
    for i in range(len(names)):
        matrix[i, i] = 100.0
    position = {n: i for i, n in enumerate(names)}
    for p in result.pairs:
        if p.combined is None or p.file_a not in position or p.file_b not in position:
            continue
        i, j = position[p.file_a], position[p.file_b]
        matrix[i, j] = matrix[j, i] = p.combined
    return names, matrix
