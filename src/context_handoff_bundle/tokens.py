"""Token estimation for handoff bundles.

Uses the standard ~4 characters per token heuristic. Estimates are
order-of-magnitude honest, not billing-accurate, and every surface that
shows them labels them as estimates. The point is to make the cost of a
resume visible next to the cost of re-deriving the same understanding
from source files.
"""

from __future__ import annotations

from pathlib import Path

CHARS_PER_TOKEN = 4

# Orientation files a fresh agent session typically reads before doing
# anything useful in a repo, independent of the task at hand.
ORIENTATION_FILES = [
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "package.json",
]


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_file_tokens(path: Path) -> int:
    # st_size is bytes; for source text, bytes ~= chars.
    try:
        if not path.is_file():
            return 0
        return max(1, path.stat().st_size // CHARS_PER_TOKEN)
    except OSError:
        return 0


def format_tokens(count: int) -> str:
    if count >= 1000:
        return f"~{count / 1000:.1f}k"
    return f"~{count}"


def bundle_tokens(bundle_dir: Path) -> int:
    total = 0
    try:
        for path in bundle_dir.iterdir():
            total += estimate_file_tokens(path)
    except OSError:
        pass
    return total


def _resolve_anchor(repo_root: Path, anchor: str) -> Path | None:
    raw = anchor.strip()
    if not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = repo_root / raw
    try:
        if candidate.is_file():
            return candidate.resolve()
    except OSError:
        pass
    return None


def estimate_reread_tokens(repo_root: Path, evidence_paths: list[str]) -> dict:
    """Estimate what a fresh session would spend re-reading the evidence
    files plus standard orientation files to rebuild the same context."""
    counted: set[Path] = set()
    evidence_tokens = 0
    for anchor in evidence_paths:
        resolved = _resolve_anchor(repo_root, anchor)
        if resolved is None or resolved in counted:
            continue
        counted.add(resolved)
        evidence_tokens += estimate_file_tokens(resolved)

    orientation_tokens = 0
    for name in ORIENTATION_FILES:
        path = repo_root / name
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in counted or not path.is_file():
            continue
        counted.add(resolved)
        orientation_tokens += estimate_file_tokens(path)

    return {
        "evidence_tokens": evidence_tokens,
        "orientation_tokens": orientation_tokens,
        "total": evidence_tokens + orientation_tokens,
        "files_counted": len(counted),
    }
