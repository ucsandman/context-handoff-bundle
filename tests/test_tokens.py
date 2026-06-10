"""Unit tests for token estimation."""

from __future__ import annotations


from context_handoff_bundle.tokens import (
    bundle_tokens,
    estimate_file_tokens,
    estimate_reread_tokens,
    estimate_tokens,
    format_tokens,
)


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_string_floors_at_one(self):
        assert estimate_tokens("ab") == 1

    def test_chars_per_token_heuristic(self):
        assert estimate_tokens("x" * 4000) == 1000


class TestFormatTokens:
    def test_below_thousand(self):
        assert format_tokens(840) == "~840"

    def test_thousands(self):
        assert format_tokens(1234) == "~1.2k"

    def test_large(self):
        assert format_tokens(48200) == "~48.2k"


class TestFileTokens:
    def test_missing_file(self, tmp_path):
        assert estimate_file_tokens(tmp_path / "nope.txt") == 0

    def test_directory_returns_zero(self, tmp_path):
        assert estimate_file_tokens(tmp_path) == 0

    def test_real_file(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x" * 400, encoding="utf-8")
        assert estimate_file_tokens(f) == 100


class TestBundleTokens:
    def test_sums_files_in_dir(self, tmp_path):
        (tmp_path / "a.txt").write_text("x" * 400, encoding="utf-8")
        (tmp_path / "b.txt").write_text("y" * 800, encoding="utf-8")
        assert bundle_tokens(tmp_path) == 300

    def test_missing_dir(self, tmp_path):
        assert bundle_tokens(tmp_path / "gone") == 0


class TestRereadEstimate:
    def test_counts_evidence_and_orientation(self, tmp_path):
        (tmp_path / "README.md").write_text("r" * 4000, encoding="utf-8")
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("m" * 8000, encoding="utf-8")

        result = estimate_reread_tokens(tmp_path, ["src/main.py"])
        assert result["evidence_tokens"] == 2000
        assert result["orientation_tokens"] == 1000
        assert result["total"] == 3000
        assert result["files_counted"] == 2

    def test_deduplicates_anchors(self, tmp_path):
        (tmp_path / "a.py").write_text("a" * 400, encoding="utf-8")
        result = estimate_reread_tokens(
            tmp_path, ["a.py", "a.py", str(tmp_path / "a.py")]
        )
        assert result["evidence_tokens"] == 100
        assert result["files_counted"] == 1

    def test_missing_anchors_ignored(self, tmp_path):
        result = estimate_reread_tokens(tmp_path, ["does/not/exist.py", ""])
        assert result["total"] == 0
        assert result["files_counted"] == 0
