"""Bundle comparison: what changed between two handoff snapshots.

Shows new findings, resolved questions, invalidated recommendations,
entity changes, and evidence evolution.
"""
from __future__ import annotations

import json
from pathlib import Path


def compare_bundles(bundle_a: Path, bundle_b: Path) -> dict:
    """Compare two bundles and summarize what changed.

    Args:
        bundle_a: Path to the older bundle
        bundle_b: Path to the newer bundle

    Returns:
        Structured comparison with diffs per section.
    """
    a = _load_bundle(bundle_a)
    b = _load_bundle(bundle_b)

    return {
        'bundle_a': {'path': str(bundle_a), 'title': a['title'], 'date': a['date']},
        'bundle_b': {'path': str(bundle_b), 'title': b['title'], 'date': b['date']},
        'findings': _diff_findings(a['findings'], b['findings']),
        'questions': _diff_questions(a['questions'], b['questions']),
        'recommendations': _diff_recommendations(a['recommendations'], b['recommendations']),
        'evidence': _diff_evidence(a['evidence'], b['evidence']),
        'entities': _diff_entities(a['entities'], b['entities']),
    }


def format_comparison(comp: dict) -> str:
    """Format a comparison result into readable output."""
    parts: list[str] = []
    parts.append(f'# Bundle Comparison')
    parts.append(f'')
    parts.append(f'**A (older):** {comp["bundle_a"]["title"]} ({comp["bundle_a"]["date"]})')
    parts.append(f'**B (newer):** {comp["bundle_b"]["title"]} ({comp["bundle_b"]["date"]})')

    # Findings
    fd = comp['findings']
    if fd['added'] or fd['removed'] or fd['changed']:
        parts.append('\n## Findings')
        for f in fd['added']:
            parts.append(f'+ NEW: {f}')
        for f in fd['removed']:
            parts.append(f'- GONE: {f}')
        for old, new in fd['changed']:
            parts.append(f'~ CHANGED: "{old[:50]}" -> "{new[:50]}"')
    else:
        parts.append('\n## Findings\nNo changes.')

    # Questions
    qd = comp['questions']
    if qd['added'] or qd['resolved']:
        parts.append('\n## Open Questions')
        for q in qd['resolved']:
            parts.append(f'RESOLVED: {q}')
        for q in qd['added']:
            parts.append(f'+ NEW: {q}')
    else:
        parts.append('\n## Open Questions\nNo changes.')

    # Recommendations
    rd = comp['recommendations']
    if rd['added'] or rd['removed']:
        parts.append('\n## Recommendations')
        for r in rd['added']:
            parts.append(f'+ NEW: {r}')
        for r in rd['removed']:
            parts.append(f'- DROPPED: {r}')
    else:
        parts.append('\n## Recommendations\nNo changes.')

    # Evidence
    ed = comp['evidence']
    if ed['added'] or ed['removed']:
        parts.append('\n## Evidence')
        for e in ed['added']:
            parts.append(f'+ NEW: {e}')
        for e in ed['removed']:
            parts.append(f'- GONE: {e}')
    else:
        parts.append('\n## Evidence\nNo changes.')

    # Summary
    total_changes = (
        len(fd['added']) + len(fd['removed']) + len(fd['changed'])
        + len(qd['added']) + len(qd['resolved'])
        + len(rd['added']) + len(rd['removed'])
    )
    parts.append(f'\n---')
    parts.append(f'**Total changes:** {total_changes}')
    if qd['resolved']:
        parts.append(f'**Questions resolved:** {len(qd["resolved"])}')

    return '\n'.join(parts)


# ── Internal ──

def _load_bundle(path: Path) -> dict:
    path = Path(path).expanduser().resolve()
    summary = _load_json(path / 'summary.json', {})
    return {
        'title': summary.get('title', 'Unknown'),
        'date': summary.get('date', '?'),
        'findings': summary.get('findings', []),
        'recommendations': summary.get('recommendations', []),
        'questions': _load_json(path / 'open_questions.json', []),
        'evidence': _load_json(path / 'evidence_index.json', []),
        'entities': _load_json(path / 'entities.json', []),
    }


def _diff_findings(a: list[dict], b: list[dict]) -> dict:
    a_texts = {f.get('summary', f.get('title', '')): f.get('id', '') for f in a}
    b_texts = {f.get('summary', f.get('title', '')): f.get('id', '') for f in b}
    a_set = set(a_texts.keys())
    b_set = set(b_texts.keys())
    return {
        'added': sorted(b_set - a_set),
        'removed': sorted(a_set - b_set),
        'changed': [],  # Would need fuzzy matching for real change detection
        'unchanged_count': len(a_set & b_set),
    }


def _diff_questions(a: list[dict], b: list[dict]) -> dict:
    a_texts = {q.get('question', ''): q.get('id', '') for q in a}
    b_texts = {q.get('question', ''): q.get('id', '') for q in b}
    a_set = set(a_texts.keys())
    b_set = set(b_texts.keys())
    return {
        'resolved': sorted(a_set - b_set),  # In A but not B = resolved
        'added': sorted(b_set - a_set),      # In B but not A = new
        'unchanged_count': len(a_set & b_set),
    }


def _diff_recommendations(a: list[dict], b: list[dict]) -> dict:
    a_actions = {r.get('action', '') for r in a}
    b_actions = {r.get('action', '') for r in b}
    return {
        'added': sorted(b_actions - a_actions),
        'removed': sorted(a_actions - b_actions),
        'unchanged_count': len(a_actions & b_actions),
    }


def _diff_evidence(a: list[dict], b: list[dict]) -> dict:
    a_paths = {e.get('path', '') for e in a}
    b_paths = {e.get('path', '') for e in b}
    return {
        'added': sorted(b_paths - a_paths),
        'removed': sorted(a_paths - b_paths),
        'unchanged_count': len(a_paths & b_paths),
    }


def _diff_entities(a: list[dict], b: list[dict]) -> dict:
    a_ids = {e.get('id', '') for e in a}
    b_ids = {e.get('id', '') for e in b}
    return {
        'added': sorted(b_ids - a_ids),
        'removed': sorted(a_ids - b_ids),
        'unchanged_count': len(a_ids & b_ids),
    }


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data
    except Exception:
        return default
