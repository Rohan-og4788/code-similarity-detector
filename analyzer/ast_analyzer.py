"""AST-based structural analysis (Method C).

``ast.parse`` only builds a syntax tree from text; it never runs the code.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import warnings
from collections import Counter
from dataclasses import dataclass, field

MAX_NODES = 300_000
_BUILTINS = frozenset(dir(builtins))

# Human-readable structure categories -> AST node classes.
_TRY_NODES = (ast.Try,) + ((ast.TryStar,) if hasattr(ast, "TryStar") else ())
STRUCTURE_CATEGORIES: dict[str, tuple[type, ...]] = {
    "Function definitions": (ast.FunctionDef, ast.AsyncFunctionDef),
    "Class definitions": (ast.ClassDef,),
    "Conditionals (if)": (ast.If, ast.IfExp),
    "Loops (for/while)": (ast.For, ast.AsyncFor, ast.While),
    "Function calls": (ast.Call,),
    "Return statements": (ast.Return,),
    "Assignments": (ast.Assign, ast.AugAssign, ast.AnnAssign),
    "Binary operations": (ast.BinOp,),
    "Boolean operations": (ast.BoolOp,),
    "Comparisons": (ast.Compare,),
    "Comprehensions": (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp),
    "Exception handling (try)": _TRY_NODES,
    "Imports": (ast.Import, ast.ImportFrom),
    "Lambdas": (ast.Lambda,),
}


class AstAnalysisError(Exception):
    """Raised when a file cannot be analyzed. The message is safe to show."""


@dataclass
class AstProfile:
    """Structural description of one source file."""

    features: Counter
    summary: dict[str, int]
    node_count: int
    fingerprint: str
    function_names: list[str] = field(default_factory=list)
    class_names: list[str] = field(default_factory=list)


def parse_source(source: str) -> ast.Module:
    """Parse text into a syntax tree, translating failures into AstAnalysisError."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # e.g. invalid escape sequence warnings
            return ast.parse(source, filename="<uploaded>", mode="exec")
    except SyntaxError as exc:
        where = f" on line {exc.lineno}" if exc.lineno else ""
        raise AstAnalysisError(f"{type(exc).__name__}{where}: {exc.msg}") from None
    except (RecursionError, MemoryError):
        raise AstAnalysisError("File is too deeply nested or too large to parse safely.") from None
    except ValueError:
        raise AstAnalysisError("File contains characters Python cannot parse.") from None


def _is_normalizable(name: str) -> bool:
    return name not in _BUILTINS and not (name.startswith("__") and name.endswith("__"))


def collect_user_names(tree: ast.AST) -> set[str]:
    """Names the author defined (functions, classes, parameters, variables)."""
    user: set[str] = set()
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            user.add(node.name)
        elif isinstance(node, ast.arg):
            user.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            user.add(node.id)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            user.update(node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            user.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            user.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                imported.add((alias.asname or alias.name).split(".")[0])
    return {n for n in user if _is_normalizable(n)} - imported


def _detail(node: ast.AST, user_names: set[str], normalize: bool) -> str | None:
    def mapped(identifier: str) -> str:
        return "ID" if normalize and identifier in user_names else identifier

    if isinstance(node, ast.Name):
        return mapped(node.id)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return mapped(node.name)
    if isinstance(node, ast.arg):
        return mapped(node.arg)
    if isinstance(node, ast.Constant):
        return type(node.value).__name__      # the *kind* of constant, not its value
    if isinstance(node, ast.Attribute):
        return node.attr                       # attribute names are never normalized
    if isinstance(node, ast.alias):
        return node.name
    if isinstance(node, ast.keyword):
        return node.arg or "**"
    if isinstance(node, ast.ExceptHandler):
        return mapped(node.name) if node.name else ""
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        return ",".join(mapped(n) for n in node.names)
    return None


_NAMED_NODES = (ast.Name, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.arg, ast.Attribute)


def build_profile(source: str, normalize_identifiers: bool = False) -> AstProfile:
    """Parse ``source`` and build its structural profile.

    Features (all counted in a multiset):
      * ``E:Parent>Child``  - parent/child node-type pairs
      * ``S:<hash>``        - a hash of every whole statement subtree
      * ``N:<label>``       - identifiers (``ID`` when normalized)
    """
    tree = parse_source(source)
    if not tree.body:
        raise AstAnalysisError("File contains no code (only comments or whitespace).")

    node_count = sum(1 for _ in ast.walk(tree))
    if node_count > MAX_NODES:
        raise AstAnalysisError(f"File has more than {MAX_NODES:,} syntax nodes; too large to compare safely.")

    user_names = collect_user_names(tree) if normalize_identifiers else set()
    features: Counter = Counter()

    def visit(node: ast.AST) -> str:
        detail = _detail(node, user_names, normalize_identifiers)
        label = type(node).__name__ if detail is None else f"{type(node).__name__}:{detail}"
        child_sigs: list[str] = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr_context):
                continue
            features[f"E:{type(node).__name__}>{type(child).__name__}"] += 1
            child_sigs.append(visit(child))
        digest = hashlib.blake2b("|".join([label, *child_sigs]).encode("utf-8"), digest_size=8).hexdigest()
        if isinstance(node, ast.stmt):
            features[f"S:{digest}"] += 1
        if isinstance(node, _NAMED_NODES) and detail is not None:
            features[f"N:{label}"] += 1
        return digest

    try:
        fingerprint = visit(tree)
    except RecursionError:
        raise AstAnalysisError("File is too deeply nested to analyze safely.") from None

    summary = {
        label: sum(1 for n in ast.walk(tree) if isinstance(n, classes))
        for label, classes in STRUCTURE_CATEGORIES.items()
    }
    functions = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes_ = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    return AstProfile(features, summary, node_count, fingerprint, functions, classes_)
