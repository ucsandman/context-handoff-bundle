"""Quality scoring for context handoff bundles."""
from __future__ import annotations

import json
from pathlib import Path


DIMENSIONS = [
    'completeness',
    'evidence_coverage',
    'entity_richness',
    'relation_richness',
    'open_question_honesty',
    'resume_usability',
    'markdown_clarity',
    'repo_specificity',
]


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

    # --- Completeness: are all required files present with real content? ---
    required = [
        'CONTEXT_HANDOFF.md', 'summary.json', 'entities.json',
        'relations.json', 'evidence_index.json', 'open_questions.json',
        'resume_prompt.txt', 'bundle_metadata.json',
    ]
    present = sum(1 for f in required if (bundle_dir / f).exists())
    non_empty = 0
    for f in required:
        p = bundle_dir / f
        if p.exists() and len(p.read_text(encoding='utf-8').strip()) > 20:
            non_empty += 1
    dim_scores['completeness'] = non_empty / len(required)
    if present < len(required):
        warnings.append(f'Missing {len(required) - present} required file(s)')

    # --- Evidence coverage ---
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

    # --- Entity richness ---
    entities = _load_json_list(bundle_dir / 'entities.json')
    ent_count = len(entities)
    if ent_count == 0:
        dim_scores['entity_richness'] = 0.0
        warnings.append('No entities extracted')
    elif ent_count < 3:
        dim_scores['entity_richness'] = 0.3
        warnings.append('Very few entities for a meaningful handoff')
    elif ent_count < 8:
        dim_scores['entity_richness'] = 0.6
    else:
        dim_scores['entity_richness'] = min(1.0, ent_count / 15)

    # --- Relation richness ---
    relations = _load_json_list(bundle_dir / 'relations.json')
    rel_count = len(relations)
    if rel_count == 0:
        dim_scores['relation_richness'] = 0.0
        warnings.append('No relations extracted')
    elif rel_count < 3:
        dim_scores['relation_richness'] = 0.3
    else:
        dim_scores['relation_richness'] = min(1.0, rel_count / 10)

    # --- Open question honesty ---
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
            warnings.append('Handoff markdown has few sections')
        elif md_len < 800:
            dim_scores['markdown_clarity'] = 0.6
        else:
            dim_scores['markdown_clarity'] = min(1.0, 0.7 + heading_count * 0.03)
    else:
        dim_scores['markdown_clarity'] = 0.0

    # --- Repo specificity ---
    summary = _load_json_dict(bundle_dir / 'summary.json')
    scope = summary.get('scope', {})
    repos = scope.get('repos', [])
    inputs = scope.get('inputs', [])
    specificity = 0.0
    if repos:
        specificity += min(0.5, len(repos) * 0.15)
    if inputs:
        specificity += min(0.3, len(inputs) * 0.1)
    if summary.get('purpose') and len(summary.get('purpose', '')) > 20:
        specificity += 0.2
    dim_scores['repo_specificity'] = min(1.0, specificity)
    if specificity < 0.3:
        warnings.append('Bundle is too generic - lacks repo-specific detail')

    # --- Overall ---
    if dim_scores:
        avg = sum(dim_scores.values()) / len(dim_scores)
    else:
        avg = 0.0

    if avg >= 0.65:
        overall = 'strong'
    elif avg >= 0.4:
        overall = 'acceptable'
    else:
        overall = 'weak'

    return {
        'overall': overall,
        'score': round(avg, 3),
        'dimensions': {k: round(v, 3) for k, v in dim_scores.items()},
        'warnings': warnings,
        'pass': avg >= 0.35,
    }


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
