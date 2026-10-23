"""Tests for pure helper functions."""

from decomp_mcp.server import extract_slug_from_url, format_diff_output, format_scratch_info

from .conftest import SCRATCH


def test_extract_slug_from_url():
    assert extract_slug_from_url("https://decomp.me/scratch/abc12") == "abc12"
    assert extract_slug_from_url("https://decomp.me/scratch/abc12/") == "abc12"
    assert extract_slug_from_url("https://decomp.me/scratch/abc12/compile") == "abc12"


def test_extract_slug_passes_through_bare_slug():
    assert extract_slug_from_url("abc12") == "abc12"


def test_extract_slug_url_without_scratch_returns_input():
    url = "https://decomp.me/preset/1"
    assert extract_slug_from_url(url) == url


def test_format_scratch_info():
    out = format_scratch_info(SCRATCH)
    assert "# Scratch: example_func (abc12)" in out
    assert "**Platform:** gc_wii" in out
    assert "**Compiler:** mwcc_233_163n" in out
    assert "**Score:** 50 / 200" in out
    assert "**Description:** A made-up scratch for tests" in out
    assert SCRATCH["source_code"] in out


def test_format_scratch_info_minimal_fields():
    out = format_scratch_info({"slug": "x", "platform": "n64", "compiler": "gcc"})
    assert "# Scratch: Unnamed (x)" in out
    assert "**Description:**" not in out


def row(base: str, current: str) -> dict:
    return {"base": {"text": [{"text": base}]}, "current": {"text": [{"text": current}]}}


def test_format_diff_output_perfect_match():
    out = format_diff_output({"current_score": 0, "max_score": 100, "rows": []})
    assert "PERFECT MATCH" in out


def test_format_diff_output_match_percent():
    out = format_diff_output({"current_score": 25, "max_score": 100, "rows": []})
    assert "**Diff Score:** 25 / 100" in out
    assert "75.0%" in out


def test_format_diff_output_rows():
    out = format_diff_output({
        "current_score": 10,
        "max_score": 100,
        "rows": [
            row("same", "same"),
            row("only in target", ""),
            row("", "only in current"),
            row("old", "new"),
        ],
    })
    assert "  same" in out
    assert "- only in target" in out
    assert "+ only in current" in out
    assert "- old\n+ new" in out


def test_format_diff_output_accepts_plain_string_text():
    out = format_diff_output({
        "current_score": 1,
        "max_score": 2,
        "rows": [{"base": {"text": "a"}, "current": {"text": "a"}}],
    })
    assert "  a" in out


def test_format_diff_output_truncates_after_50_rows():
    rows = [row(f"line {i}", f"line {i}") for i in range(60)]
    out = format_diff_output({"current_score": 1, "max_score": 2, "rows": rows})
    assert "line 49" in out
    assert "line 50" not in out
    assert "... (10 more rows)" in out
