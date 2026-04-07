"""Bundle storage and registry for cross-terminal reuse."""
from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPO_LOCAL_DIR = '.context-handoffs'
DEFAULT_GLOBAL_DIR = '~/.context-handoff-bundles'
REGISTRY_FILENAME = 'index.json'


def _git_info(repo_root: Path | None = None) -> dict[str, str | None]:
    """Gather git repo info. Returns empty values on failure."""
    info: dict[str, str | None] = {
        'repo_root': None,
        'branch': None,
        'head_commit': None,
        'dirty': None,
    }
    cwd = str(repo_root) if repo_root else None
    try:
        root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        info['repo_root'] = root
    except Exception:
        return info

    try:
        info['branch'] = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except Exception:
        pass

    try:
        info['head_commit'] = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except Exception:
        pass

    try:
        status = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        info['dirty'] = 'true' if status else 'false'
    except Exception:
        pass

    return info


class BundleStore:
    """Manages bundle storage in a single store directory with an index registry."""

    def __init__(self, store_path: Path):
        self.store_path = store_path.expanduser().resolve()
        self.index_path = self.store_path / REGISTRY_FILENAME

    def ensure_store(self) -> None:
        self.store_path.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        try:
            return json.loads(self.index_path.read_text(encoding='utf-8'))
        except Exception:
            return []

    def _save_index(self, entries: list[dict]) -> None:
        self.ensure_store()
        self.index_path.write_text(json.dumps(entries, indent=2), encoding='utf-8')

    def register(self, entry: dict) -> None:
        """Add or update a bundle entry in the index."""
        entries = self._load_index()
        # Replace existing entry with same id
        entries = [e for e in entries if e.get('id') != entry['id']]
        entries.append(entry)
        # Sort by created_at descending
        entries.sort(key=lambda e: e.get('created_at', ''), reverse=True)
        self._save_index(entries)

    def list_entries(
        self,
        repo_root: str | None = None,
        tag: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        entries = self._load_index()
        if repo_root:
            norm = _normalize_path(repo_root)
            entries = [e for e in entries if _normalize_path(e.get('repo_root', '')) == norm]
        if tag:
            entries = [e for e in entries if tag in e.get('tags', [])]
        return entries[:limit]

    def resolve(
        self,
        query: str | None = None,
        repo_root: str | None = None,
    ) -> dict | list[dict] | None:
        """Resolve a bundle by query string.

        Returns:
            - Single dict if unambiguous match found
            - List of dicts if ambiguous (caller must handle)
            - None if no match
        """
        entries = self._load_index()
        if not entries:
            return None

        # "latest" or no query: latest for this repo or overall
        if not query or query == 'latest':
            if repo_root:
                norm = _normalize_path(repo_root)
                repo_entries = [e for e in entries if _normalize_path(e.get('repo_root', '')) == norm]
                if repo_entries:
                    return repo_entries[0]  # Already sorted by date desc
            return entries[0]

        # Exact id match
        for e in entries:
            if e.get('id') == query:
                return e

        # Slug match
        slug_matches = [e for e in entries if e.get('slug') == query]
        if len(slug_matches) == 1:
            return slug_matches[0]
        if len(slug_matches) > 1:
            return slug_matches  # Ambiguous

        # Partial match on slug or title
        partial = [e for e in entries if query.lower() in e.get('slug', '').lower()
                    or query.lower() in e.get('title', '').lower()]
        if len(partial) == 1:
            return partial[0]
        if len(partial) > 1:
            return partial  # Ambiguous

        return None

    def get_bundle_path(self, entry: dict) -> Path:
        return Path(entry['path'])

    def delete_entry(self, bundle_id: str) -> bool:
        entries = self._load_index()
        original_len = len(entries)
        entries = [e for e in entries if e.get('id') != bundle_id]
        if len(entries) == original_len:
            return False
        self._save_index(entries)
        return True


def _normalize_path(p: str) -> str:
    """Normalize path for comparison (forward slashes, lowercase on Windows)."""
    import sys
    result = p.replace('\\', '/')
    if sys.platform == 'win32':
        result = result.lower()
    return result


def get_repo_local_store(cwd: Path | None = None) -> BundleStore | None:
    """Find repo-local store. Returns None if not in a git repo."""
    try:
        root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=str(cwd) if cwd else None,
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        return BundleStore(Path(root) / DEFAULT_REPO_LOCAL_DIR)
    except Exception:
        return None


def get_global_store() -> BundleStore:
    return BundleStore(Path(DEFAULT_GLOBAL_DIR).expanduser())


def resolve_store(mode: str = 'auto', cwd: Path | None = None) -> BundleStore:
    """Resolve which store to use.

    mode:
        'repo-local': force repo-local store
        'global': force global store
        'auto': default to global (cross-terminal is the primary use case)
    """
    if mode == 'global':
        return get_global_store()
    if mode == 'repo-local':
        store = get_repo_local_store(cwd)
        if store is None:
            raise RuntimeError('Not in a git repository; cannot use repo-local store')
        return store
    # auto: default to global for cross-terminal portability
    return get_global_store()


def save_bundle(
    bundle_dir: Path,
    store: BundleStore,
    title: str,
    slug: str,
    tags: list[str] | None = None,
    repo_root: str | None = None,
    quality_score: dict | None = None,
) -> dict:
    """Copy a bundle directory into the store and register it."""
    store.ensure_store()
    bundle_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{slug}"
    dest = store.store_path / bundle_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(bundle_dir, dest)

    git_info = _git_info(Path(repo_root) if repo_root else None)
    now = datetime.now(timezone.utc).isoformat()

    entry: dict[str, Any] = {
        'id': bundle_id,
        'title': title,
        'slug': slug,
        'created_at': now,
        'updated_at': now,
        'path': str(dest),
        'repo_root': repo_root or git_info.get('repo_root') or '',
        'branch': git_info.get('branch') or '',
        'head_commit': git_info.get('head_commit') or '',
        'dirty': git_info.get('dirty') or '',
        'tags': tags or [],
        'quality': quality_score or {},
        'storage_mode': 'repo-local' if DEFAULT_REPO_LOCAL_DIR in str(store.store_path) else 'global',
    }
    store.register(entry)

    # Also update bundle_metadata.json inside the stored bundle
    meta_path = dest / 'bundle_metadata.json'
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
        except Exception:
            meta = {}
    else:
        meta = {}
    meta['bundle_id'] = bundle_id
    meta['title'] = title
    meta['slug'] = slug
    meta['repo_root'] = entry['repo_root']
    meta['branch'] = entry['branch']
    meta['head_commit'] = entry['head_commit']
    meta['tags'] = entry['tags']
    meta['stored_at'] = now
    meta_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')

    return entry
