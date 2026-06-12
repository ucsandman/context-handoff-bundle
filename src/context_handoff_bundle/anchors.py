"""Evidence anchor parsing, resolution, and content verification.

Evidence anchors are authored by agents as human-readable bullets like:

    orchestrator/company_loop/builder.py:59 — DEFAULT_BUILDER_CMD (new prompt)
    git commit 4a135d2 on main (pushed)
    https://github.com/remotion-dev/remotion — video lib
    py -3 -m pytest tests/ — verification run

Treating those raw strings as filesystem paths is what caused drift to mark
every anchor GONE. This module is the single shared parser: save uses it to
verify and hash anchors, load uses it to check them, freshness and token
estimation use it to resolve files. Parse the locator out, classify the kind,
and never existence-check prose.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

# Note separators in priority order of first occurrence (em dash, double
# hyphen, en dash). Everything after the first separator is the note.
_NOTE_SEPARATORS = (" — ", " -- ", " – ")

_COMMIT_RE = re.compile(r"^(?:git\s+)?commit\s+([0-9a-fA-F]{6,40})\b")
_BARE_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
_LINE_SUFFIX_RE = re.compile(r":(\d+)(?:-(\d+))?$")
# "Memory: C:\path" / "Config: ~/x" style label prefixes before a real path.
_LABEL_PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z ]*:\s+(?=[A-Za-z]:[\\/]|[\\/~.]|\w)")
_BARE_FILENAME_RE = re.compile(r"^[\w.\-]+\.[A-Za-z0-9]+$")


@dataclass
class Anchor:
    raw: str
    kind: str  # 'file' | 'url' | 'commit' | 'other'
    path: str | None = None  # file path or commit sha or url
    line_start: int | None = None
    line_end: int | None = None
    note: str = ""


def parse_anchor(raw: str) -> Anchor:
    """Parse a free-form evidence anchor string into a structured Anchor."""
    raw = (raw or "").strip()
    if not raw:
        return Anchor(raw=raw, kind="other")

    # Split off the note at the earliest separator occurrence.
    locator, note = raw, ""
    cut = min(
        (raw.find(sep) for sep in _NOTE_SEPARATORS if raw.find(sep) != -1),
        default=-1,
    )
    if cut != -1:
        sep_len = next(len(s) for s in _NOTE_SEPARATORS if raw.startswith(s, cut))
        locator, note = raw[:cut].strip(), raw[cut + sep_len :].strip()

    # URLs first (before any colon/paren surgery).
    if locator.startswith(("http://", "https://")):
        return Anchor(raw=raw, kind="url", path=locator.split(" ")[0], note=note)

    # Commit references ("git commit 4a135d2 on main", "commit 1eb485f").
    m = _COMMIT_RE.match(locator)
    if m:
        return Anchor(raw=raw, kind="commit", path=m.group(1), note=note)

    # Drop trailing parentheticals and "; extra" clauses from the locator.
    locator = locator.split(" (")[0].split("; ")[0].strip()

    # Strip a label prefix like "Memory: C:\path\file.md", but never eat a
    # Windows drive letter ("C:\..." has no space after the colon).
    locator = _LABEL_PREFIX_RE.sub("", locator)

    if _BARE_COMMIT_RE.match(locator):
        return Anchor(raw=raw, kind="commit", path=locator, note=note)

    # Pull off a ":line" / ":start-end" suffix.
    line_start = line_end = None
    m = _LINE_SUFFIX_RE.search(locator)
    if m:
        # Guard against eating a Windows drive colon ("C:" with no path).
        candidate = locator[: m.start()]
        if candidate and not re.fullmatch(r"[A-Za-z]", candidate):
            line_start = int(m.group(1))
            line_end = int(m.group(2)) if m.group(2) else None
            locator = candidate

    # A file locator has no spaces and either contains a path separator or
    # looks like a bare filename with an extension.
    if (
        locator
        and " " not in locator
        and ("/" in locator or "\\" in locator or _BARE_FILENAME_RE.match(locator))
    ):
        return Anchor(
            raw=raw,
            kind="file",
            path=locator,
            line_start=line_start,
            line_end=line_end,
            note=note,
        )

    return Anchor(raw=raw, kind="other", note=note)


def resolve_anchor_path(
    anchor: Anchor,
    repo_root: Path | str | None = None,
    cwd: Path | str | None = None,
) -> Path | None:
    """Resolve a file anchor to an existing file on disk, or None."""
    if anchor.kind != "file" or not anchor.path:
        return None
    candidate = Path(anchor.path)
    candidates = [candidate] if candidate.is_absolute() else []
    if not candidate.is_absolute():
        if repo_root:
            candidates.append(Path(repo_root) / candidate)
        if cwd:
            candidates.append(Path(cwd) / candidate)
    for c in candidates:
        try:
            if c.is_file():
                return c.resolve()
        except OSError:
            continue
    return None


def hash_anchor_content(
    path: Path,
    line_start: int | None,
    line_end: int | None,
) -> str | None:
    """Content hash for an anchor: the referenced line range, or the whole
    file when no lines are given. Line-range hashing means unrelated edits
    elsewhere in the file do not invalidate the anchor."""
    try:
        if line_start is None:
            return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        end = line_end if line_end is not None else line_start
        segment = "\n".join(lines[line_start - 1 : end])
        return hashlib.sha256(segment.encode("utf-8")).hexdigest()[:16]
    except OSError:
        return None


def normalize_for_match(path_str: str) -> str:
    """Normalize a path for exact comparison against git diff output
    (forward slashes, lowercased -- git paths are repo-relative and we only
    use this for matching, never for display)."""
    return path_str.replace("\\", "/").strip("/").lower()


def repo_relative(resolved: Path, repo_root: Path | str | None) -> str | None:
    """Repo-relative normalized form of a resolved path, or None if the file
    is outside the repo."""
    if not repo_root:
        return None
    try:
        rel = resolved.relative_to(Path(repo_root).resolve())
    except ValueError:
        return None
    return normalize_for_match(str(rel))


# Re-exported convenience used by save: parse + resolve + hash in one pass.
def verify_anchor(
    raw: str,
    repo_root: Path | str | None = None,
    cwd: Path | str | None = None,
) -> dict:
    """Classify and (for file anchors) verify an anchor at save time.

    Returns a dict of the optional evidence-index fields:
        anchor_kind, resolved_path (repo-relative when possible),
        line_start, line_end, content_hash, verified_at_save
    """
    anchor = parse_anchor(raw)
    out: dict = {
        "anchor_kind": anchor.kind,
        "resolved_path": None,
        "line_start": anchor.line_start,
        "line_end": anchor.line_end,
        "content_hash": None,
        "verified_at_save": False,
    }
    if anchor.kind != "file":
        return out
    resolved = resolve_anchor_path(anchor, repo_root=repo_root, cwd=cwd)
    if resolved is None:
        return out
    rel = repo_relative(resolved, repo_root)
    out["resolved_path"] = rel if rel is not None else str(resolved)
    out["content_hash"] = hash_anchor_content(
        resolved, anchor.line_start, anchor.line_end
    )
    out["verified_at_save"] = out["content_hash"] is not None
    return out
