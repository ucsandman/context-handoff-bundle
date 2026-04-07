"""Resume prompt composition for loading bundles into Claude Code.

The resume output is operational, not archival. It tells the next session:
- State: what's true right now
- Pressure: what matters most
- Drift: what changed since save
- Open first: which files to look at
- Must reverify: what not to trust blindly
- Next moves: what to do first
"""
from __future__ import annotations

import json
from pathlib import Path


def compose_resume(
    bundle_dir: Path,
    mode: str = 'fast',
    freshness: dict | None = None,
    drift: dict | None = None,
) -> str:
    """Compose a Claude-ready resume context from a bundle.

    Args:
        bundle_dir: Path to the bundle directory
        mode: 'fast' for compact orientation, 'deep' for detailed context
        freshness: Optional freshness check result (legacy, used if no drift)
        drift: Optional drift analysis result from drift.analyze_drift()

    Returns:
        A formatted string ready to inject into Claude Code context
    """
    bundle_dir = Path(bundle_dir).expanduser().resolve()

    parts: list[str] = []
    summary = _load_json(bundle_dir / 'summary.json', {})
    title = summary.get('title', 'Untitled Handoff')
    purpose = summary.get('purpose', '')

    parts.append(f'# Resume: {title}')
    parts.append('')

    # ── STATE: what's true right now ──
    parts.append('## State')
    if purpose:
        parts.append(f'- **What this is:** {purpose}')
    scope = summary.get('scope', {})
    repos = scope.get('repos', [])
    if repos:
        parts.append(f'- **Repos:** {", ".join(repos)}')
    exec_summary = summary.get('executive_summary', '')
    if exec_summary:
        parts.append(f'- **Summary:** {exec_summary}')

    # Include trustworthy findings as state, with drift-aware confidence
    findings = summary.get('findings', [])
    at_risk_ids = set()
    if drift and drift.get('findings_at_risk'):
        at_risk_ids = {f['id'] for f in drift['findings_at_risk']}

    if findings:
        parts.append('')
        parts.append('**What was established:**')
        limit = 8 if mode == 'deep' else 5
        for f in findings[:limit]:
            text = f.get('summary', f.get('title', ''))
            fid = f.get('id', '')
            confidence = f.get('confidence', 'medium')
            if fid in at_risk_ids:
                parts.append(f'- ~~{text}~~ **[STALE - evidence changed]**')
            elif confidence == 'high':
                parts.append(f'- {text}')
            else:
                parts.append(f'- {text} *(confidence: {confidence})*')

    # ── CONFIDENCE SUMMARY ──
    confidence_parts = _compute_section_confidence(summary, findings, at_risk_ids, drift)
    if confidence_parts:
        parts.append('')
        parts.append('**Section confidence:**')
        for label, level in confidence_parts:
            parts.append(f'- {label}: **{level}**')

    # ── DRIFT: what changed since save ──
    if drift and drift.get('has_drift'):
        from .drift import format_drift_report
        drift_text = format_drift_report(drift)
        if drift_text:
            parts.append('')
            parts.append(drift_text)
    elif freshness and freshness.get('warnings'):
        parts.append('')
        parts.append('## Drift')
        parts.append('**The repo has changed since this handoff was saved:**')
        for w in freshness['warnings']:
            parts.append(f'- {w}')
        if not freshness.get('fresh', True):
            parts.append('- **This handoff may be stale. Verify claims before acting on them.**')

    # ── PRESSURE: what matters most ──
    recs = summary.get('recommendations', [])
    questions = _load_json(bundle_dir / 'open_questions.json', [])
    blocking = [q for q in questions if q.get('blocking')]

    if recs or blocking:
        parts.append('')
        parts.append('## Pressure')
        if blocking:
            for q in blocking:
                parts.append(f'- **BLOCKING:** {q.get("question", "")}')
        for r in recs[:3]:
            action = r.get('action', '')
            parts.append(f'- {action}')

    # ── OPEN FIRST: which files to look at ──
    evidence = _load_json(bundle_dir / 'evidence_index.json', [])
    resume_instr = summary.get('resume_instructions', {})
    read_first = resume_instr.get('read_first', [])

    if evidence or read_first:
        parts.append('')
        parts.append('## Open First')
        if read_first and mode == 'deep':
            for f in read_first:
                parts.append(f'- `{f}`')
        # Show evidence anchors -- these are the actual repo files
        shown = set()
        for e in evidence[:6]:
            path = e.get('path', '')
            if path and path not in shown:
                role = e.get('role', '')
                parts.append(f'- `{path}` ({role})' if role else f'- `{path}`')
                shown.add(path)

    # ── MUST REVERIFY: what not to trust blindly ──
    must_reverify = resume_instr.get('must_reverify', [])
    stale_evidence = []
    if freshness:
        stale_evidence = freshness.get('evidence_missing', [])

    if must_reverify or stale_evidence:
        parts.append('')
        parts.append('## Must Reverify')
        for item in must_reverify[:5]:
            parts.append(f'- {item}')
        for path in stale_evidence[:3]:
            parts.append(f'- Evidence file gone: `{path}`')

    # ── OPEN QUESTIONS ──
    non_blocking = [q for q in questions if not q.get('blocking')]
    if non_blocking:
        parts.append('')
        parts.append('## Open Questions')
        limit = 5 if mode == 'fast' else len(non_blocking)
        for q in non_blocking[:limit]:
            qid = q.get('id', '')
            qtxt = q.get('question', '')
            parts.append(f'- **{qid}** {qtxt}')

    # ── NEXT MOVES ──
    if recs:
        parts.append('')
        parts.append('## Next Moves')
        for i, r in enumerate(recs[:3], 1):
            action = r.get('action', '')
            parts.append(f'{i}. {action}')

    # ── GUIDANCE ──
    parts.append('')
    parts.append('---')
    parts.append('Trust established findings unless drift warnings say otherwise.')
    parts.append('Do not re-research from scratch. Verify incrementally.')

    return '\n'.join(parts)


def _compute_section_confidence(
    summary: dict,
    findings: list[dict],
    at_risk_ids: set,
    drift: dict | None,
) -> list[tuple[str, str]]:
    """Compute per-section confidence ratings."""
    sections: list[tuple[str, str]] = []

    # Findings confidence
    if findings:
        stale_count = sum(1 for f in findings if f.get('id', '') in at_risk_ids)
        high_count = sum(1 for f in findings if f.get('confidence') == 'high')
        total = len(findings)
        if stale_count > total / 2:
            sections.append(('Findings', 'STALE'))
        elif stale_count > 0:
            sections.append(('Findings', f'mixed ({stale_count}/{total} at risk)'))
        elif high_count > total / 2:
            sections.append(('Findings', 'strong'))
        else:
            sections.append(('Findings', 'medium'))

    # Evidence confidence
    if drift and drift.get('evidence_status'):
        ok = sum(1 for e in drift['evidence_status'] if e['status'] == 'ok')
        total = len(drift['evidence_status'])
        if total > 0:
            if ok == total:
                sections.append(('Evidence', 'strong'))
            elif ok > total / 2:
                sections.append(('Evidence', f'partial ({total - ok}/{total} affected)'))
            else:
                sections.append(('Evidence', 'WEAK'))

    # Recommendations confidence
    recs = summary.get('recommendations', [])
    if recs:
        if drift and drift.get('recommendations_at_risk'):
            sections.append(('Recommendations', 'STALE'))
        elif drift and drift.get('has_drift') and drift.get('commit_count', 0) > 5:
            sections.append(('Recommendations', 'uncertain'))
        else:
            sections.append(('Recommendations', 'medium'))

    # Overall drift
    if drift and drift.get('severity') == 'high':
        sections.append(('Overall', 'LOW - significant drift'))
    elif drift and drift.get('severity') == 'medium':
        sections.append(('Overall', 'MEDIUM - some drift'))

    return sections


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data
    except Exception:
        return default
