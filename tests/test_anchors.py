"""Unit tests for evidence anchor parsing and verification."""

from __future__ import annotations


from context_handoff_bundle.anchors import (
    hash_anchor_content,
    normalize_for_match,
    parse_anchor,
    resolve_anchor_path,
)


class TestParseAnchor:
    def test_plain_relative_path(self):
        a = parse_anchor("pipeline-tracker/api/security.py")
        assert a.kind == "file"
        assert a.path == "pipeline-tracker/api/security.py"
        assert a.line_start is None
        assert a.note == ""

    def test_path_with_line(self):
        a = parse_anchor("orchestrator/company_loop/builder.py:59")
        assert a.kind == "file"
        assert a.path == "orchestrator/company_loop/builder.py"
        assert a.line_start == 59
        assert a.line_end is None

    def test_path_with_line_range(self):
        a = parse_anchor("orchestrator/company_loop/builder.py:95-111")
        assert a.kind == "file"
        assert a.path == "orchestrator/company_loop/builder.py"
        assert a.line_start == 95
        assert a.line_end == 111

    def test_composite_em_dash_note(self):
        """The exact format that caused the false-GONE bug."""
        raw = (
            "orchestrator/company_loop/builder.py:59 — DEFAULT_BUILDER_CMD "
            "(new supergoal prompt, bypassPermissions)"
        )
        a = parse_anchor(raw)
        assert a.kind == "file"
        assert a.path == "orchestrator/company_loop/builder.py"
        assert a.line_start == 59
        assert "DEFAULT_BUILDER_CMD" in a.note

    def test_composite_double_hyphen_note(self):
        a = parse_anchor("src/app.ts:10 -- entry point")
        assert a.kind == "file"
        assert a.path == "src/app.ts"
        assert a.line_start == 10
        assert a.note == "entry point"

    def test_windows_absolute_path(self):
        a = parse_anchor("C:\\Projects\\thing\\file.py:12 — a note")
        assert a.kind == "file"
        assert a.path == "C:\\Projects\\thing\\file.py"
        assert a.line_start == 12

    def test_label_prefix_stripped(self):
        a = parse_anchor("Memory: C:\\Users\\x\\memory\\note.md")
        assert a.kind == "file"
        assert a.path == "C:\\Users\\x\\memory\\note.md"

    def test_url(self):
        a = parse_anchor("https://github.com/remotion-dev/remotion — video lib")
        assert a.kind == "url"
        assert a.path.startswith("https://")

    def test_git_commit_phrase(self):
        """'git commit 4a135d2 on main (pushed ...)' must not be treated as a file."""
        a = parse_anchor(
            "git commit 4a135d2 on main (pushed to ucsandman/Practical-Systems)"
        )
        assert a.kind == "commit"
        assert a.path == "4a135d2"

    def test_commit_phrase_without_git_word(self):
        a = parse_anchor("commit 1eb485f — merged Company OS")
        assert a.kind == "commit"
        assert a.path == "1eb485f"

    def test_prose_is_other(self):
        a = parse_anchor("the websocket auth design discussion")
        assert a.kind == "other"

    def test_command_is_other(self):
        a = parse_anchor("py -3 -m pytest tests/ — verification run")
        assert a.kind == "other"

    def test_bare_filename_is_file(self):
        a = parse_anchor("CLAUDE.md:704-714 — dev-loop env block")
        assert a.kind == "file"
        assert a.path == "CLAUDE.md"
        assert a.line_start == 704
        assert a.line_end == 714

    def test_parenthetical_stripped_from_locator(self):
        a = parse_anchor("src/main.py:5 (why it matters); extra notes")
        assert a.kind == "file"
        assert a.path == "src/main.py"
        assert a.line_start == 5

    def test_empty_string(self):
        a = parse_anchor("")
        assert a.kind == "other"


class TestResolveAndHash:
    def test_resolve_relative_to_repo_root(self, tmp_path):
        f = tmp_path / "sub" / "x.py"
        f.parent.mkdir()
        f.write_text("line1\nline2\nline3\n", encoding="utf-8")
        a = parse_anchor("sub/x.py:2")
        resolved = resolve_anchor_path(a, repo_root=tmp_path)
        assert resolved is not None
        assert resolved.name == "x.py"

    def test_resolve_missing_returns_none(self, tmp_path):
        a = parse_anchor("sub/nope.py")
        assert resolve_anchor_path(a, repo_root=tmp_path) is None

    def test_hash_line_range_stable_and_sensitive(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text("a\nb\nc\nd\n", encoding="utf-8")
        h1 = hash_anchor_content(f, 2, 3)
        h2 = hash_anchor_content(f, 2, 3)
        assert h1 == h2
        # Changing an out-of-range line does not affect the range hash
        f.write_text("CHANGED\nb\nc\nd\n", encoding="utf-8")
        assert hash_anchor_content(f, 2, 3) == h1
        # Changing an in-range line does
        f.write_text("CHANGED\nb\nX\nd\n", encoding="utf-8")
        assert hash_anchor_content(f, 2, 3) != h1

    def test_hash_whole_file_when_no_lines(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text("a\nb\n", encoding="utf-8")
        h1 = hash_anchor_content(f, None, None)
        f.write_text("a\nb\nc\n", encoding="utf-8")
        assert hash_anchor_content(f, None, None) != h1

    def test_normalize_for_match(self):
        assert normalize_for_match("A\\B\\c.py") == normalize_for_match("a/b/C.py")
