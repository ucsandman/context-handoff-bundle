"""Auto-context gathering for rich handoff generation without manual notes."""
from __future__ import annotations

import subprocess
from pathlib import Path


def gather_repo_context(cwd: Path | None = None) -> dict:
    """Gather rich context from the current repo automatically.

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

    # Check for monorepo patterns
    for subdir in ['packages', 'projects', 'apps', 'services', 'modules']:
        d = cwd / subdir
        if d.is_dir():
            for child in sorted(d.iterdir()):
                if child.is_dir() and not child.name.startswith('.'):
                    projects.append(child.name)

    return projects


def _gather_findings(cwd: Path) -> list[str]:
    """Extract findings from repo inspection."""
    findings: list[str] = []

    # 1. Project description from README
    readme_desc = _extract_readme_purpose(cwd)
    if readme_desc:
        findings.append(readme_desc)

    # 2. CLAUDE.md project description
    claude_desc = _extract_claude_md_purpose(cwd)
    if claude_desc:
        findings.append(claude_desc)

    # 3. Recent git activity summary
    recent_summary = _summarize_recent_commits(cwd)
    if recent_summary:
        findings.append(recent_summary)

    # 4. Key technology stack
    stack = _detect_tech_stack(cwd)
    if stack:
        findings.append(f'Technology stack: {", ".join(stack)}')

    # 5. Project structure summary
    structure = _summarize_structure(cwd)
    if structure:
        findings.append(structure)

    # 6. Recent file changes
    recent_files = _recent_modified_files(cwd)
    if recent_files:
        findings.append(f'Recently modified files: {", ".join(recent_files[:8])}')

    # 7. Dirty state
    dirty_files = _get_dirty_files(cwd)
    if dirty_files:
        findings.append(f'Uncommitted changes in {len(dirty_files)} file(s): {", ".join(dirty_files[:5])}')

    return findings


def _gather_evidence_anchors(cwd: Path) -> list[str]:
    """Gather key files as evidence anchors."""
    anchors: list[str] = []

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
        import glob
        matches = glob.glob(str(cwd / pattern))
        for m in matches[:3]:
            anchors.append(m)

    # Config files
    for name in ['.env.example', 'tsconfig.json', 'jest.config.*',
                 'pytest.ini', 'setup.cfg', 'Makefile', 'Dockerfile']:
        import glob as g2
        matches = g2.glob(str(cwd / name))
        for m in matches[:2]:
            anchors.append(m)

    return list(dict.fromkeys(anchors))  # Deduplicate preserving order


def _gather_open_questions(cwd: Path, findings: list[str]) -> list[str]:
    """Generate honest open questions based on what we don't know."""
    questions: list[str] = []

    # Always ask about in-progress work
    dirty = _get_dirty_files(cwd)
    if dirty:
        questions.append('What is the current state of the uncommitted changes?')

    # Check for TODO/FIXME in recent files
    todo_count = _count_todos(cwd)
    if todo_count > 0:
        questions.append(f'There are {todo_count} TODO/FIXME comments in the codebase - which are priorities?')

    # Default questions
    questions.append('What was the most recent work focus before this handoff?')
    questions.append('Are there any blocking issues or decisions pending?')

    return questions


# --- Helper functions ---

def _git_output(cmd: list[str], cwd: Path) -> str:
    """Run a git command and return stripped stdout, or empty string on failure."""
    try:
        return subprocess.check_output(
            cmd, cwd=str(cwd), stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return ''


def _extract_readme_purpose(cwd: Path) -> str:
    """Extract the first meaningful paragraph from README.md."""
    readme = cwd / 'README.md'
    if not readme.exists():
        return ''
    try:
        text = readme.read_text(encoding='utf-8')
        lines = text.splitlines()
        # Skip title line and blank lines, grab first real paragraph
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
            if len(desc) > 200:
                desc = desc[:197] + '...'
            return f'README says: {desc}'
    except Exception:
        pass
    return ''


def _extract_claude_md_purpose(cwd: Path) -> str:
    """Extract project description from CLAUDE.md if present."""
    for name in ['CLAUDE.md', '.claude/CLAUDE.md']:
        p = cwd / name
        if p.exists():
            try:
                text = p.read_text(encoding='utf-8')
                # Look for first meaningful line
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#') and len(stripped) > 20:
                        desc = stripped[:200]
                        return f'CLAUDE.md describes: {desc}'
            except Exception:
                pass
    return ''


def _summarize_recent_commits(cwd: Path, count: int = 10) -> str:
    """Summarize recent git commits."""
    log = _git_output(
        ['git', 'log', f'--max-count={count}', '--oneline', '--no-decorate'],
        cwd
    )
    if not log:
        return ''
    lines = log.splitlines()
    if len(lines) <= 3:
        commits_text = '; '.join(lines)
        return f'Recent commits ({len(lines)}): {commits_text}'
    # Summarize
    return f'Recent commits ({len(lines)}): {"; ".join(lines[:5])}; and {len(lines) - 5} more'


def _detect_tech_stack(cwd: Path) -> list[str]:
    """Detect technology stack from project files."""
    stack: list[str] = []
    indicators = {
        'package.json': 'Node.js',
        'pyproject.toml': 'Python',
        'Cargo.toml': 'Rust',
        'go.mod': 'Go',
        'pom.xml': 'Java/Maven',
        'build.gradle': 'Java/Gradle',
        'Gemfile': 'Ruby',
        'composer.json': 'PHP',
        'tsconfig.json': 'TypeScript',
        'next.config.js': 'Next.js',
        'next.config.ts': 'Next.js',
        'vite.config.ts': 'Vite',
        'Dockerfile': 'Docker',
        'docker-compose.yml': 'Docker Compose',
    }
    for filename, tech in indicators.items():
        if (cwd / filename).exists():
            stack.append(tech)
    return stack


def _summarize_structure(cwd: Path) -> str:
    """Summarize the top-level directory structure."""
    dirs: list[str] = []
    for item in sorted(cwd.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            dirs.append(item.name)
    if not dirs:
        return ''
    return f'Top-level directories: {", ".join(dirs[:12])}'


def _recent_modified_files(cwd: Path, count: int = 10) -> list[str]:
    """Get recently modified tracked files from git."""
    output = _git_output(
        ['git', 'log', '--max-count=3', '--name-only', '--pretty=format:'],
        cwd
    )
    if not output:
        return []
    files = [f for f in output.splitlines() if f.strip()]
    # Deduplicate preserving order
    seen: set[str] = set()
    result: list[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result[:count]


def _get_dirty_files(cwd: Path) -> list[str]:
    """Get list of uncommitted changed files."""
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
    """Count TODO/FIXME comments in tracked source files."""
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
