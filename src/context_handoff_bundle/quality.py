"""Quality scoring for context handoff bundles.

Scores trustworthiness and decision usefulness, not prettiness.
Weighted to reward: evidence, honesty, specificity, actionable resume.
De-weighted: entity/relation richness (structure-for-structure's-sake).
"""
from __future__ import annotations

import json
from pathlib import Path


# Weights: higher = more important to the overall score.
# Trustworthiness dimensions get 2-3x weight of structural ones.
DIMENSION_WEIGHTS = {
    'evidence_coverage':     3.0,   # Can findings be traced to sources?
    'open_question_honesty': 2.5,   # Does the bundle admit what it doesn't know?
    'repo_specificity':      2.5,   # Is this about a real project, not generic filler?
    'findings_substance':    2.0,   # Are findings specific and actionable?
    'resume_usability':      2.0,   # Does the resume actually help the next session?
    'completeness':          1.0,   # Are the files present?
    'markdown_clarity':      1.0,   # Is the narrative readable?
    'entity_richness':       0.5,   # Nice to have, not critical
    'relation_richness':     0.3,   # Nice to have, not critical
}


def score_bundle(bundle_dir: Path) -> dict:
    """Score a bundle across quality dimensions.

    Returns:
        {
            'overall': 'strong' | 'acceptable' | 'weak',
            'score': float (0-1),
            'dimensions': {dim: float, ...},
            'warnings': [str, ...],
            'pass': bool,
        }
    """
    bundle_dir = Path(bundle_dir).expanduser().resolve()
    warnings: list[str] = []
    dim_scores: dict[str, float] = {}

    # --- Completeness ---
    required = [
        'CONTEXT_HANDOFF.md', 'summary.json', 'entities.json',
        'relations.json', 'evidence_index.json', 'open_questions.json',
        'resume_prompt.txt', 'bundle_metadata.json',
    ]
    non_empty = 0
    for f in required:
        p = bundle_dir / f
        if p.exists() and len(p.read_text(encoding='utf-8').strip()) > 20:
            non_empty += 1
    dim_scores['completeness'] = non_empty / len(required)
    missing = len(required) - sum(1 for f in required if (bundle_dir / f).exists())
    if missing:
        warnings.append(f'Missing {missing} required file(s)')

    # --- Evidence coverage (high weight) ---
    evidence = _load_json_list(bundle_dir / 'evidence_index.json')
    ev_count = len(evidence)
    if ev_count == 0:
        dim_scores['evidence_coverage'] = 0.0
        warnings.append('No evidence anchors - findings are unsupported')
    elif ev_count < 3:
        dim_scores['evidence_coverage'] = 0.3
        warnings.append('Very few evidence anchors')
    elif ev_count < 6:
        dim_scores['evidence_coverage'] = 0.6
    else:
        dim_scores['evidence_coverage'] = min(1.0, ev_count / 10)

    # --- Findings substance (new: are findings specific?) ---
    summary = _load_json_dict(bundle_dir / 'summary.json')
    findings = summary.get('findings', [])
    if not findings:
        dim_scores['findings_substance'] = 0.0
        warnings.append('No findings - bundle has nothing to hand off')
    else:
        # Score based on count and average length (longer = more specific)
        avg_len = sum(len(f.get('summary', f.get('title', ''))) for f in findings) / len(findings)
        count_score = min(1.0, len(findings) / 6)
        length_score = min(1.0, avg_len / 80)
        # Penalize if all findings are generic/short
        generic_count = sum(1 for f in findings if _is_generic(f.get('summary', '')))
        generic_penalty = generic_count / len(findings) * 0.4
        dim_scores['findings_substance'] = max(0.0, (count_score * 0.4 + length_score * 0.6) - generic_penalty)

    # --- Open question honesty (high weight) ---
    questions = _load_json_list(bundle_dir / 'open_questions.json')
    q_count = len(questions)
    if q_count == 0:
        dim_scores['open_question_honesty'] = 0.2
        warnings.append('No open questions - suspiciously certain')
    elif q_count < 2:
        dim_scores['open_question_honesty'] = 0.5
    else:
        dim_scores['open_question_honesty'] = min(1.0, 0.5 + q_count * 0.1)

    # --- Resume usability ---
    resume_path = bundle_dir / 'resume_prompt.txt'
    if resume_path.exists():
        resume_text = resume_path.read_text(encoding='utf-8').strip()
        resume_len = len(resume_text)
        if resume_len < 50:
            dim_scores['resume_usability'] = 0.2
            warnings.append('Resume prompt is too short to be useful')
        elif resume_len < 200:
            dim_scores['resume_usability'] = 0.5
        else:
            dim_scores['resume_usability'] = min(1.0, 0.6 + resume_len / 2000)
    else:
        dim_scores['resume_usability'] = 0.0
        warnings.append('No resume prompt file')

    # --- Markdown clarity ---
    md_path = bundle_dir / 'CONTEXT_HANDOFF.md'
    if md_path.exists():
        md_text = md_path.read_text(encoding='utf-8')
        md_len = len(md_text)
        heading_count = md_text.count('\n## ')
        if md_len < 200:
            dim_scores['markdown_clarity'] = 0.2
            warnings.append('Handoff markdown is too thin')
        elif heading_count < 3:
            dim_scores['markdown_clarity'] = 0.4
        elif md_len < 800:
            dim_scores['markdown_clarity'] = 0.6
        else:
            dim_scores['markdown_clarity'] = min(1.0, 0.7 + heading_count * 0.03)
    else:
        dim_scores['markdown_clarity'] = 0.0

    # --- Repo specificity (high weight) ---
    scope = summary.get('scope', {})
    repos = scope.get('repos', [])
    inputs = scope.get('inputs', [])
    specificity = 0.0
    if repos:
        specificity += min(0.4, len(repos) * 0.15)
    if inputs:
        specificity += min(0.2, len(inputs) * 0.1)
    purpose = summary.get('purpose', '')
    if purpose and len(purpose) > 20 and 'untitled' not in purpose.lower():
        specificity += 0.2
    # Bonus for specific findings (not "needs refinement")
    specific_findings = sum(1 for f in findings if not _is_generic(f.get('summary', '')))
    if specific_findings:
        specificity += min(0.2, specific_findings * 0.04)
    dim_scores['repo_specificity'] = min(1.0, specificity)
    if specificity < 0.3:
        warnings.append('Bundle is too generic - lacks repo-specific detail')

    # --- Entity richness (low weight) ---
    entities = _load_json_list(bundle_dir / 'entities.json')
    ent_count = len(entities)
    if ent_count == 0:
        dim_scores['entity_richness'] = 0.0
    elif ent_count < 3:
        dim_scores['entity_richness'] = 0.4
    else:
        dim_scores['entity_richness'] = min(1.0, ent_count / 10)

    # --- Relation richness (low weight) ---
    relations = _load_json_list(bundle_dir / 'relations.json')
    rel_count = len(relations)
    if rel_count == 0:
        dim_scores['relation_richness'] = 0.0
    else:
        dim_scores['relation_richness'] = min(1.0, rel_count / 8)

    # --- Weighted overall ---
    total_weight = sum(DIMENSION_WEIGHTS.get(k, 1.0) for k in dim_scores)
    weighted_sum = sum(v * DIMENSION_WEIGHTS.get(k, 1.0) for k, v in dim_scores.items())
    avg = weighted_sum / total_weight if total_weight > 0 else 0.0

    if avg >= 0.6:
        overall = 'strong'
    elif avg >= 0.35:
        overall = 'acceptable'
    else:
        overall = 'weak'

    return {
        'overall': overall,
        'score': round(avg, 3),
        'dimensions': {k: round(v, 3) for k, v in dim_scores.items()},
        'warnings': warnings,
        'pass': avg >= 0.3,
    }


def _is_generic(text: str) -> bool:
    """Check if a finding is generic filler rather than specific insight."""
    generic_markers = [
        'needs refinement', 'unknown', 'starter handoff',
        'needs direct validation', 'needs refinement from source',
    ]
    lower = text.lower()
    return any(marker in lower for marker in generic_markers) or len(text) < 15


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
