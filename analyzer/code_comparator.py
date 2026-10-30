"""Detailed two-file comparison: line diff, highlighting and explanations."""
from __future__ import annotations

import difflib
import html
import re
from collections import Counter
from dataclasses import dataclass, field

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

from analyzer.similarity_engine import FileAnalysis, PairResult
from analyzer.tokenizer import STRUCTURAL_TOKENS, TokenizationError, remove_comments

MAX_VIEW_LINES = 3000
MIN_FRAGMENT_LINES = 3


@dataclass
class DiffRow:
    left_no: int | None
    left_text: str
    right_no: int | None
    right_text: str
    kind: str          # match | changed | left_only | right_only | neutral


@dataclass
class DiffResult:
    rows: list[DiffRow]
    matched_lines: int
    lines_a: int
    lines_b: int
    line_similarity: float
    fragments: list[dict] = field(default_factory=list)
    truncated: bool = False


def _split_lines(text: str) -> list[str]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def line_keys(source: str) -> list[str]:
    """Comparison key per line: comment-free, trimmed, whitespace collapsed."""
    try:
        cleaned = remove_comments(source)
    except TokenizationError:
        cleaned = source
    return [re.sub(r"\s+", " ", ln.strip()) for ln in _split_lines(cleaned)]


def build_diff(text_a: str, text_b: str) -> DiffResult:
    """Line-level diff using difflib (comments/blank lines/indent ignored for matching)."""
    lines_a, lines_b = _split_lines(text_a), _split_lines(text_b)
    truncated = len(lines_a) > MAX_VIEW_LINES or len(lines_b) > MAX_VIEW_LINES
    lines_a, lines_b = lines_a[:MAX_VIEW_LINES], lines_b[:MAX_VIEW_LINES]
    keys_a = line_keys("\n".join(lines_a))
    keys_b = line_keys("\n".join(lines_b))
    # line_keys never changes the line count, but pad defensively
    keys_a += [""] * (len(lines_a) - len(keys_a))
    keys_b += [""] * (len(lines_b) - len(keys_b))

    matcher = difflib.SequenceMatcher(lambda s: s == "", keys_a, keys_b, autojunk=False)
    rows: list[DiffRow] = []
    matched = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        count = max(i2 - i1, j2 - j1)
        for k in range(count):
            ia = i1 + k if i1 + k < i2 else None
            ib = j1 + k if j1 + k < j2 else None
            ka = keys_a[ia] if ia is not None else ""
            kb = keys_b[ib] if ib is not None else ""
            if tag == "equal":
                kind = "match" if ka else "neutral"
                matched += 1 if ka else 0
            elif not ka and not kb:
                kind = "neutral"
            elif ia is None:
                kind = "right_only"
            elif ib is None:
                kind = "left_only"
            else:
                kind = "changed"
            rows.append(DiffRow(
                ia + 1 if ia is not None else None, lines_a[ia] if ia is not None else "",
                ib + 1 if ib is not None else None, lines_b[ib] if ib is not None else "",
                kind,
            ))

    fragments = []
    for a0, b0, size in matcher.get_matching_blocks():
        real = [keys_a[a0 + k] for k in range(size) if keys_a[a0 + k]]
        if len(real) >= MIN_FRAGMENT_LINES:
            fragments.append({
                "start_a": a0 + 1, "start_b": b0 + 1, "line_count": len(real),
                "code": "\n".join(lines_a[a0 : a0 + size]),
            })
    total_a = sum(1 for k in keys_a if k)
    total_b = sum(1 for k in keys_b if k)
    similarity = 100.0 * 2 * matched / (total_a + total_b) if (total_a + total_b) else 0.0
    return DiffResult(rows, matched, total_a, total_b, round(similarity, 2), fragments, truncated)


# --------------------------------------------------------------------------- #
# Safe HTML rendering
# --------------------------------------------------------------------------- #
def highlight_lines(source: str) -> list[str]:
    """Pygments-highlighted HTML, one string per source line.

    Pygments escapes ``< > & "`` in all token text, so uploaded code cannot
    inject markup. If highlighting fails we fall back to ``html.escape``.
    """
    lines = _split_lines(source)
    try:
        formatter = HtmlFormatter(nowrap=True, noclasses=True, style="monokai")
        rendered = highlight(source, PythonLexer(), formatter).split("\n")
    except Exception:  # pragma: no cover - defensive
        rendered = []
    return [rendered[i] if i < len(rendered) else html.escape(lines[i]) for i in range(len(lines))]


def render_diff_html(rows: list[DiffRow], left_html: list[str], right_html: list[str]) -> str:
    """Side-by-side table. Returned as one line so Markdown cannot reinterpret it."""
    def cell(number: int | None, lines: list[str]) -> str:
        if number is None:
            return '<td class="no"></td><td class="code">&nbsp;</td>'
        code = lines[number - 1] if number - 1 < len(lines) else ""
        return f'<td class="no">{number}</td><td class="code">{code or "&nbsp;"}</td>'

    body = "".join(
        f'<tr class="{html.escape(r.kind)}">{cell(r.left_no, left_html)}{cell(r.right_no, right_html)}</tr>'
        for r in rows
    )
    return f'<div class="cs-diff-wrap"><table class="cs-diff"><tbody>{body}</tbody></table></div>'


# --------------------------------------------------------------------------- #
# Explanations
# --------------------------------------------------------------------------- #
LIMITATIONS = [
    "Scores are review indicators, not proof of plagiarism or copying.",
    "Short programs, starter templates and standard algorithms naturally look alike.",
    "AST and token scores measure structure, so similar structure does not mean identical meaning.",
    "Line matching ignores comments, blank lines and indentation width, but not renamed variables.",
    "Identifier normalization is a heuristic: it numbers names by first appearance and keeps imports, built-ins and attributes.",
]


def _similar_names(names_a: list[str], names_b: list[str], kind: str) -> list[dict]:
    found = []
    for x in sorted(set(names_a)):
        for y in sorted(set(names_b)):
            ratio = difflib.SequenceMatcher(None, x, y).ratio()
            if x == y or ratio >= 0.8:
                found.append({"kind": kind, "name_a": x, "name_b": y, "similarity": round(ratio * 100)})
    return found


def explain_pair(a: FileAnalysis, b: FileAnalysis, pair: PairResult, diff: DiffResult) -> dict:
    """Plain-language comparison details. Never asserts that code was copied."""
    counts = Counter(t for t in a.tokens if t not in STRUCTURAL_TOKENS) & Counter(
        t for t in b.tokens if t not in STRUCTURAL_TOKENS
    )
    meaningful = [(t, c) for t, c in counts.most_common() if re.search(r"\w", t)]
    vocab_a = {t for t in a.tokens if t not in STRUCTURAL_TOKENS}
    vocab_b = {t for t in b.tokens if t not in STRUCTURAL_TOKENS}
    union = vocab_a | vocab_b
    shared_vocab = round(100.0 * len(vocab_a & vocab_b) / len(union), 1) if union else 0.0

    structure = []
    differences: list[str] = []
    if a.ast_profile and b.ast_profile:
        for label, count_a in a.ast_profile.summary.items():
            count_b = b.ast_profile.summary[label]
            structure.append({"Construct": label, a.name: count_a, b.name: count_b})
            if count_a != count_b:
                differences.append(f"{label}: {count_a} in {a.name} vs {count_b} in {b.name}.")

    names = []
    if a.ast_profile and b.ast_profile:
        names += _similar_names(a.ast_profile.function_names, b.ast_profile.function_names, "function")
        names += _similar_names(a.ast_profile.class_names, b.ast_profile.class_names, "class")

    only_a = sum(1 for r in diff.rows if r.kind in ("left_only", "changed") and r.left_no)
    only_b = sum(1 for r in diff.rows if r.kind in ("right_only", "changed") and r.right_no)
    differences.insert(0, f"{only_a} line(s) in {a.name} and {only_b} line(s) in {b.name} have no exact counterpart.")

    notes: list[str] = []
    if pair.ast is not None and pair.ast >= 50 and diff.line_similarity < 30:
        notes.append(
            "Structural, not textual: the code is built in a similar way, but few lines are identical. "
            "This often happens when names, formatting or comments differ, or when both follow a common pattern."
        )
    elif diff.line_similarity >= 60:
        notes.append("Many lines are textually identical after ignoring comments, blank lines and indentation width.")
    if pair.ast is not None and pair.ast < 30 and diff.line_similarity < 30:
        notes.append("Both the structure and the text differ considerably.")
    notes.append("Treat this as a prompt for human review, not as a verdict.")

    return {
        "common_tokens": meaningful[:15],
        "shared_vocabulary_pct": shared_vocab,
        "structure": structure,
        "similar_names": names,
        "fragments": diff.fragments,
        "differences": differences,
        "notes": notes,
        "limitations": LIMITATIONS,
    }
