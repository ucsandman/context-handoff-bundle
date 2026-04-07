"""Auto-context gathering for rich handoff generation without manual notes.

Task-aware: captures what was being worked on, what changed, what broke,
what remains unresolved, and which files matter first -- not just repo orientation.
"""
from __future__ import annotations

import glob
import subprocess
from pathlib import Path


def gather_repo_context(cwd: Path | None = None) -> dict:
    """Gather rich, task-aware context from the current repo automatically.

    Returns a parsed dict compatible with the notes format:
        scope, projects, findings, opportunities, open_questions, evidence_anchors
    """
    cwd = cwd or Path.cwd()
    cwd = cwd.resolve()

    scope = _build_scope(cwd)
    projects = _detect_projects(cwd)
    findings = _gather_findings(cwd)
    evidence = _gather_evidence_anchors(cwd)
    open_questions = _gather_open_questions(cwd, findings)

    return {
        'scope': scope,
        'projects': projects,
        'findings': findings,
        'opportunities': [],
        'open_questions': open_questions,
        'evidence_anchors': evidence,
    }


def _build_scope(cwd: Path) -> str:
    """Build a scope description from repo state."""
    parts = [f'Context handoff from {cwd.name}']
    branch = _git_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd)
    if branch:
        parts.append(f'on branch {branch}')
    return ' '.join(parts)


def _detect_projects(cwd: Path) -> list[str]:
    """Detect project names from repo structure."""
    projects = [cwd.name]
    for subdir in ['packages', 'projects', 'apps', 'services', 'modules']:
        d = cwd / subdir
        if d.is_dir():
            for child in sorted(d.iterdir()):
                if child.is_dir() and not child.name.startswith('.'):
                    projects.append(child.name)
    return projects


def _gather_findings(cwd: Path) -> list[str]:
    """Extract task-aware findings from repo inspection."""
    findings: list[str] = []

    # 1. What the project is
    readme_desc = _extract_readme_purpose(cwd)
    if readme_desc:
        findings.append(readme_desc)

    # 2. What branch work looks like
    branch_summary = _summarize_branch_work(cwd)
    if branch_summary:
        findings.append(branch_summary)

    # 3. What was being worked on (recent commit themes)
    work_focus = _detect_work_focus(cwd)
    if work_focus:
        findings.append(work_focus)

    # 4. What changed recently (diff stats)
    diff_summary = _summarize_recent_diff(cwd)
    if diff_summary:
        findings.append(diff_summary)

    # 5. What's in progress right now
    wip = _detect_work_in_progress(cwd)
    if wip:
        findings.append(wip)

    # 6. Technology stack
    stack = _detect_tech_stack(cwd)
    if stack:
        findings.append(f'Technology stack: {", ".join(stack)}')

    # 7. Project structure
    structure = _summarize_structure(cwd)
    if structure:
        findings.append(structure)

    # 8. What files were touched most recently
    hot_files = _get_hot_files(cwd)
    if hot_files:
        findings.append(f'Hot files (most recently changed): {", ".join(hot_files[:6])}')

    return findings


def _gather_evidence_anchors(cwd: Path) -> list[str]:
    """Gather key files as evidence anchors, prioritizing recently changed files."""
    anchors: list[str] = []

    # Recently changed files first -- these are most relevant
    hot = _get_hot_files(cwd)
    for f in hot[:5]:
        p = cwd / f
        if p.exists():
            anchors.append(str(p))

    # Key documentation files
    for name in ['README.md', 'CLAUDE.md', 'docs/SPEC.md', 'docs/ROADMAP.md',
                 'docs/ARCHITECTURE.md', 'package.json', 'pyproject.toml',
                 'Cargo.toml', 'go.mod', 'pom.xml']:
        p = cwd / name
        if p.exists():
            anchors.append(str(p))

    # Source entry points
    for pattern in ['src/index.*', 'src/main.*', 'src/app.*', 'src/lib.*',
                    'src/*/cli.py', 'src/*/main.py', 'src/*/__init__.py',
                    'main.*', 'index.*', 'app.*']:
        matches = glob.glob(str(cwd / pattern))
        for m in matches[:3]:
            anchors.append(m)

    # Dirty files -- these are actively being worked on
    dirty = _get_dirty_files(cwd)
    for f in dirty[:5]:
        p = cwd / f
        if p.exists():
            anchors.append(str(p))

    return list(dict.fromkeys(anchors))  # Deduplicate preserving order


def _gather_open_questions(cwd: Path, findings: list[str]) -> list[str]:
    """Generate honest open questions based on what we don't know."""
    questions: list[str] = []

    dirty = _get_dirty_files(cwd)
    if dirty:
        questions.append(f'There are {len(dirty)} uncommitted file(s) -- what is their state? Ready to commit or still in progress?')

    # Detect potential issues
    failing_tests = _detect_test_failures(cwd)
    if failing_tests:
        questions.append(f'Tests may be failing: {failing_tests}')

    todo_count = _count_todos(cwd)
    if todo_count > 0:
        questions.append(f'{todo_count} TODO/FIXME comments in the codebase -- which are relevant to the current work?')

    # Branch-specific questions
    branch = _git_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd)
    if branch and branch not in ('main', 'master'):
        questions.append(f'Branch "{branch}" -- is it ready to merge, or still in progress?')

    questions.append('What was the immediate next step before this handoff?')

    return questions


# ── Task-awareness helpers ──

def _summarize_branch_work(cwd: Path) -> str:
    """Summarize what this branch has done vs main."""
    branch = _git_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd)
    if not branch or branch in ('main', 'master'):
        return ''

    # Count commits ahead of main
    for base in ['main', 'master']:
        count = _git_output(['git', 'rev-list', '--count', f'{base}..HEAD'], cwd)
        if count and count != '0':
            # Get the commit subjects
            subjects = _git_output(
                ['git', 'log', f'{base}..HEAD', '--oneline', '--no-decorate', '--max-count=5'],
                cwd
            )
            if subjects:
                lines = subjects.splitlines()
                summary = '; '.join(lines[:4])
                extra = f'; and {len(lines) - 4} more' if len(lines) > 4 else ''
                return f'Branch "{branch}" is {count} commit(s) ahead of {base}: {summary}{extra}'
    return ''


def _detect_work_focus(cwd: Path) -> str:
    """Detect what kind of work was happening from recent commits."""
    log = _git_output(
        ['git', 'log', '--max-count=8', '--format=%s', '--no-decorate'],
        cwd
    )
    if not log:
        return ''

    messages = log.splitlines()
    # Look for patterns
    keywords: dict[str, int] = {}
    for msg in messages:
        lower = msg.lower()
        for kw in ['fix', 'add', 'update', 'refactor', 'test', 'docs', 'feat',
                    'build', 'config', 'remove', 'clean', 'merge', 'wip']:
            if kw in lower:
                keywords[kw] = keywords.get(kw, 0) + 1

    if not keywords:
        return f'Recent work: {"; ".join(messages[:3])}'

    # Top themes
    sorted_kw = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
    themes = [k for k, _ in sorted_kw[:3]]
    return f'Recent work themes: {", ".join(themes)}. Last commits: {"; ".join(messages[:3])}'


def _summarize_recent_diff(cwd: Path) -> str:
    """Summarize what changed in recent commits by file count and areas."""
    stat = _git_output(
        ['git', 'diff', '--stat', '--stat-count=10', 'HEAD~3..HEAD'],
        cwd
    )
    if not stat:
        # Try with fewer commits
        stat = _git_output(['git', 'diff', '--stat', '--stat-count=10', 'HEAD~1..HEAD'], cwd)
    if not stat:
        return ''

    lines = stat.strip().splitlines()
    if lines:
        # Last line is the summary (e.g., "10 files changed, 200 insertions(+), 50 deletions(-)")
        summary_line = lines[-1].strip()
        if 'changed' in summary_line:
            return f'Recent changes: {summary_line}'
    return ''


def _detect_work_in_progress(cwd: Path) -> str:
    """Detect uncommitted work and characterize it."""
    dirty = _get_dirty_files(cwd)
    if not dirty:
        return ''

    # Categorize dirty files
    staged = _git_output(['git', 'diff', '--name-only', '--cached'], cwd)
    unstaged = _git_output(['git', 'diff', '--name-only'], cwd)
    untracked = _git_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd)

    parts = []
    if staged:
        staged_count = len(staged.splitlines())
        parts.append(f'{staged_count} staged')
    if unstaged:
        unstaged_count = len(unstaged.splitlines())
        parts.append(f'{unstaged_count} modified')
    if untracked:
        untracked_count = len(untracked.splitlines())
        parts.append(f'{untracked_count} untracked')

    file_list = ', '.join(dirty[:5])
    extra = f' and {len(dirty) - 5} more' if len(dirty) > 5 else ''
    return f'Work in progress ({", ".join(parts)}): {file_list}{extra}'


def _detect_test_failures(cwd: Path) -> str:
    """Quick check for obvious test failure indicators."""
    # Look for common test result files
    for pattern in ['.pytest_cache/v/cache/lastfailed', 'test-results.xml']:
        p = cwd / pattern
        if p.exists():
            try:
                content = p.read_text(encoding='utf-8')
                if content.strip() and content.strip() != '{}':
                    return 'pytest lastfailed cache is non-empty -- tests may have been failing'
            except Exception:
                pass
    return ''


def _get_hot_files(cwd: Path) -> list[str]:
    """Get the most actively changed files across recent commits + dirty state."""
    files: list[str] = []

    # Files changed in last 5 commits
    output = _git_output(
        ['git', 'log', '--max-count=5', '--name-only', '--pretty=format:'],
        cwd
    )
    if output:
        for f in output.splitlines():
            f = f.strip()
            if f and f not in files:
                files.append(f)

    # Dirty files
    dirty = _get_dirty_files(cwd)
    for f in dirty:
        if f not in files:
            files.insert(0, f)  # Dirty files are hottest

    return files[:15]


# ── Base helpers ──

def _git_output(cmd: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(
            cmd, cwd=str(cwd), stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return ''


def _extract_readme_purpose(cwd: Path) -> str:
    readme = cwd / 'README.md'
    if not readme.exists():
        return ''
    try:
        text = readme.read_text(encoding='utf-8')
        lines = text.splitlines()
        content_lines: list[str] = []
        past_title = False
        for line in lines:
            if line.startswith('# ') and not past_title:
                past_title = True
                continue
            if past_title and line.strip():
                content_lines.append(line.strip())
                if len(content_lines) >= 3:
                    break
            elif past_title and content_lines:
                break
        if content_lines:
            desc = ' '.join(content_lines)
            if len(desc) > 300:
                desc = desc[:297] + '...'
            return desc
    except Exception:
        pass
    return ''


def _detect_tech_stack(cwd: Path) -> list[str]:
    stack: list[str] = []
    indicators = {
        'package.json': 'Node.js', 'pyproject.toml': 'Python',
        'Cargo.toml': 'Rust', 'go.mod': 'Go',
        'pom.xml': 'Java/Maven', 'build.gradle': 'Java/Gradle',
        'Gemfile': 'Ruby', 'composer.json': 'PHP',
        'tsconfig.json': 'TypeScript', 'next.config.js': 'Next.js',
        'next.config.ts': 'Next.js', 'vite.config.ts': 'Vite',
        'Dockerfile': 'Docker', 'docker-compose.yml': 'Docker Compose',
    }
    for filename, tech in indicators.items():
        if (cwd / filename).exists():
            stack.append(tech)
    return stack


def _summarize_structure(cwd: Path) -> str:
    dirs: list[str] = []
    for item in sorted(cwd.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            dirs.append(item.name)
    if not dirs:
        return ''
    return f'Top-level directories: {", ".join(dirs[:12])}'


def _get_dirty_files(cwd: Path) -> list[str]:
    output = _git_output(['git', 'status', '--porcelain', '--short'], cwd)
    if not output:
        return []
    files: list[str] = []
    for line in output.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            files.append(parts[1])
    return files[:20]


def _count_todos(cwd: Path) -> int:
    try:
        output = subprocess.check_output(
            ['git', 'grep', '-c', '-E', r'TODO|FIXME'],
            cwd=str(cwd), stderr=subprocess.DEVNULL, text=True
        )
        total = 0
        for line in output.splitlines():
            parts = line.rsplit(':', 1)
            if len(parts) == 2:
                try:
                    total += int(parts[1])
                except ValueError:
                    pass
        return total
    except Exception:
        return 0
