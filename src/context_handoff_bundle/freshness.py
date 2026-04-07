"""Freshness checks for context handoff bundles."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path


def check_freshness(entry: dict, cwd: Path | None = None) -> dict:
    """Check if a stored bundle is still fresh relative to current repo state.

    Returns:
        {
            'fresh': bool,
            'warnings': [str, ...],
            'age_hours': float | None,
            'branch_match': bool | None,
            'commit_match': bool | None,
            'evidence_missing': [str, ...],
        }
    """
    warnings: list[str] = []
    result: dict = {
        'fresh': True,
        'warnings': warnings,
        'age_hours': None,
        'branch_match': None,
        'commit_match': None,
        'evidence_missing': [],
    }

    # --- Age check ---
    created_at = entry.get('created_at')
    if created_at:
        try:
            created = datetime.fromisoformat(created_at)
            age = datetime.now(timezone.utc) - created
            result['age_hours'] = round(age.total_seconds() / 3600, 1)
            if age.total_seconds() > 7 * 24 * 3600:
                warnings.append(f'Bundle is {result["age_hours"]:.0f} hours old (>7 days)')
                result['fresh'] = False
            elif age.total_seconds() > 24 * 3600:
                warnings.append(f'Bundle is {result["age_hours"]:.0f} hours old (>1 day)')
        except Exception:
            pass

    # --- Branch check ---
    saved_branch = entry.get('branch')
    if saved_branch:
        try:
            current_branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=str(cwd) if cwd else None,
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            result['branch_match'] = current_branch == saved_branch
            if not result['branch_match']:
                warnings.append(f'Branch changed: bundle was on "{saved_branch}", now on "{current_branch}"')
        except Exception:
            pass

    # --- Commit check ---
    saved_commit = entry.get('head_commit')
    if saved_commit:
        try:
            current_commit = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=str(cwd) if cwd else None,
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            result['commit_match'] = current_commit == saved_commit
            if not result['commit_match']:
                # Count commits between
                try:
                    count = subprocess.check_output(
                        ['git', 'rev-list', '--count', f'{saved_commit}..{current_commit}'],
                        cwd=str(cwd) if cwd else None,
                        stderr=subprocess.DEVNULL, text=True,
                    ).strip()
                    warnings.append(f'Repo advanced {count} commit(s) since bundle was saved')
                except Exception:
                    warnings.append('Repo HEAD has changed since bundle was saved')
        except Exception:
            pass

    # --- Evidence file existence check ---
    bundle_path = entry.get('path')
    if bundle_path:
        evidence_path = Path(bundle_path) / 'evidence_index.json'
        if evidence_path.exists():
            import json
            try:
                evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
                if isinstance(evidence, list):
                    for item in evidence:
                        path_str = item.get('path', '')
                        if path_str and not path_str.startswith('http'):
                            p = Path(path_str)
                            if not p.exists():
                                # Try relative to repo root
                                repo_root = entry.get('repo_root')
                                if repo_root:
                                    p_rel = Path(repo_root) / path_str
                                    if not p_rel.exists():
                                        result['evidence_missing'].append(path_str)
                                else:
                                    result['evidence_missing'].append(path_str)
            except Exception:
                pass

    if result['evidence_missing']:
        count = len(result['evidence_missing'])
        warnings.append(f'{count} evidence file(s) no longer exist')
        if count > 2:
            result['fresh'] = False

    if not result['fresh'] or warnings:
        result['fresh'] = result['fresh'] and len(warnings) <= 1

    return result
