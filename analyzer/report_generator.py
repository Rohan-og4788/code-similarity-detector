"""Build CSV, JSON and HTML reports in memory. Source code is never included."""
from __future__ import annotations

import html
import json

import pandas as pd

from analyzer.similarity_engine import METHOD_LABELS, AnalysisResult
from utils.helpers import CATEGORY_COLORS, fmt_score, is_high_or_above

TOOL_NAME = "CodeSimilarity"
VERSION = "1.0"
DISCLAIMER = (
    "Similarity scores are review indicators, not proof of plagiarism. Common programming patterns, "
    "starter templates and standard algorithms can produce high scores for independent work. "
    "A human reviewer should examine flagged pairs before drawing any conclusion."
)
METHODOLOGY = [
    ("Token similarity", "Python tokens are extracted with the tokenize module. The score is the Dice coefficient over token 3-grams."),
    ("TF-IDF similarity", "Token unigrams and bigrams are weighted with TF-IDF; the score is the cosine similarity of the vectors."),
    ("AST similarity", "Code is parsed with ast.parse (never executed). Parent/child node pairs, statement-subtree hashes and identifiers form a feature set compared with weighted Jaccard."),
    ("Combined score", "Weighted average of the enabled methods. Weights are heuristic defaults and are re-normalized to 100% when a method is disabled."),
]
_CSV_COLUMNS = [
    "file_a", "file_b", "token_similarity", "tfidf_similarity", "ast_similarity",
    "combined_similarity", "classification", "analysis_status", "note",
]


def _csv_safe(value: str) -> str:
    """Prevent spreadsheet formula injection from hostile file names."""
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def methods_used(result: AnalysisResult) -> list[str]:
    return [METHOD_LABELS[m] for m in result.config.enabled_methods()]


def build_report_dict(result: AnalysisResult) -> dict:
    cfg = result.config
    t = cfg.thresholds
    return {
        "tool": TOOL_NAME,
        "version": VERSION,
        "analysis_id": result.analysis_id,
        "analysis_timestamp": result.created_at,
        "duration_seconds": result.duration_s,
        "disclaimer": DISCLAIMER,
        "configuration": {
            "methods_used": cfg.enabled_methods(),
            "identifier_normalization": cfg.normalize_identifiers,
            "configured_weights": {m: cfg.weights[m] for m in cfg.weights},
            "effective_weights": {m: round(w, 2) for m, w in cfg.effective_weights().items()},
            "thresholds": {"moderate_min": t.moderate, "high_min": t.high, "very_high_min": t.very_high},
        },
        "files": [
            {"name": f.name, "size_bytes": f.size, "lines": f.line_count, "status": f.status, "error": f.error}
            for f in result.files
        ],
        "pairs": [
            {
                "file_a": p.file_a, "file_b": p.file_b,
                "token_similarity": p.token, "tfidf_similarity": p.tfidf, "ast_similarity": p.ast,
                "combined_similarity": p.combined, "classification": p.classification,
                "status": p.status, "note": p.note or None,
            }
            for p in result.pairs
        ],
        "errors": [{"file": f.name, "error": f.error} for f in result.failed_files] + [{"warning": w} for w in result.warnings],
    }


def build_csv(result: AnalysisResult) -> str:
    rows = [
        {
            "file_a": _csv_safe(p.file_a), "file_b": _csv_safe(p.file_b),
            "token_similarity": p.token, "tfidf_similarity": p.tfidf, "ast_similarity": p.ast,
            "combined_similarity": p.combined, "classification": p.classification,
            "analysis_status": p.status, "note": _csv_safe(p.note),
        }
        for p in result.pairs
    ]
    return pd.DataFrame(rows, columns=_CSV_COLUMNS).to_csv(index=False)


def build_json(result: AnalysisResult) -> str:
    return json.dumps(build_report_dict(result), indent=2, ensure_ascii=False)


def build_html(result: AnalysisResult) -> str:
    """Self-contained, escaped HTML report (no external resources)."""
    esc = html.escape
    cfg = result.config
    scored = sorted(result.scored_pairs, key=lambda p: p.combined or 0, reverse=True)
    highest = scored[0].combined if scored else None
    flagged = sum(1 for p in scored if is_high_or_above(p.classification))

    def badge(label: str | None) -> str:
        if not label:
            return "—"
        return f'<span class="b" style="background:{CATEGORY_COLORS.get(label, "#9CA3AF")}">{esc(label)}</span>'

    pair_rows = "".join(
        f"<tr><td>{esc(p.file_a)}</td><td>{esc(p.file_b)}</td><td>{fmt_score(p.token)}</td>"
        f"<td>{fmt_score(p.tfidf)}</td><td>{fmt_score(p.ast)}</td><td><b>{fmt_score(p.combined)}</b></td>"
        f"<td>{badge(p.classification)}</td></tr>"
        for p in scored
    ) or '<tr><td colspan="7">No pairs were scored.</td></tr>'
    skipped = [p for p in result.pairs if p.combined is None]
    skipped_rows = "".join(
        f"<tr><td>{esc(p.file_a)}</td><td>{esc(p.file_b)}</td><td>{esc(p.status)}</td><td>{esc(p.note)}</td></tr>"
        for p in skipped
    )
    failed_rows = "".join(f"<tr><td>{esc(f.name)}</td><td>{esc(f.error or '')}</td></tr>" for f in result.failed_files)
    weights = ", ".join(f"{esc(METHOD_LABELS[m])}: {w:.1f}%" for m, w in cfg.effective_weights().items())
    t = cfg.thresholds
    ranges = "".join(f"<li>{esc(label)}: {lo:g}% to below {hi:g}%</li>" for label, lo, hi in t.ranges()[:-1])
    ranges += f"<li>{esc(t.ranges()[-1][0])}: {t.very_high:g}% to 100%</li>"
    method_items = "".join(f"<li><b>{esc(n)}.</b> {esc(d)}</li>" for n, d in METHODOLOGY)

    extra = ""
    if skipped:
        extra += f"<h2>Skipped or incomplete comparisons</h2><table><tr><th>File A</th><th>File B</th><th>Status</th><th>Reason</th></tr>{skipped_rows}</table>"
    if failed_rows:
        extra += f"<h2>Files that could not be analyzed</h2><table><tr><th>File</th><th>Reason</th></tr>{failed_rows}</table>"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>CodeSimilarity report</title>
<style>
body{{font-family:Segoe UI,Helvetica,Arial,sans-serif;background:#0B1020;color:#F9FAFB;margin:0;padding:32px;line-height:1.5}}
main{{max-width:1000px;margin:auto}} h1{{margin-bottom:0}} h2{{margin-top:32px;border-bottom:1px solid #1F2937;padding-bottom:6px}}
.muted{{color:#9CA3AF}} .cards{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}}
.card{{background:#111827;border:1px solid #1F2937;border-radius:12px;padding:14px 18px;min-width:170px}}
.card b{{display:block;font-size:1.6rem;color:#06B6D4}}
table{{width:100%;border-collapse:collapse;background:#111827;border-radius:12px;overflow:hidden;font-size:.92rem}}
th,td{{padding:8px 10px;text-align:left;border-bottom:1px solid #1F2937}} th{{background:#1F2937}}
.b{{color:#0B1020;padding:2px 10px;border-radius:999px;font-weight:600;font-size:.8rem;white-space:nowrap}}
.note{{background:#111827;border-left:4px solid #F59E0B;padding:12px 16px;border-radius:8px}}
</style></head><body><main>
<h1>CodeSimilarity report</h1>
<p class="muted">Python code similarity analysis · {esc(result.created_at)} (UTC) · analysis {esc(result.analysis_id)}</p>
<div class="cards">
<div class="card">Files analyzed<b>{len(result.analyzed_files)}</b></div>
<div class="card">Pairs compared<b>{len(result.pairs)}</b></div>
<div class="card">Highest similarity<b>{fmt_score(highest)}</b></div>
<div class="card">High / very high pairs<b>{flagged}</b></div>
</div>
<h2>Pairwise similarity</h2>
<table><tr><th>File A</th><th>File B</th><th>Token</th><th>TF-IDF</th><th>AST</th><th>Combined</th><th>Classification</th></tr>{pair_rows}</table>
{extra}
<h2>Configuration</h2>
<p>Methods used: {esc(", ".join(methods_used(result)))}. Identifier normalization: {"on" if cfg.normalize_identifiers else "off"}.</p>
<p>Effective weights: {weights}. These weights are heuristic defaults and can be adjusted.</p>
<ul>{ranges}</ul>
<h2>Methodology</h2><ul>{method_items}</ul>
<h2>Limitations and disclaimer</h2>
<p class="note">{esc(DISCLAIMER)}</p>
<p class="muted">Uploaded source code is not included in this report.</p>
</main></body></html>"""
