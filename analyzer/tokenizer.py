"""Python tokenization and comment-safe preprocessing (Methods A and B).

Everything here uses the standard ``tokenize`` module, which only *reads*
the source text. Nothing is executed.
"""
from __future__ import annotations

import builtins
import io
import keyword
import tokenize

MAX_TOKENS = 300_000

_BUILTINS = frozenset(dir(builtins))
_KEYWORDS = frozenset(keyword.kwlist) | frozenset(keyword.softkwlist)
_SKIPPED = {tokenize.COMMENT, tokenize.NL, tokenize.ENDMARKER}
STRUCTURAL_TOKENS = frozenset({"<NEWLINE>", "<INDENT>", "<DEDENT>"})


class TokenizationError(Exception):
    """Raised when a file cannot be tokenized. The message is safe to show."""


def _generate(source: str) -> list[tokenize.TokenInfo]:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError as exc:
        raise TokenizationError(f"Tokenization error: {exc.args[0]}") from None
    except SyntaxError as exc:  # includes IndentationError
        raise TokenizationError(f"{type(exc).__name__} on line {exc.lineno}: {exc.msg}") from None
    if len(tokens) > MAX_TOKENS:
        raise TokenizationError(f"File has more than {MAX_TOKENS:,} tokens; too large to compare safely.")
    return tokens


def remove_comments(source: str) -> str:
    """Remove ``#`` comments using real tokenization.

    A ``#`` inside a string literal is not a COMMENT token, so strings are
    never damaged. The number of lines is unchanged.
    """
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = source.split("\n")
    for tok in _generate(source):
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            lines[row - 1] = lines[row - 1][:col]
    return "\n".join(lines)


def normalize_source(source: str) -> str:
    """Method A: comment-free source with trailing whitespace and blank lines removed.

    Leading indentation is kept (it is meaningful in Python). Lines that are
    part of a multi-line string are left untouched, so string contents are
    never altered.
    """
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = source.split("\n")
    protected: set[int] = set()
    for tok in _generate(source):
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            lines[row - 1] = lines[row - 1][:col]
        elif tok.end[0] > tok.start[0]:  # token spans lines (multi-line string)
            protected.update(range(tok.start[0], tok.end[0]))
    kept: list[str] = []
    for number, line in enumerate(lines, start=1):
        if number in protected:
            kept.append(line)
            continue
        line = line.rstrip()
        if line:
            kept.append(line)
    return "\n".join(kept) + "\n" if kept else ""


def _imported_names(tokens: list[tokenize.TokenInfo]) -> set[str]:
    """Names that appear on import lines (module names and aliases)."""
    names: set[str] = set()
    at_line_start = True
    in_import = False
    for tok in tokens:
        if tok.type in _SKIPPED:
            continue
        if tok.type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            at_line_start = True
            in_import = False
            continue
        if at_line_start and tok.type == tokenize.NAME and tok.string in ("import", "from"):
            in_import = True
        elif in_import and tok.type == tokenize.NAME and tok.string not in ("import", "from", "as"):
            names.add(tok.string)
        at_line_start = False
    return names


def _should_normalize(name: str, previous: tokenize.TokenInfo | None, preserved: set[str]) -> bool:
    if name in _KEYWORDS or name in _BUILTINS or name in preserved:
        return False
    if name.startswith("__") and name.endswith("__"):
        return False
    if previous is not None and previous.type == tokenize.OP and previous.string == ".":
        return False  # attribute name, e.g. the "append" in items.append(x)
    return True


def extract_tokens(source: str, normalize_identifiers: bool = False) -> list[str]:
    """Method B: meaningful token strings.

    Comments and non-logical newlines are dropped. NEWLINE/INDENT/DEDENT are
    kept as ``<NEWLINE>``/``<INDENT>``/``<DEDENT>`` so structure is preserved
    without depending on how many spaces were used.

    With ``normalize_identifiers`` user-defined names become ``ID_1``, ``ID_2``
    ... numbered by first appearance. Keywords, built-ins, attribute names,
    dunder names, imported names, strings and numbers are never replaced.
    """
    raw = _generate(source.replace("\r\n", "\n").replace("\r", "\n"))
    preserved = _imported_names(raw) if normalize_identifiers else set()
    mapping: dict[str, str] = {}
    out: list[str] = []
    previous: tokenize.TokenInfo | None = None
    for tok in raw:
        kind = tok.type
        if kind in _SKIPPED:
            continue
        if kind == tokenize.NEWLINE:
            out.append("<NEWLINE>")
        elif kind == tokenize.INDENT:
            out.append("<INDENT>")
        elif kind == tokenize.DEDENT:
            out.append("<DEDENT>")
        elif kind == tokenize.NAME:
            name = tok.string
            if normalize_identifiers and _should_normalize(name, previous, preserved):
                name = mapping.setdefault(name, f"ID_{len(mapping) + 1}")
            out.append(name)
        elif tok.string.strip():
            out.append(tok.string)
        else:
            continue
        previous = tok
    return out
