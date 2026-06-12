"""Drift intelligence: what changed since the bundle was saved, and what it means.

This is the signature feature. Not just "repo drifted" -- show exactly:
- which evidence anchors still verify against the current repo
- which files changed
- which findings might be invalidated
- which recommendations may be unsafe

Anchor statuses:
    verified  file/commit anchor checked against content hash or git -- trustworthy
    ok        file exists and is untouched by the diff since save (no hash stored)
    changed   file exists but the anchored content (or the file) changed
    gone      file or commit no longer exists
    n/a       not file-checkable (URL, command, prose) -- never counted as risk

Findings are flagged only when their own anchors are changed/gone. Broad
repo activity (many commits, unrelated files) is reported as context, never
as a blanket "everything is stale" -- that cried wolf and made agents waste
tokens re-verifying healthy bundles.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .anchors import (
    hash_anchor_content,
    normalize_for_match,
    parse_anchor,
    repo_relative,
    resolve_anchor_path,
)

_RISKY = ("changed", "gone")


def analyze_drift(entry: dict, cwd: Path | None = None) -> dict:
    """Deep drift analysis between bundle state and current repo.

    Returns:
        {
            'has_drift': bool,
            'severity': 'none' | 'low' | 'medium' | 'high',
            'summary': str,
            'files_changed': [str, ...],
            'files_added': [str, ...],
            'files_deleted': [str, ...],
            'evidence_status': [{'path': str, 'status': str, 'role': str}, ...],
            'findings_at_risk': [{'id': str, 'title': str, 'reason': str}, ...],
            'recommendations_at_risk': [{'action': str, 'reason': str}, ...],
            'branch_drift': str | None,
            'commit_count': int,
            'age_hours': float | None,
        }
    """
    cwd = cwd or Path.cwd()
    result: dict = {
        "has_drift": False,
        "severity": "none",
        "summary": "No drift detected.",
        "files_changed": [],
        "files_added": [],
        "files_deleted": [],
        "evidence_status": [],
        "findings_at_risk": [],
        "recommendations_at_risk": [],
        "branch_drift": None,
        "commit_count": 0,
        "age_hours": None,
    }

    saved_commit = entry.get("head_commit", "")
    saved_branch = entry.get("branch", "")
    bundle_path = Path(entry.get("path", ""))
    repo_root = entry.get("repo_root", "") or str(cwd)

    # ── Age ──
    from .freshness import check_freshness

    freshness = check_freshness(entry, cwd)
    result["age_hours"] = freshness.get("age_hours")

    # ── Branch drift ──
    current_branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if saved_branch and current_branch and saved_branch != current_branch:
        result["branch_drift"] = f'Saved on "{saved_branch}", now on "{current_branch}"'
        result["has_drift"] = True

    # ── File-level drift since saved commit ──
    if saved_commit:
        current_commit = _git(cwd, "rev-parse", "HEAD")
        if current_commit and current_commit != saved_commit:
            result["has_drift"] = True

            # Count commits
            count = _git(
                cwd, "rev-list", "--count", f"{saved_commit}..{current_commit}"
            )
            result["commit_count"] = int(count) if count.isdigit() else 0

            # Get changed files with status
            diff_output = _git(
                cwd, "diff", "--name-status", saved_commit, current_commit
            )
            for line in diff_output.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    status, filepath = parts[0].strip(), parts[-1].strip()
                    if status.startswith("A"):
                        result["files_added"].append(filepath)
                    elif status.startswith("D"):
                        result["files_deleted"].append(filepath)
                    elif status.startswith("M") or status.startswith("R"):
                        result["files_changed"].append(filepath)

        # Also include uncommitted changes
        dirty = _git(cwd, "diff", "--name-only")
        staged = _git(cwd, "diff", "--name-only", "--cached")
        for f in (dirty + "\n" + staged).splitlines():
            f = f.strip()
            if f and f not in result["files_changed"]:
                result["files_changed"].append(f)
                result["has_drift"] = True

    # ── Evidence anchor status ──
    # Exact repo-relative path matching against the diff; never basename
    # matching (a changed b/route.ts must not implicate a/route.ts).
    anchor_status: dict[str, str] = {}
    if bundle_path.exists():
        evidence = _load_json_list(bundle_path / "evidence_index.json")
        changed_set = {normalize_for_match(f) for f in result["files_changed"]}
        deleted_set = {normalize_for_match(f) for f in result["files_deleted"]}

        for item in evidence:
            raw = item.get("path", "")
            if not raw:
                continue
            status = _anchor_status(item, raw, repo_root, cwd, changed_set, deleted_set)
            anchor_status[raw] = status
            result["evidence_status"].append(
                {
                    "path": raw,
                    "status": status,
                    "role": item.get("role", ""),
                }
            )
            if status in _RISKY:
                result["has_drift"] = True

    # ── Which findings are at risk ──
    # Only findings whose own evidence anchors are changed/gone. No
    # commit-count blankets.
    if bundle_path.exists():
        summary_data = _load_json_dict(bundle_path / "summary.json")
        findings = summary_data.get("findings", [])
        for f in findings:
            for ev in f.get("evidence", []):
                status = anchor_status.get(ev)
                if status in _RISKY:
                    result["findings_at_risk"].append(
                        {
                            "id": f.get("id", ""),
                            "title": f.get("title", f.get("summary", "")[:60]),
                            "reason": f"Evidence anchor {status}: {ev[:80]}",
                        }
                    )
                    break

        # Recommendations at risk only when the bundle's checkable evidence
        # has majority-drifted -- not because unrelated commits landed.
        checkable = [s for s in anchor_status.values() if s != "n/a"]
        impacted = sum(1 for s in checkable if s in _RISKY)
        if checkable and impacted * 2 > len(checkable):
            reason = (
                f"{impacted}/{len(checkable)} checkable evidence anchors "
                "changed or gone since save"
            )
            for r in summary_data.get("recommendations", []):
                result["recommendations_at_risk"].append(
                    {
                        "action": r.get("action", ""),
                        "reason": reason,
                    }
                )

    # ── Severity: driven by anchor impact, not raw repo activity ──
    statuses = list(anchor_status.values())
    gone = statuses.count("gone")
    changed = statuses.count("changed")
    if not result["has_drift"]:
        result["severity"] = "none"
    elif gone >= 2 or len(result["findings_at_risk"]) >= 3:
        result["severity"] = "high"
    elif (
        gone == 1
        or result["findings_at_risk"]
        or changed >= 3
        or result["branch_drift"]
    ):
        result["severity"] = "medium"
    else:
        result["severity"] = "low"

    # ── Summary ──
    result["summary"] = _build_summary(result)

    return result


def _anchor_status(
    item: dict,
    raw: str,
    repo_root: str,
    cwd: Path,
    changed_set: set[str],
    deleted_set: set[str],
) -> str:
    anchor = parse_anchor(raw)

    if anchor.kind in ("url", "other"):
        return "n/a"

    if anchor.kind == "commit":
        ok = _git_ok(cwd, "cat-file", "-e", f"{anchor.path}^{{commit}}")
        return "verified" if ok else "gone"

    resolved = resolve_anchor_path(anchor, repo_root=repo_root, cwd=cwd)
    if resolved is None:
        return "gone"

    stored_hash = item.get("content_hash")
    if stored_hash:
        # Bundles saved with verification: re-hash the anchored content.
        line_start = item.get("line_start", anchor.line_start)
        line_end = item.get("line_end", anchor.line_end)
        current = hash_anchor_content(resolved, line_start, line_end)
        return "verified" if current == stored_hash else "changed"

    # Legacy bundles (no hash): exact-path comparison against the diff.
    rel = repo_relative(resolved, repo_root)
    if rel and (rel in changed_set or rel in deleted_set):
        return "changed"
    return "ok"


def format_drift_report(drift: dict) -> str:
    """Format drift analysis into a readable report for the resume.

    Low-impact drift (repo moved, anchors intact) collapses to two lines so
    a healthy load does not spend tokens on alarm formatting.
    """
    if not drift["has_drift"]:
        return ""

    statuses = [e["status"] for e in drift["evidence_status"]]
    counts = {
        s: statuses.count(s) for s in ("verified", "ok", "changed", "gone", "n/a")
    }
    anchors_line = _anchors_line(counts)

    parts: list[str] = ["## Drift"]

    # Compact path: nothing the next session needs to re-verify.
    low_impact = (
        drift["severity"] == "low"
        and not drift["findings_at_risk"]
        and counts["changed"] == 0
        and counts["gone"] == 0
    )
    if low_impact:
        activity = []
        if drift["commit_count"]:
            activity.append(f"{drift['commit_count']} commit(s)")
        touched = (
            len(drift["files_changed"])
            + len(drift["files_added"])
            + len(drift["files_deleted"])
        )
        if touched:
            activity.append(f"{touched} file(s) touched")
        line = " and ".join(activity) or "Repo activity"
        parts.append(f"{line} since save; no evidence anchors affected. {anchors_line}")
        return "\n".join(parts)

    parts.append(f"**Severity: {drift['severity'].upper()}** -- {drift['summary']}")
    if anchors_line:
        parts.append(anchors_line)

    if drift["branch_drift"]:
        parts.append(f"- {drift['branch_drift']}")
    if drift["commit_count"]:
        parts.append(f"- {drift['commit_count']} commit(s) since save")

    # Only the anchors that actually need attention are listed individually.
    affected = [e for e in drift["evidence_status"] if e["status"] in _RISKY]
    if affected:
        parts.append("\n**Anchors needing attention:**")
        for e in affected:
            parts.append(f"- `{e['path']}` {e['status'].upper()}")

    if drift["files_deleted"]:
        parts.append(f"\n**Files deleted ({len(drift['files_deleted'])}):**")
        for f in drift["files_deleted"][:5]:
            parts.append(f"- `{f}` DELETED")

    if drift["findings_at_risk"]:
        parts.append("\n**Findings that may be stale:**")
        for f in drift["findings_at_risk"]:
            parts.append(f"- **{f['id']}** {f['title']} -- {f['reason']}")

    if drift["recommendations_at_risk"]:
        parts.append("\n**Recommendations that may be unsafe:**")
        for r in drift["recommendations_at_risk"]:
            parts.append(f"- {r['action']} -- {r['reason']}")

    return "\n".join(parts)


def _anchors_line(counts: dict[str, int]) -> str:
    checkable = sum(v for k, v in counts.items() if k != "n/a")
    if not checkable:
        return ""
    bits = []
    for key, label in (
        ("verified", "verified"),
        ("ok", "unchanged"),
        ("changed", "changed"),
        ("gone", "gone"),
    ):
        if counts[key]:
            bits.append(f"{counts[key]} {label}")
    line = f"Evidence anchors: {', '.join(bits)}"
    if counts["n/a"]:
        line += f" ({counts['n/a']} not file-checkable)"
    return line


def _build_summary(drift: dict) -> str:
    parts: list[str] = []
    if drift["commit_count"]:
        parts.append(f"{drift['commit_count']} commits")
    fc = len(drift["files_changed"])
    fa = len(drift["files_added"])
    fd = len(drift["files_deleted"])
    if fc + fa + fd > 0:
        parts.append(f"{fc + fa + fd} files touched")
    at_risk = len(drift["findings_at_risk"])
    if at_risk:
        parts.append(f"{at_risk} finding(s) at risk")
    if drift["branch_drift"]:
        parts.append("branch changed")
    if not parts:
        return "Minor drift detected."
    return ", ".join(parts) + " since save."


def _git(cwd: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=str(cwd),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return ""


def _git_ok(cwd: Path, *args: str) -> bool:
    try:
        return (
            subprocess.call(
                ["git", *args],
                cwd=str(cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            == 0
        )
    except Exception:
        return False


def _load_json_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _load_json_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
