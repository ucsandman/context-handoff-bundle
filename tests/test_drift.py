"""Drift analysis tests: no more false GONE / blanket stale flags.

Recreates the real failure: a bundle whose anchors are composite strings
("file.py:59 — note", "git commit abc123 ..."), loaded in a repo where the
anchored files exist untouched and only unrelated files changed. Old drift
marked every anchor GONE and every finding/recommendation stale.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from context_handoff_bundle.anchors import verify_anchor
from context_handoff_bundle.drift import analyze_drift, format_drift_report


def _git(cwd: Path, *args: str) -> str:
    # --no-verify on commits: the host machine may have global pre-commit
    # hooks (ruff/vulture) that would block these throwaway fixture commits.
    if args and args[0] == "commit":
        args = (args[0], "--no-verify", *args[1:])
    return subprocess.check_output(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


@pytest.fixture
def repo(tmp_path):
    """A tiny git repo with two files and one commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "builder.py").write_text(
        "\n".join(f"line {i}" for i in range(1, 21)) + "\n", encoding="utf-8"
    )
    (repo / "unrelated.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


def _make_bundle(tmp_path: Path, evidence: list[dict], findings=None, recs=None):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "evidence_index.json").write_text(json.dumps(evidence), encoding="utf-8")
    summary = {
        "findings": findings or [],
        "recommendations": recs or [],
    }
    (bundle / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return bundle


def _entry(repo: Path, bundle: Path) -> dict:
    return {
        "path": str(bundle),
        "repo_root": str(repo),
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "head_commit": _git(repo, "rev-parse", "HEAD"),
        "created_at": "2026-06-12T00:00:00+00:00",
    }


class TestNoFalseGone:
    def test_composite_anchor_on_existing_file_is_not_gone(self, tmp_path, repo):
        """The original bug: 'file.py:5 — note' marked GONE while file exists."""
        evidence = [
            {
                "path": "builder.py:5 — DEFAULT_BUILDER_CMD (supergoal prompt)",
                "role": "reference",
            }
        ]
        bundle = _make_bundle(tmp_path, evidence)
        entry = _entry(repo, bundle)

        drift = analyze_drift(entry, cwd=repo)
        statuses = {e["path"]: e["status"] for e in drift["evidence_status"]}
        assert statuses[evidence[0]["path"]] in ("ok", "verified")
        assert drift["severity"] == "none"

    def test_head_commit_anchor_is_verified_not_gone(self, tmp_path, repo):
        head = _git(repo, "rev-parse", "--short", "HEAD")
        evidence = [
            {"path": f"git commit {head} on main (pushed)", "role": "reference"}
        ]
        bundle = _make_bundle(tmp_path, evidence)
        drift = analyze_drift(_entry(repo, bundle), cwd=repo)
        assert drift["evidence_status"][0]["status"] == "verified"

    def test_bogus_commit_anchor_is_gone(self, tmp_path, repo):
        evidence = [
            {"path": "git commit deadbeef00 — never existed", "role": "reference"}
        ]
        bundle = _make_bundle(tmp_path, evidence)
        drift = analyze_drift(_entry(repo, bundle), cwd=repo)
        assert drift["evidence_status"][0]["status"] == "gone"

    def test_prose_and_command_anchors_are_na(self, tmp_path, repo):
        evidence = [
            {"path": "py -3 -m pytest tests/ — verification run", "role": "reference"},
            {"path": "the websocket auth design discussion", "role": "reference"},
        ]
        bundle = _make_bundle(tmp_path, evidence)
        drift = analyze_drift(_entry(repo, bundle), cwd=repo)
        assert all(e["status"] == "n/a" for e in drift["evidence_status"])
        assert drift["findings_at_risk"] == []


class TestContentHashVerification:
    def test_hash_match_is_verified(self, tmp_path, repo):
        fields = verify_anchor("builder.py:2-4 — early lines", repo_root=repo)
        assert fields["verified_at_save"]
        evidence = [
            {"path": "builder.py:2-4 — early lines", "role": "reference", **fields}
        ]
        bundle = _make_bundle(tmp_path, evidence)
        drift = analyze_drift(_entry(repo, bundle), cwd=repo)
        assert drift["evidence_status"][0]["status"] == "verified"

    def test_in_range_edit_is_changed(self, tmp_path, repo):
        fields = verify_anchor("builder.py:2-4 — early lines", repo_root=repo)
        evidence = [
            {"path": "builder.py:2-4 — early lines", "role": "reference", **fields}
        ]
        bundle = _make_bundle(tmp_path, evidence)
        entry = _entry(repo, bundle)

        text = (repo / "builder.py").read_text(encoding="utf-8").splitlines()
        text[2] = "EDITED"
        (repo / "builder.py").write_text("\n".join(text) + "\n", encoding="utf-8")

        drift = analyze_drift(entry, cwd=repo)
        assert drift["evidence_status"][0]["status"] == "changed"

    def test_out_of_range_edit_stays_verified(self, tmp_path, repo):
        fields = verify_anchor("builder.py:2-4 — early lines", repo_root=repo)
        evidence = [
            {"path": "builder.py:2-4 — early lines", "role": "reference", **fields}
        ]
        bundle = _make_bundle(tmp_path, evidence)
        entry = _entry(repo, bundle)

        text = (repo / "builder.py").read_text(encoding="utf-8").splitlines()
        text[15] = "EDITED FAR AWAY"
        (repo / "builder.py").write_text("\n".join(text) + "\n", encoding="utf-8")

        drift = analyze_drift(entry, cwd=repo)
        assert drift["evidence_status"][0]["status"] == "verified"


class TestNoBlanketFlags:
    def test_unrelated_changes_do_not_flag_findings_or_recs(self, tmp_path, repo):
        """Unrelated edits + new commits must not mark anchored findings stale."""
        anchor = "builder.py:5 — DEFAULT_BUILDER_CMD"
        fields = verify_anchor(anchor, repo_root=repo)
        evidence = [{"path": anchor, "role": "reference", **fields}]
        findings = [
            {
                "id": "F1",
                "title": "builder cmd",
                "summary": "builder cmd",
                "evidence": [anchor],
            }
        ]
        recs = [{"priority": 1, "action": "do the thing"}]
        bundle = _make_bundle(tmp_path, evidence, findings, recs)
        entry = _entry(repo, bundle)

        # 12 commits touching only the unrelated file (old code: >10 commits
        # blanket-flagged every finding, >5 flagged every recommendation).
        for i in range(12):
            (repo / "unrelated.py").write_text(f"x = {i}\n", encoding="utf-8")
            _git(repo, "add", ".")
            _git(repo, "commit", "-q", "-m", f"c{i}")

        drift = analyze_drift(entry, cwd=repo)
        assert drift["has_drift"] is True
        assert drift["commit_count"] == 12
        assert drift["evidence_status"][0]["status"] == "verified"
        assert drift["findings_at_risk"] == []
        assert drift["recommendations_at_risk"] == []
        assert drift["severity"] == "low"

    def test_anchored_finding_flagged_when_its_file_deleted(self, tmp_path, repo):
        anchor = "builder.py:5 — DEFAULT_BUILDER_CMD"
        evidence = [{"path": anchor, "role": "reference"}]
        findings = [{"id": "F1", "title": "t", "summary": "s", "evidence": [anchor]}]
        bundle = _make_bundle(tmp_path, evidence, findings)
        entry = _entry(repo, bundle)

        (repo / "builder.py").unlink()
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "delete builder")

        drift = analyze_drift(entry, cwd=repo)
        assert drift["evidence_status"][0]["status"] == "gone"
        assert len(drift["findings_at_risk"]) == 1
        assert drift["severity"] in ("medium", "high")

    def test_basename_collision_does_not_mark_changed(self, tmp_path, repo):
        """Old code matched on basename endswith: editing any 'route.ts' marked
        every 'route.ts' anchor changed. Exact repo-relative paths only."""
        (repo / "a").mkdir()
        (repo / "b").mkdir()
        (repo / "a" / "route.ts").write_text("a\n", encoding="utf-8")
        (repo / "b" / "route.ts").write_text("b\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "routes")

        evidence = [{"path": "a/route.ts — handler A", "role": "reference"}]
        bundle = _make_bundle(tmp_path, evidence)
        entry = _entry(repo, bundle)

        (repo / "b" / "route.ts").write_text("b changed\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "edit b only")

        drift = analyze_drift(entry, cwd=repo)
        assert drift["evidence_status"][0]["status"] == "ok"


class TestReportFormat:
    def test_clean_low_drift_report_is_compact(self, tmp_path, repo):
        anchor = "builder.py:5 — cmd"
        fields = verify_anchor(anchor, repo_root=repo)
        evidence = [{"path": anchor, "role": "reference", **fields}]
        bundle = _make_bundle(tmp_path, evidence)
        entry = _entry(repo, bundle)

        (repo / "unrelated.py").write_text("x = 99\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "unrelated")

        drift = analyze_drift(entry, cwd=repo)
        report = format_drift_report(drift)
        assert "GONE" not in report
        assert "verified" in report.lower()
        # Compact: no per-file dumps for a low-impact drift
        assert len(report.splitlines()) <= 6
