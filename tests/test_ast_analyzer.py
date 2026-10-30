"""Tests for tokenization, identifier normalization and AST profiling."""
import pytest

from analyzer.ast_analyzer import AstAnalysisError, build_profile
from analyzer.tokenizer import extract_tokens, normalize_source, remove_comments


# Test 8: identifier normalization must not touch keywords, strings, attributes, built-ins
def test_identifier_normalization_preserves_protected_names():
    src = (
        "import math\n"
        "def total(items):\n"
        "    result = []\n"
        "    for item in items:\n"
        "        result.append(len(item))\n"
        "    print('result', math.sqrt(4))\n"
        "    return result\n"
    )
    tokens = extract_tokens(src, normalize_identifiers=True)
    for kept in ("def", "for", "in", "return", "import", "math", "append", "len", "print", "sqrt", "'result'"):
        assert kept in tokens, kept
    for replaced in ("total", "items", "result", "item"):
        assert replaced not in tokens, replaced
    assert any(t.startswith("ID_") for t in tokens)


def test_normalization_numbers_names_consistently():
    tokens = extract_tokens("a = b\nb = a\n", normalize_identifiers=True)
    assert tokens[:3] == ["ID_1", "=", "ID_2"]
    assert tokens[4:7] == ["ID_2", "=", "ID_1"]


def test_without_normalization_names_are_kept():
    assert "total" in extract_tokens("total = 1\n")


def test_dunder_names_are_not_normalized():
    tokens = extract_tokens("class A:\n    def __init__(self):\n        self.x = 1\n", normalize_identifiers=True)
    assert "__init__" in tokens and "x" in tokens  # attribute x kept


def test_ast_normalization_keeps_attributes_and_builtins():
    profile = build_profile("def f(v):\n    return len(v.items)\n", normalize_identifiers=True)
    assert "N:Name:len" in profile.features
    assert "N:Attribute:items" in profile.features
    assert "N:FunctionDef:ID" in profile.features


def test_remove_comments_keeps_hash_inside_strings():
    src = 'url = "http://x.com/#frag"  # real comment\n'
    cleaned = remove_comments(src)
    assert "#frag" in cleaned and "real comment" not in cleaned


def test_normalize_source_preserves_multiline_strings():
    src = 'text = """line one\n\n   indented   \nend"""  # note\n\n\nx = 1   \n'
    out = normalize_source(src)
    assert '"""line one\n\n   indented   \nend"""' in out
    assert "note" not in out
    assert out.endswith("x = 1\n")


def test_structure_summary_counts_constructs():
    src = (
        "class A:\n    pass\n"
        "def f(x):\n"
        "    try:\n"
        "        y = [i for i in range(x) if i % 2 == 0 and x]\n"
        "    except ValueError:\n"
        "        return None\n"
        "    while x:\n        x -= 1\n"
        "    return y\n"
    )
    s = build_profile(src).summary
    assert s["Function definitions"] == 1 and s["Class definitions"] == 1
    assert s["Exception handling (try)"] == 1 and s["Comprehensions"] == 1
    assert s["Loops (for/while)"] == 1 and s["Boolean operations"] == 1
    assert s["Return statements"] == 2


# Test 5: invalid syntax
def test_syntax_error_is_reported_not_raised_as_crash():
    with pytest.raises(AstAnalysisError) as info:
        build_profile("def broken(:\n    pass\n")
    assert "line 1" in str(info.value)


def test_comment_only_file_is_rejected():
    with pytest.raises(AstAnalysisError):
        build_profile("# nothing here\n")
