from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover - optional dependency for early prototype
    jsonschema = None

REQUIRED_FILES = [
    'CONTEXT_HANDOFF.md',
    'summary.json',
    'entities.json',
    'relations.json',
    'evidence_index.json',
    'open_questions.json',
    'resume_prompt.txt',
    'bundle_metadata.json',
]

TEMPLATE_MAP = {
    'CONTEXT_HANDOFF.md': 'CONTEXT_HANDOFF.template.md',
    'summary.json': 'summary.template.json',
    'entities.json': 'entities.template.json',
    'relations.json': 'relations.template.json',
    'evidence_index.json': 'evidence_index.template.json',
    'open_questions.json': 'open_questions.template.json',
    'resume_prompt.txt': 'resume_prompt.template.txt',
    'bundle_metadata.json': 'bundle_metadata.template.json',
}

SCHEMA_MAP = {
    'summary.json': 'summary.schema.json',
    'entities.json': 'entities.schema.json',
    'relations.json': 'relations.schema.json',
    'evidence_index.json': 'evidence_index.schema.json',
    'open_questions.json': 'open_questions.schema.json',
    'bundle_metadata.json': 'bundle_metadata.schema.json',
}

SECTION_KEYS = {
    'scope': 'scope',
    'projects mentioned': 'projects',
    'findings': 'findings',
    'opportunities': 'opportunities',
    'open questions': 'open_questions',
    'evidence anchors': 'evidence_anchors',
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def templates_dir() -> Path:
    return project_root() / 'templates'


def schemas_dir() -> Path:
    return project_root() / 'schemas'


def slugify(text: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9]+', '-', text.strip().lower()).strip('-')
    return value or 'untitled-handoff'


def write_from_template(bundle_dir: Path, filename: str, force: bool = False) -> None:
    target = bundle_dir / filename
    if target.exists() and not force:
        return
    template_name = TEMPLATE_MAP[filename]
    content = (templates_dir() / template_name).read_text(encoding='utf-8')
    target.write_text(content, encoding='utf-8')


def ensure_bundle_dir(output_root: str, slug: str) -> Path:
    root = Path(output_root).expanduser().resolve()
    bundle_dir = root / f"{date.today().isoformat()}-{slug}"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    return bundle_dir


def parse_bullets(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith('- '):
            items.append(stripped[2:].strip())
    return items


def parse_notes(text: str) -> dict:
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []

    for line in text.splitlines():
        if line.startswith('## '):
            if current is not None:
                sections[current] = '\n'.join(buffer).strip()
            heading = line[3:].strip().lower()
            current = SECTION_KEYS.get(heading)
            buffer = []
        else:
            if current is not None:
                buffer.append(line)

    if current is not None:
        sections[current] = '\n'.join(buffer).strip()

    parsed = {
        'scope': sections.get('scope', ''),
        'projects': parse_bullets(sections.get('projects', '')),
        'findings': parse_bullets(sections.get('findings', '')),
        'opportunities': parse_bullets(sections.get('opportunities', '')),
        'open_questions': parse_bullets(sections.get('open_questions', '')),
        'evidence_anchors': parse_bullets(sections.get('evidence_anchors', '')),
    }
    return parsed


def build_entities(projects: list[str], evidence: list[str]) -> list[dict]:
    entities: list[dict] = []
    for project in projects:
        entities.append({
            'id': f"project_{slugify(project)}",
            'type': 'project',
            'name': project,
            'description': f"Project identified in the handoff input: {project}",
            'status': 'active',
            'confidence': 'medium',
            'tags': ['project'],
            'sources': evidence[:3],
            'notes': '',
        })
    return entities


def build_relations(projects: list[str], findings: list[str], evidence: list[str]) -> list[dict]:
    relations: list[dict] = []
    if len(projects) >= 2 and findings:
        relations.append({
            'source': f"project_{slugify(projects[0])}",
            'target': f"project_{slugify(projects[1])}",
            'relation': 'candidate_for_integration_with',
            'confidence': 'medium',
            'why': findings[0],
            'sources': evidence[:2],
        })
    return relations


def build_evidence_index(evidence: list[str]) -> list[dict]:
    return [
        {
            'path': item,
            'role': 'reference',
            'used_for': ['session finding support'],
            'confidence': 'medium',
            'review_status': 'referenced',
        }
        for item in evidence
    ]


def build_open_questions(questions: list[str]) -> list[dict]:
    items: list[dict] = []
    for idx, question in enumerate(questions, start=1):
        items.append({
            'id': f'Q{idx}',
            'question': question,
            'why_it_matters': 'Captured from session notes as unresolved uncertainty.',
            'how_to_verify': 'Review source materials and validate against current repo state.',
            'blocking': False,
        })
    return items


def build_bundle_metadata(mode: str, source_inputs: list[str], notes: str = '') -> dict:
    return {
        'bundle_version': '0.1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'generator': {
            'tool': 'context-handoff-bundle',
            'mode': mode,
        },
        'source_inputs': source_inputs,
        'notes': notes,
    }


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def render_markdown(title: str, parsed: dict) -> str:
    findings_md = '\n'.join([f"### Finding {i}\n- What is true: {item}\n- Why it matters: Preserved from source notes.\n- Confidence: medium\n- Evidence anchors: {', '.join(parsed['evidence_anchors'][:2]) or 'none listed'}\n" for i, item in enumerate(parsed['findings'], start=1)])
    projects_md = '\n'.join([f"### {project}\n- Purpose: Needs refinement from source materials.\n- Main subsystems: Unknown from current notes.\n- Current maturity / state: Active or relevant enough to be included in the session.\n- Strengths: Needs refinement.\n- Weaknesses: Needs refinement.\n- Important files / directories: Needs refinement.\n" for project in parsed['projects']])
    opportunities_md = '\n'.join([f"- {item}" for item in parsed['opportunities']])
    questions_md = '\n'.join([f"- {item}" for item in parsed['open_questions']])
    evidence_md = '\n'.join([f"- {item}" for item in parsed['evidence_anchors']])

    return f"# Context Handoff: {title}\n\n## 1. Scope\n- Date: {date.today().isoformat()}\n- Model used: unknown\n- Session purpose: {parsed['scope'] or 'Not explicitly captured'}\n- Repositories / folders reviewed: Needs refinement\n- Primary inputs reviewed: source notes file\n- Important things intentionally not reviewed: unknown\n- Artifacts created during the session: this bundle\n\n## 2. Executive Summary\nThis is a starter handoff generated from structured session notes. It preserves the main themes, findings, and unresolved questions, but should be refined with direct source review for higher confidence.\n\n## 3. Core Findings\n{findings_md or 'No findings captured.'}\n\n## 4. Project / Repo Summaries\n{projects_md or 'No projects captured.'}\n\n## 5. Shared Patterns and Overlap\n- Repeated abstractions: agent capability plus oversight plus durable artifacts\n- Reused components: Needs refinement\n- Duplicate capabilities: Needs refinement\n- Architectural similarities: Needs refinement\n- Architectural conflicts: Needs refinement\n\n## 6. Opportunities\n### Consolidation opportunities\n{opportunities_md or '- None captured'}\n\n### Integration opportunities\n- Needs refinement\n\n### New product opportunities\n- Needs refinement\n\n### Cleanup / retirement opportunities\n- Needs refinement\n\n## 7. Decisions / Recommendations\n- Recommended next moves: Refine this starter bundle against direct source materials.\n- Sequencing: Confirm project boundaries first, then refine overlaps, then recommendations.\n- Preconditions: More direct evidence review.\n- Risks: Current output may over-compress or under-specify real architecture.\n\n## 8. Open Questions\n{questions_md or '- None captured'}\n\n## 9. Evidence Anchors\n{evidence_md or '- None captured'}\n\n## 10. Resume Instructions\n1. Read this handoff first\n2. Review summary.json, entities.json, relations.json, and evidence_index.json\n3. Re-open the evidence anchors before making consequential decisions\n4. Refine project summaries using direct repo/docs inspection\n"


def validate_json_file(bundle: Path, filename: str) -> dict:
    path = bundle / filename
    result = {
        'file': filename,
        'exists': path.exists(),
        'json_valid': False,
        'schema_valid': None,
        'error': None,
    }
    if not path.exists():
        result['error'] = 'missing file'
        return result

    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        result['json_valid'] = True
    except Exception as exc:
        result['error'] = f'invalid json: {exc}'
        return result

    schema_name = SCHEMA_MAP.get(filename)
    if schema_name and jsonschema is not None:
        try:
            schema = json.loads((schemas_dir() / schema_name).read_text(encoding='utf-8'))
            jsonschema.validate(data, schema)
            result['schema_valid'] = True
        except Exception as exc:
            result['schema_valid'] = False
            result['error'] = f'schema validation failed: {exc}'
    elif schema_name:
        result['schema_valid'] = None
        result['error'] = 'jsonschema not installed; schema validation skipped'

    return result


def cmd_init(args: argparse.Namespace) -> int:
    slug = args.slug or 'untitled-handoff'
    bundle_dir = ensure_bundle_dir(args.output, slug)

    created_files: list[str] = []
    for name in REQUIRED_FILES:
        before = (bundle_dir / name).exists()
        write_from_template(bundle_dir, name, force=args.force)
        after = (bundle_dir / name).exists()
        if after and (args.force or not before):
            created_files.append(name)

    metadata = build_bundle_metadata(mode='init', source_inputs=[])
    write_json(bundle_dir / 'bundle_metadata.json', metadata)

    if args.with_graph:
        graph_path = bundle_dir / 'graph.json'
        if args.force or not graph_path.exists():
            graph_path.write_text('[]\n', encoding='utf-8')
            created_files.append('graph.json')

    print(json.dumps({
        'bundle_dir': str(bundle_dir),
        'created_files': created_files,
    }, indent=2))
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    notes_path = Path(args.notes).expanduser().resolve()
    text = notes_path.read_text(encoding='utf-8')
    parsed = parse_notes(text)
    title = args.title or notes_path.stem.replace('-', ' ').replace('_', ' ').title()
    slug = args.slug or slugify(title)
    bundle_dir = ensure_bundle_dir(args.output, slug)

    entities = build_entities(parsed['projects'], parsed['evidence_anchors'])
    relations = build_relations(parsed['projects'], parsed['findings'], parsed['evidence_anchors'])
    evidence_index = build_evidence_index(parsed['evidence_anchors'])
    open_questions = build_open_questions(parsed['open_questions'])

    summary = {
        'title': title,
        'date': date.today().isoformat(),
        'generated_by': {
            'tool': 'context-handoff-bundle',
            'model': 'starter-generator',
        },
        'purpose': parsed['scope'] or 'Generated from source notes',
        'scope': {
            'repos': parsed['projects'],
            'folders': [],
            'inputs': [str(notes_path)],
            'excluded': [],
            'artifacts_created': [
                'CONTEXT_HANDOFF.md',
                'summary.json',
                'entities.json',
                'relations.json',
                'evidence_index.json',
                'open_questions.json',
                'resume_prompt.txt',
                'bundle_metadata.json',
            ],
        },
        'executive_summary': 'Starter handoff generated from structured notes. Intended to preserve direction and reduce re-research, not replace direct source verification.',
        'findings': [
            {
                'id': f'F{i}',
                'title': item[:80],
                'summary': item,
                'importance': 'medium',
                'confidence': 'medium',
                'evidence': parsed['evidence_anchors'][:2],
                'implications': [],
            }
            for i, item in enumerate(parsed['findings'], start=1)
        ],
        'recommendations': [
            {
                'priority': i,
                'action': item,
                'why': 'Captured from the opportunities section of the source notes.',
                'depends_on': [],
                'risk': 'Needs direct validation against current repo state.',
            }
            for i, item in enumerate(parsed['opportunities'], start=1)
        ],
        'resume_instructions': {
            'read_first': ['CONTEXT_HANDOFF.md', 'summary.json', 'evidence_index.json'],
            'assumptions_to_continue_from': parsed['findings'],
            'must_reverify': parsed['open_questions'],
        },
    }

    write_json(bundle_dir / 'summary.json', summary)
    write_json(bundle_dir / 'entities.json', entities)
    write_json(bundle_dir / 'relations.json', relations)
    write_json(bundle_dir / 'evidence_index.json', evidence_index)
    write_json(bundle_dir / 'open_questions.json', open_questions)
    write_json(
        bundle_dir / 'bundle_metadata.json',
        build_bundle_metadata(mode='generate', source_inputs=[str(notes_path)], notes='Generated from structured markdown notes.')
    )
    (bundle_dir / 'CONTEXT_HANDOFF.md').write_text(render_markdown(title, parsed), encoding='utf-8')
    (bundle_dir / 'resume_prompt.txt').write_text(
        'Read CONTEXT_HANDOFF.md, summary.json, and evidence_index.json first.\n'
        'Continue from high-confidence findings provisionally.\n'
        'Re-verify all open questions and any consequential architectural claims against source materials.\n',
        encoding='utf-8'
    )
    if args.with_graph:
        graph = {
            'nodes': entities,
            'edges': relations,
        }
        write_json(bundle_dir / 'graph.json', graph)

    print(json.dumps({
        'bundle_dir': str(bundle_dir),
        'title': title,
        'projects': parsed['projects'],
        'findings_count': len(parsed['findings']),
        'open_questions_count': len(parsed['open_questions']),
    }, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle).expanduser().resolve()
    missing = [name for name in REQUIRED_FILES if not (bundle / name).exists()]
    markdown_path = bundle / 'CONTEXT_HANDOFF.md'
    resume_path = bundle / 'resume_prompt.txt'

    file_results = [validate_json_file(bundle, name) for name in SCHEMA_MAP]
    markdown_ok = markdown_path.exists() and markdown_path.read_text(encoding='utf-8').strip().startswith('# Context Handoff:')
    resume_ok = resume_path.exists() and len(resume_path.read_text(encoding='utf-8').strip()) > 0

    json_failures = [r for r in file_results if not r['json_valid'] or r['schema_valid'] is False]
    ok = len(missing) == 0 and markdown_ok and resume_ok and len(json_failures) == 0

    result = {
        'bundle': str(bundle),
        'ok': ok,
        'missing': missing,
        'markdown_ok': markdown_ok,
        'resume_prompt_ok': resume_ok,
        'jsonschema_available': jsonschema is not None,
        'files': file_results,
    }
    print(json.dumps(result, indent=2))
    return 0 if ok else 1


def cmd_save(args: argparse.Namespace) -> int:
    from .storage import resolve_store, save_bundle, _git_info
    from .quality import score_bundle

    # Handle --update: find existing bundle and reuse its title/slug/tags
    update_entry = None
    if getattr(args, 'update', False):
        from .storage import resolve_store as _rs, get_repo_local_store, get_global_store
        for store_fn in [lambda: get_repo_local_store(Path.cwd()), get_global_store]:
            s = store_fn()
            if s is None:
                continue
            resolved = s.resolve(args.update if isinstance(args.update, str) and args.update is not True else None,
                                 repo_root=str(Path.cwd()))
            if resolved and not isinstance(resolved, list):
                update_entry = resolved
                break

    # Determine title and slug
    if update_entry and not args.title:
        title = update_entry.get('title', 'Untitled Handoff')
    else:
        title = args.title or 'Untitled Handoff'
    if update_entry and not args.slug:
        slug = update_entry.get('slug', slugify(title))
    else:
        slug = args.slug or slugify(title)
    tags = args.tag or []
    if update_entry and not tags:
        tags = update_entry.get('tags', [])

    # Determine storage mode
    mode = 'auto'
    if getattr(args, 'global_store', False):
        mode = 'global'
    elif getattr(args, 'repo_local', False):
        mode = 'repo-local'

    cwd = Path.cwd()
    store = resolve_store(mode, cwd)

    # If --notes provided, generate from notes first
    # Otherwise, generate a minimal bundle from repo context
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix='chb-'))
    bundle_dir = tmp / f"{date.today().isoformat()}-{slug}"
    bundle_dir.mkdir(parents=True)

    if args.notes:
        notes_path = Path(args.notes).expanduser().resolve()
        text = notes_path.read_text(encoding='utf-8')
        parsed = parse_notes(text)
        source_inputs = [str(notes_path)]
    else:
        # Auto-gather rich context from repo
        from .autocontext import gather_repo_context
        parsed = gather_repo_context(cwd)
        source_inputs = [str(cwd)]

    # Build bundle files
    entities = build_entities(parsed['projects'], parsed['evidence_anchors'])
    relations = build_relations(parsed['projects'], parsed['findings'], parsed['evidence_anchors'])
    evidence_index = build_evidence_index(parsed['evidence_anchors'])
    open_questions = build_open_questions(parsed['open_questions'])

    summary = {
        'title': title,
        'date': date.today().isoformat(),
        'generated_by': {
            'tool': 'context-handoff-bundle',
            'model': 'save-command',
        },
        'purpose': parsed['scope'] or f'Handoff from {cwd.name}',
        'scope': {
            'repos': parsed['projects'],
            'folders': [str(cwd)],
            'inputs': source_inputs,
            'excluded': [],
            'artifacts_created': list(REQUIRED_FILES),
        },
        'executive_summary': f'Context handoff for {title}. Generated to preserve session understanding for cross-terminal reuse.',
        'findings': [
            {
                'id': f'F{i}',
                'title': item[:80],
                'summary': item,
                'importance': 'medium',
                'confidence': 'medium',
                'evidence': parsed['evidence_anchors'][:2],
                'implications': [],
            }
            for i, item in enumerate(parsed['findings'], start=1)
        ],
        'recommendations': [
            {
                'priority': i,
                'action': item,
                'why': 'From session opportunities.',
                'depends_on': [],
                'risk': 'Needs validation.',
            }
            for i, item in enumerate(parsed['opportunities'], start=1)
        ],
        'resume_instructions': {
            'read_first': ['CONTEXT_HANDOFF.md', 'summary.json', 'evidence_index.json'],
            'assumptions_to_continue_from': parsed['findings'],
            'must_reverify': parsed['open_questions'],
        },
    }

    write_json(bundle_dir / 'summary.json', summary)
    write_json(bundle_dir / 'entities.json', entities)
    write_json(bundle_dir / 'relations.json', relations)
    write_json(bundle_dir / 'evidence_index.json', evidence_index)
    write_json(bundle_dir / 'open_questions.json', open_questions)
    write_json(
        bundle_dir / 'bundle_metadata.json',
        build_bundle_metadata(mode='save', source_inputs=source_inputs, notes=f'Saved handoff: {title}')
    )
    (bundle_dir / 'CONTEXT_HANDOFF.md').write_text(render_markdown(title, parsed), encoding='utf-8')
    (bundle_dir / 'resume_prompt.txt').write_text(
        f'# Resume: {title}\n\n'
        f'Read CONTEXT_HANDOFF.md and summary.json first.\n'
        f'Continue from high-confidence findings provisionally.\n'
        f'Re-verify all open questions before making consequential decisions.\n'
        f'Do not re-research established findings unless evidence is stale.\n',
        encoding='utf-8'
    )

    # Score the bundle
    quality = score_bundle(bundle_dir)

    # Persist to store
    git_info = _git_info(cwd)
    entry = save_bundle(
        bundle_dir=bundle_dir,
        store=store,
        title=title,
        slug=slug,
        tags=tags,
        repo_root=git_info.get('repo_root') or str(cwd),
        quality_score=quality,
    )

    # Clean up temp dir
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    # Output result
    result = {
        'saved': True,
        'bundle_id': entry['id'],
        'title': title,
        'slug': slug,
        'path': entry['path'],
        'storage_mode': entry['storage_mode'],
        'quality': quality['overall'],
        'score': quality['score'],
        'warnings': quality['warnings'],
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    from .storage import resolve_store, get_repo_local_store, get_global_store
    from .freshness import check_freshness
    from .resume import compose_resume

    cwd = Path.cwd()
    query = args.query

    # Search both stores
    stores = []
    repo_store = get_repo_local_store(cwd)
    if repo_store and repo_store.index_path.exists():
        stores.append(('repo-local', repo_store))
    global_store = get_global_store()
    if global_store.index_path.exists():
        stores.append(('global', global_store))

    if not stores:
        print(json.dumps({'error': 'No bundle stores found. Save a handoff first.'}))
        return 1

    # Try resolution
    result = None
    used_store = None
    for label, store in stores:
        git_info_mod = None
        try:
            import subprocess
            root = subprocess.check_output(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=str(cwd), stderr=subprocess.DEVNULL, text=True,
            ).strip()
            git_info_mod = root
        except Exception:
            pass
        resolved = store.resolve(query, repo_root=git_info_mod)
        if resolved is not None:
            result = resolved
            used_store = (label, store)
            break

    if result is None:
        print(json.dumps({'error': f'No bundle found for query: {query or "latest"}'}))
        return 1

    # Ambiguous?
    if isinstance(result, list):
        print(json.dumps({
            'error': 'Ambiguous match - multiple bundles found',
            'matches': [
                {'id': e['id'], 'title': e.get('title', ''), 'created_at': e.get('created_at', '')}
                for e in result[:10]
            ],
            'hint': 'Use an exact id or slug to resolve.',
        }, indent=2))
        return 1

    entry = result
    bundle_path = Path(entry['path'])
    if not bundle_path.exists():
        print(json.dumps({'error': f'Bundle directory missing: {entry["path"]}'}))
        return 1

    # Freshness check
    freshness = check_freshness(entry, cwd)

    # Compose resume
    mode = 'deep' if args.deep else 'fast'
    resume_text = compose_resume(bundle_path, mode=mode)

    output: dict = {
        'loaded': True,
        'bundle_id': entry['id'],
        'title': entry.get('title', ''),
        'path': entry['path'],
        'created_at': entry.get('created_at', ''),
        'fresh': freshness['fresh'],
        'freshness_warnings': freshness['warnings'],
    }

    if args.json_output:
        print(json.dumps(output, indent=2))
    else:
        # Human-readable: print resume context
        if freshness['warnings']:
            print('--- FRESHNESS WARNINGS ---')
            for w in freshness['warnings']:
                print(f'  WARNING:{w}')
            print('---\n')
        print(resume_text)

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    from .storage import get_repo_local_store, get_global_store

    cwd = Path.cwd()
    entries: list[dict] = []

    if not args.global_only:
        repo_store = get_repo_local_store(cwd)
        if repo_store:
            for e in repo_store.list_entries(limit=args.limit):
                e['_store'] = 'repo-local'
                entries.append(e)

    if not args.repo_only:
        global_store = get_global_store()
        for e in global_store.list_entries(limit=args.limit):
            e['_store'] = 'global'
            entries.append(e)

    # Deduplicate by id
    seen = set()
    deduped = []
    for e in entries:
        if e['id'] not in seen:
            seen.add(e['id'])
            deduped.append(e)

    # Sort by date
    deduped.sort(key=lambda e: e.get('created_at', ''), reverse=True)
    deduped = deduped[:args.limit]

    if not deduped:
        print('No saved handoff bundles found.')
        return 0

    if args.json_output:
        print(json.dumps(deduped, indent=2))
    else:
        print(f'{"ID":<40} {"Title":<30} {"Date":<12} {"Quality":<10} {"Store":<10}')
        print('-' * 102)
        for e in deduped:
            bid = e.get('id', '')[:38]
            title = e.get('title', '')[:28]
            created = e.get('created_at', '')[:10]
            quality = e.get('quality', {})
            qstr = quality.get('overall', '?') if isinstance(quality, dict) else '?'
            store_label = e.get('_store', '?')
            print(f'{bid:<40} {title:<30} {created:<12} {qstr:<10} {store_label:<10}')

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    from .storage import get_repo_local_store, get_global_store
    from .quality import score_bundle
    from .freshness import check_freshness

    cwd = Path.cwd()
    query = args.query

    # Try both stores
    entry = None
    for store_fn in [lambda: get_repo_local_store(cwd), get_global_store]:
        store = store_fn()
        if store is None:
            continue
        resolved = store.resolve(query)
        if resolved and not isinstance(resolved, list):
            entry = resolved
            break
        if isinstance(resolved, list) and resolved:
            entry = resolved[0]
            break

    if entry is None:
        print(json.dumps({'error': f'No bundle found for: {query}'}))
        return 1

    bundle_path = Path(entry['path'])
    if not bundle_path.exists():
        print(json.dumps({'error': f'Bundle directory missing: {entry["path"]}'}))
        return 1

    # Score (recompute to get current assessment)
    quality = score_bundle(bundle_path)
    freshness = check_freshness(entry, cwd)

    # Load key data
    summary = {}
    summary_path = bundle_path / 'summary.json'
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding='utf-8'))
        except Exception:
            pass

    questions = []
    q_path = bundle_path / 'open_questions.json'
    if q_path.exists():
        try:
            questions = json.loads(q_path.read_text(encoding='utf-8'))
        except Exception:
            pass

    if args.json_output:
        print(json.dumps({
            'entry': entry,
            'quality': quality,
            'freshness': freshness,
            'summary_excerpt': summary.get('executive_summary', ''),
            'findings_count': len(summary.get('findings', [])),
            'open_questions_count': len(questions),
        }, indent=2))
    else:
        print(f'Bundle: {entry["id"]}')
        print(f'Title:  {entry.get("title", "")}')
        print(f'Slug:   {entry.get("slug", "")}')
        print(f'Created: {entry.get("created_at", "")}')
        print(f'Repo:   {entry.get("repo_root", "")}')
        print(f'Branch: {entry.get("branch", "")}')
        print(f'Tags:   {", ".join(entry.get("tags", []))}')
        print(f'Path:   {entry["path"]}')
        print()
        print(f'Quality: {quality["overall"]} ({quality["score"]:.2f})')
        if quality['warnings']:
            for w in quality['warnings']:
                print(f'  WARNING:{w}')
        print()
        print(f'Fresh:  {"yes" if freshness["fresh"] else "NO"}')
        if freshness['warnings']:
            for w in freshness['warnings']:
                print(f'  WARNING:{w}')
        print()
        exec_summ = summary.get('executive_summary', 'N/A')
        print(f'Summary: {exec_summ}')
        findings = summary.get('findings', [])
        if findings:
            print(f'\nFindings ({len(findings)}):')
            for f in findings[:5]:
                print(f'  - {f.get("id", "")} {f.get("title", "")}')
        if questions:
            print(f'\nOpen Questions ({len(questions)}):')
            for q in questions[:5]:
                print(f'  - {q.get("id", "")} {q.get("question", "")}')

    return 0


def cmd_score(args: argparse.Namespace) -> int:
    from .quality import score_bundle
    bundle = Path(args.bundle).expanduser().resolve()
    result = score_bundle(bundle)
    print(json.dumps(result, indent=2))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    from .storage import get_repo_local_store, get_global_store
    import shutil

    cwd = Path.cwd()
    query = args.query
    deleted = False

    for store_fn in [lambda: get_repo_local_store(cwd), get_global_store]:
        store = store_fn()
        if store is None:
            continue
        resolved = store.resolve(query)
        if resolved and not isinstance(resolved, list):
            bundle_path = Path(resolved['path'])
            if bundle_path.exists():
                shutil.rmtree(bundle_path)
            store.delete_entry(resolved['id'])
            print(json.dumps({'deleted': True, 'id': resolved['id'], 'path': str(bundle_path)}))
            deleted = True
            break

    if not deleted:
        print(json.dumps({'error': f'No bundle found for: {query}'}))
        return 1
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    from .storage import get_repo_local_store, get_global_store
    import shutil

    cwd = Path.cwd()
    pruned: list[dict] = []

    stores: list[tuple[str, object]] = []
    if not args.global_only:
        repo_store = get_repo_local_store(cwd)
        if repo_store:
            stores.append(('repo-local', repo_store))
    if not args.repo_only:
        stores.append(('global', get_global_store()))

    for label, store in stores:
        entries = store.list_entries(limit=1000)
        # Group by slug
        by_slug: dict[str, list[dict]] = {}
        for e in entries:
            slug = e.get('slug', 'unknown')
            by_slug.setdefault(slug, []).append(e)

        for slug, group in by_slug.items():
            if len(group) <= args.keep:
                continue
            # Sort by created_at descending, prune oldest beyond keep count
            group.sort(key=lambda e: e.get('created_at', ''), reverse=True)
            to_remove = group[args.keep:]
            for entry in to_remove:
                bundle_path = Path(entry['path'])
                if bundle_path.exists():
                    shutil.rmtree(bundle_path)
                store.delete_entry(entry['id'])
                pruned.append({'id': entry['id'], 'slug': slug, 'store': label})

    if pruned:
        print(f'Pruned {len(pruned)} bundle(s):')
        for p in pruned:
            print(f'  - {p["id"]} ({p["slug"]}) from {p["store"]}')
    else:
        print('Nothing to prune.')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='context-handoff-bundle')
    sub = parser.add_subparsers(dest='command', required=True)

    # --- init ---
    p_init = sub.add_parser('init', help='create a new handoff bundle directory')
    p_init.add_argument('--output', default='docs/context-handoffs', help='bundle output root')
    p_init.add_argument('--slug', default='untitled-handoff', help='bundle slug')
    p_init.add_argument('--with-graph', action='store_true', help='also create graph.json')
    p_init.add_argument('--force', action='store_true', help='overwrite existing files from templates')
    p_init.set_defaults(func=cmd_init)

    # --- generate ---
    p_generate = sub.add_parser('generate', help='generate a starter bundle from structured notes')
    p_generate.add_argument('notes', help='path to a structured markdown notes file')
    p_generate.add_argument('--output', default='docs/context-handoffs', help='bundle output root')
    p_generate.add_argument('--slug', help='bundle slug override')
    p_generate.add_argument('--title', help='bundle title override')
    p_generate.add_argument('--with-graph', action='store_true', help='also create graph.json')
    p_generate.set_defaults(func=cmd_generate)

    # --- validate ---
    p_validate = sub.add_parser('validate', help='validate required bundle files and JSON schema conformance')
    p_validate.add_argument('bundle', help='path to bundle directory')
    p_validate.set_defaults(func=cmd_validate)

    # --- save ---
    p_save = sub.add_parser('save', help='save a durable handoff bundle to the registry')
    p_save.add_argument('--title', help='bundle title')
    p_save.add_argument('--slug', help='bundle slug')
    p_save.add_argument('--notes', help='path to structured notes file')
    p_save.add_argument('--tag', action='append', help='tag (repeatable)')
    p_save.add_argument('--global', dest='global_store', action='store_true', help='save to global store')
    p_save.add_argument('--repo-local', dest='repo_local', action='store_true', help='save to repo-local store')
    p_save.add_argument('--update', nargs='?', const=True, default=False,
                        help='update latest bundle instead of creating new (optionally specify id/slug)')
    p_save.set_defaults(func=cmd_save)

    # --- load ---
    p_load = sub.add_parser('load', help='load a saved handoff bundle and emit resume context')
    p_load.add_argument('query', nargs='?', default=None, help='bundle id, slug, or "latest"')
    p_load.add_argument('--deep', action='store_true', help='deep load mode with full context')
    p_load.add_argument('--json', dest='json_output', action='store_true', help='output JSON instead of resume text')
    p_load.set_defaults(func=cmd_load)

    # --- list ---
    p_list = sub.add_parser('list', help='list saved handoff bundles')
    p_list.add_argument('--repo-only', action='store_true', help='only show repo-local bundles')
    p_list.add_argument('--global-only', action='store_true', help='only show global bundles')
    p_list.add_argument('--limit', type=int, default=20, help='max results')
    p_list.add_argument('--json', dest='json_output', action='store_true', help='output JSON')
    p_list.set_defaults(func=cmd_list)

    # --- show ---
    p_show = sub.add_parser('show', help='show details for a saved handoff bundle')
    p_show.add_argument('query', help='bundle id, slug, or "latest"')
    p_show.add_argument('--json', dest='json_output', action='store_true', help='output JSON')
    p_show.set_defaults(func=cmd_show)

    # --- score ---
    p_score = sub.add_parser('score', help='recompute quality score for a bundle directory')
    p_score.add_argument('bundle', help='path to bundle directory')
    p_score.set_defaults(func=cmd_score)

    # --- delete ---
    p_delete = sub.add_parser('delete', help='delete a saved handoff bundle')
    p_delete.add_argument('query', help='bundle id or slug to delete')
    p_delete.set_defaults(func=cmd_delete)

    # --- prune ---
    p_prune = sub.add_parser('prune', help='remove old duplicate bundles, keeping newest per slug')
    p_prune.add_argument('--keep', type=int, default=1, help='how many to keep per slug (default: 1)')
    p_prune.add_argument('--repo-only', action='store_true', help='only prune repo-local store')
    p_prune.add_argument('--global-only', action='store_true', help='only prune global store')
    p_prune.set_defaults(func=cmd_prune)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
