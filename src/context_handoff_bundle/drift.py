"""Drift intelligence: what changed since the bundle was saved, and what it means.

This is the signature feature. Not just "repo drifted" -- show exactly:
- which files changed
- which evidence anchors are affected
- which findings might be invalidated
- which recommendations may be unsafe
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


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
            'evidence_status': [{'path': str, 'status': 'ok'|'changed'|'deleted'}, ...],
            'findings_at_risk': [{'id': str, 'title': str, 'reason': str}, ...],
            'recommendations_at_risk': [{'action': str, 'reason': str}, ...],
            'branch_drift': str | None,
            'commit_count': int,
            'age_hours': float | None,
        }
    """
    cwd = cwd or Path.cwd()
    result: dict = {
        'has_drift': False,
        'severity': 'none',
        'summary': 'No drift detected.',
        'files_changed': [],
        'files_added': [],
        'files_deleted': [],
        'evidence_status': [],
        'findings_at_risk': [],
        'recommendations_at_risk': [],
        'branch_drift': None,
        'commit_count': 0,
        'age_hours': None,
    }

    saved_commit = entry.get('head_commit', '')
    saved_branch = entry.get('branch', '')
    bundle_path = Path(entry.get('path', ''))

    # ── Age ──
    from .freshness import check_freshness
    freshness = check_freshness(entry, cwd)
    result['age_hours'] = freshness.get('age_hours')

    # ── Branch drift ──
    current_branch = _git(cwd, 'rev-parse', '--abbrev-ref', 'HEAD')
    if saved_branch and current_branch and saved_branch != current_branch:
        result['branch_drift'] = f'Saved on "{saved_branch}", now on "{current_branch}"'
        result['has_drift'] = True

    # ── File-level drift since saved commit ──
    if saved_commit:
        current_commit = _git(cwd, 'rev-parse', 'HEAD')
        if current_commit and current_commit != saved_commit:
            result['has_drift'] = True

            # Count commits
            count = _git(cwd, 'rev-list', '--count', f'{saved_commit}..{current_commit}')
            result['commit_count'] = int(count) if count.isdigit() else 0

            # Get changed files with status
            diff_output = _git(cwd, 'diff', '--name-status', saved_commit, current_commit)
            for line in diff_output.splitlines():
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    status, filepath = parts[0].strip(), parts[1].strip()
                    if status.startswith('A'):
                        result['files_added'].append(filepath)
                    elif status.startswith('D'):
                        result['files_deleted'].append(filepath)
                    elif status.startswith('M') or status.startswith('R'):
                        result['files_changed'].append(filepath)

        # Also include uncommitted changes
        dirty = _git(cwd, 'diff', '--name-only')
        staged = _git(cwd, 'diff', '--name-only', '--cached')
        for f in (dirty + '\n' + staged).splitlines():
            f = f.strip()
            if f and f not in result['files_changed']:
                result['files_changed'].append(f)
                result['has_drift'] = True

    # ── Evidence anchor status ──
    if bundle_path.exists():
        evidence = _load_json_list(bundle_path / 'evidence_index.json')
        changed_files_set = set(result['files_changed'] + result['files_deleted'])

        for item in evidence:
            path_str = item.get('path', '')
            if not path_str:
                continue

            status = 'ok'
            # Check if file was deleted
            if not Path(path_str).exists():
                # Try repo-relative
                repo_root = entry.get('repo_root', '')
                if repo_root and not (Path(repo_root) / path_str).exists():
                    status = 'deleted'
                elif not repo_root:
                    status = 'deleted'

            # Check if file was modified since save
            if status == 'ok':
                # Normalize for comparison
                for changed in changed_files_set:
                    if path_str.endswith(changed) or changed.endswith(path_str.split('/')[-1]):
                        status = 'changed'
                        break

            result['evidence_status'].append({
                'path': path_str,
                'status': status,
                'role': item.get('role', ''),
            })

    # ── Which findings are at risk ──
    if bundle_path.exists() and result['has_drift']:
        summary_data = _load_json_dict(bundle_path / 'summary.json')
        findings = summary_data.get('findings', [])
        changed_evidence = {e['path'] for e in result['evidence_status'] if e['status'] != 'ok'}

        for f in findings:
            finding_evidence = f.get('evidence', [])
            # Check if any evidence for this finding has drifted
            for ev in finding_evidence:
                if any(ev.endswith(ce.split('/')[-1]) or ce.endswith(ev.split('/')[-1])
                       for ce in changed_evidence):
                    result['findings_at_risk'].append({
                        'id': f.get('id', ''),
                        'title': f.get('title', f.get('summary', '')[:60]),
                        'reason': f'Evidence file changed or deleted: {ev}',
                    })
                    break

        # Also flag findings if their related area got heavy changes
        if result['commit_count'] > 10:
            for f in findings:
                fid = f.get('id', '')
                if not any(r['id'] == fid for r in result['findings_at_risk']):
                    result['findings_at_risk'].append({
                        'id': fid,
                        'title': f.get('title', f.get('summary', '')[:60]),
                        'reason': f'{result["commit_count"]} commits since save -- finding may be outdated',
                    })

        # Recommendations at risk
        recs = summary_data.get('recommendations', [])
        if result['commit_count'] > 5 or len(changed_evidence) > 2:
            for r in recs:
                result['recommendations_at_risk'].append({
                    'action': r.get('action', ''),
                    'reason': 'Repo changed significantly since this was recommended',
                })

    # ── Severity ──
    risk_signals = (
        len(result['findings_at_risk'])
        + len(result['recommendations_at_risk'])
        + len(result['files_deleted'])
        + (1 if result['branch_drift'] else 0)
    )
    if not result['has_drift']:
        result['severity'] = 'none'
    elif risk_signals == 0 and result['commit_count'] <= 3:
        result['severity'] = 'low'
    elif risk_signals <= 3 and result['commit_count'] <= 10:
        result['severity'] = 'medium'
    else:
        result['severity'] = 'high'

    # ── Summary ──
    result['summary'] = _build_summary(result)

    return result


def format_drift_report(drift: dict) -> str:
    """Format drift analysis into a readable report for the resume."""
    if not drift['has_drift']:
        return ''

    parts: list[str] = []
    parts.append('## Drift')
    parts.append(f'**Severity: {drift["severity"].upper()}** -- {drift["summary"]}')

    if drift['branch_drift']:
        parts.append(f'- {drift["branch_drift"]}')

    if drift['commit_count']:
        parts.append(f'- {drift["commit_count"]} commit(s) since save')

    if drift['files_changed']:
        parts.append(f'\n**Files changed ({len(drift["files_changed"])}):**')
        for f in drift['files_changed'][:10]:
            parts.append(f'- `{f}`')
        if len(drift['files_changed']) > 10:
            parts.append(f'- ...and {len(drift["files_changed"]) - 10} more')

    if drift['files_deleted']:
        parts.append(f'\n**Files deleted ({len(drift["files_deleted"])}):**')
        for f in drift['files_deleted'][:5]:
            parts.append(f'- `{f}` DELETED')

    if drift['files_added']:
        parts.append(f'\n**New files ({len(drift["files_added"])}):**')
        for f in drift['files_added'][:5]:
            parts.append(f'- `{f}` NEW')

    # Evidence impact
    affected_evidence = [e for e in drift['evidence_status'] if e['status'] != 'ok']
    if affected_evidence:
        parts.append('\n**Evidence anchors affected:**')
        for e in affected_evidence:
            icon = 'CHANGED' if e['status'] == 'changed' else 'GONE'
            parts.append(f'- `{e["path"]}` {icon}')

    # Findings at risk
    if drift['findings_at_risk']:
        parts.append('\n**Findings that may be stale:**')
        for f in drift['findings_at_risk']:
            parts.append(f'- **{f["id"]}** {f["title"]} -- {f["reason"]}')

    # Recommendations at risk
    if drift['recommendations_at_risk']:
        parts.append('\n**Recommendations that may be unsafe:**')
        for r in drift['recommendations_at_risk']:
            parts.append(f'- {r["action"]} -- {r["reason"]}')

    return '\n'.join(parts)


def _build_summary(drift: dict) -> str:
    parts: list[str] = []
    if drift['commit_count']:
        parts.append(f'{drift["commit_count"]} commits')
    fc = len(drift['files_changed'])
    fa = len(drift['files_added'])
    fd = len(drift['files_deleted'])
    if fc + fa + fd > 0:
        parts.append(f'{fc + fa + fd} files touched')
    at_risk = len(drift['findings_at_risk'])
    if at_risk:
        parts.append(f'{at_risk} finding(s) at risk')
    if drift['branch_drift']:
        parts.append('branch changed')
    if not parts:
        return 'Minor drift detected.'
    return ', '.join(parts) + ' since save.'


def _git(cwd: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ['git', *args], cwd=str(cwd),
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except Exception:
        return ''


def _load_json_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _load_json_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
