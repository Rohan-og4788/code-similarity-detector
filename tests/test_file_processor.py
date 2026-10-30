"""Tests for upload validation and the security guarantees."""
import ast
import pathlib

from analyzer.code_comparator import highlight_lines, render_diff_html, build_diff
from analyzer.file_processor import process_uploads
from analyzer.similarity_engine import run_analysis
from utils.validators import UploadLimits

LIMITS = UploadLimits()


def reasons(result):
    return {r.name: r.reason for r in result.rejected}


# Test 6: empty files
def test_empty_and_whitespace_files_rejected():
    result = process_uploads([("a.py", b""), ("b.py", b"  \n\n"), ("c.py", b"x = 1\n")], LIMITS)
    assert [f.name for f in result.accepted] == ["c.py"]
    assert "empty" in reasons(result)["a.py"].lower()
    assert "whitespace" in reasons(result)["b.py"].lower()


def test_only_py_files_accepted():
    result = process_uploads([("notes.txt", b"x = 1"), ("a.PY", b"x = 1")], LIMITS)
    assert [f.name for f in result.accepted] == ["a.PY"]
    assert "Only .py" in reasons(result)["notes.txt"]


def test_duplicate_names_are_renamed():
    result = process_uploads([("a.py", b"x = 1"), ("a.py", b"x = 2"), ("A.py", b"x = 3")], LIMITS)
    assert [f.name for f in result.accepted] == ["a.py", "a (2).py", "A (3).py"]
    assert result.accepted[1].renamed_from == "a.py"


def test_size_count_and_total_limits():
    big = b"x = 1\n" * 200
    r = process_uploads([("big.py", big)], UploadLimits(max_file_bytes=1024))
    assert "limit" in reasons(r)["big.py"]
    r = process_uploads([(f"f{i}.py", b"x = 1") for i in range(4)], UploadLimits(max_files=2))
    assert len(r.accepted) == 2 and len(r.rejected) == 2
    r = process_uploads([("a.py", big), ("b.py", big)], UploadLimits(max_total_bytes=len(big) + 10))
    assert len(r.accepted) == 1 and "total" in r.rejected[0].reason


def test_binary_and_encoding_handling():
    r = process_uploads([("bin.py", b"x = 1\x00\x01")], LIMITS)
    assert "binary" in reasons(r)["bin.py"]
    r = process_uploads([("latin.py", "s = 'caf\u00e9'\n".encode("cp1252"))], LIMITS)
    assert len(r.accepted) == 1 and "caf\u00e9" in r.accepted[0].text
    r = process_uploads([("bom.py", b"\xef\xbb\xbfx = 1\r\ny = 2\r\n")], LIMITS)
    assert r.accepted[0].text == "x = 1\ny = 2\n"


def test_path_components_are_stripped_from_names():
    r = process_uploads([("../../etc/evil.py", b"x = 1")], LIMITS)
    assert r.accepted[0].name == "evil.py"


# Test 9: security
def test_uploaded_code_is_never_executed(tmp_path):
    marker = tmp_path / "pwned.txt"
    evil = (
        f"open({str(marker)!r}, 'w').write('x')\n"
        "__import__('os').system('echo hacked')\n"
        "raise SystemExit(1)\n"
    )
    files = process_uploads([("evil.py", evil.encode()), ("ok.py", b"x = 1\n")], LIMITS).accepted
    result = run_analysis(files)
    assert not marker.exists()
    assert result.pairs[0].status == "ok"


def test_html_rendering_escapes_source():
    payload = "# <script>alert('xss')</script>\nname = '<img src=x onerror=alert(1)>'\n"
    left = highlight_lines(payload)
    diff = build_diff(payload, payload)
    page = render_diff_html(diff.rows, left, left)
    assert "<script" not in page and "<img" not in page
    assert "&lt;script" in page and "&lt;img" in page


def test_analyzer_source_never_calls_eval_exec_or_import():
    root = pathlib.Path(__file__).resolve().parent.parent
    for folder in ("analyzer", "utils", "components"):
        for path in (root / folder).glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    assert node.func.id not in {"eval", "exec", "__import__", "compile"}, f"{path.name}: {node.func.id}"
