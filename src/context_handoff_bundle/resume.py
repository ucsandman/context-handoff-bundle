"""Resume prompt composition for loading bundles into Claude Code."""
from __future__ import annotations

import json
from pathlib import Path


def compose_resume(bundle_dir: Path, mode: str = 'fast') -> str:
    """Compose a Claude-ready resume context from a bundle.

    Args:
        bundle_dir: Path to the bundle directory
        mode: 'fast' for compact orientation, 'deep' for detailed context

    Returns:
        A formatted string ready to inject into Claude Code context
    """
    bundle_dir = Path(bundle_dir).expanduser().resolve()

    parts: list[str] = []

    # --- Executive summary from summary.json ---
    summary = _load_json(bundle_dir / 'summary.json', {})
    title = summary.get('title', 'Untitled Handoff')
    exec_summary = summary.get('executive_summary', '')
    purpose = summary.get('purpose', '')

    parts.append(f'# Context Handoff: {title}')
    parts.append('')
    if purpose:
        parts.append(f'**Purpose:** {purpose}')
    if exec_summary:
        parts.append(f'\n**Summary:** {exec_summary}')

    # --- Scope ---
    scope = summary.get('scope', {})
    repos = scope.get('repos', [])
    if repos:
        parts.append(f'\n**Repos covered:** {", ".join(repos)}')

    # --- Top findings ---
    findings = summary.get('findings', [])
    if findings:
        parts.append('\n## Key Findings')
        limit = 5 if mode == 'fast' else len(findings)
        for f in findings[:limit]:
            fid = f.get('id', '')
            ftitle = f.get('summary', f.get('title', ''))
            confidence = f.get('confidence', 'unknown')
            parts.append(f'- **{fid}** {ftitle} (confidence: {confidence})')

    # --- Top recommendations ---
    recs = summary.get('recommendations', [])
    if recs:
        parts.append('\n## Recommendations')
        limit = 3 if mode == 'fast' else len(recs)
        for r in recs[:limit]:
            action = r.get('action', '')
            parts.append(f'- {action}')

    # --- Open questions ---
    questions = _load_json(bundle_dir / 'open_questions.json', [])
    if questions:
        parts.append('\n## Open Questions')
        limit = 5 if mode == 'fast' else len(questions)
        for q in questions[:limit]:
            qid = q.get('id', '')
            qtxt = q.get('question', '')
            blocking = ' **[BLOCKING]**' if q.get('blocking') else ''
            parts.append(f'- **{qid}** {qtxt}{blocking}')

    # --- Evidence to inspect first ---
    evidence = _load_json(bundle_dir / 'evidence_index.json', [])
    if evidence and mode == 'deep':
        parts.append('\n## Priority Evidence')
        for e in evidence[:8]:
            path = e.get('path', '')
            role = e.get('role', '')
            parts.append(f'- `{path}` ({role})')
    elif evidence:
        parts.append(f'\n**Evidence anchors:** {len(evidence)} source(s) indexed')

    # --- Resume instructions ---
    resume_instr = summary.get('resume_instructions', {})
    must_reverify = resume_instr.get('must_reverify', [])
    assumptions = resume_instr.get('assumptions_to_continue_from', [])

    if assumptions and mode == 'deep':
        parts.append('\n## Continue From These Assumptions')
        for a in assumptions[:5]:
            parts.append(f'- {a}')

    if must_reverify:
        parts.append('\n## Must Re-verify Before Trusting')
        for item in must_reverify[:5]:
            parts.append(f'- {item}')

    # --- Guidance ---
    parts.append('\n---')
    parts.append('**Do not re-research the above findings from scratch** unless evidence is stale or missing.')
    parts.append('Start from this context and verify incrementally.')

    return '\n'.join(parts)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data
    except Exception:
        return default
