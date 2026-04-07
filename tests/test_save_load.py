"""Smoke tests for the save/load/list/show workflow."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

CLI = 'context-handoff-bundle'
REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_NOTES = REPO_ROOT / 'examples' / 'sample-notes.md'


def run_cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, '-m', 'context_handoff_bundle.cli', *args],
        capture_output=True, text=True,
        cwd=cwd or str(REPO_ROOT),
        env={**os.environ, 'PYTHONPATH': str(REPO_ROOT / 'src')},
    )


@pytest.fixture
def tmp_store(tmp_path):
    """Create a temp global store and patch the default."""
    store_dir = tmp_path / 'test-store'
    store_dir.mkdir()
    return store_dir


class TestSaveCommand:
    def test_save_minimal(self):
        """Save with just a title produces a valid bundle."""
        result = run_cli('save', '--title', 'Test Bundle', '--global')
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data['saved'] is True
        assert data['bundle_id']
        assert data['quality'] in ('strong', 'acceptable', 'weak')
        # Clean up
        bundle_path = Path(data['path'])
        if bundle_path.exists():
            shutil.rmtree(bundle_path)

    def test_save_with_notes(self):
        """Save from notes file produces richer bundle."""
        if not SAMPLE_NOTES.exists():
            pytest.skip('sample-notes.md not found')
        result = run_cli(
            'save', '--title', 'Notes Test', '--notes', str(SAMPLE_NOTES), '--global'
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data['saved'] is True
        bundle_path = Path(data['path'])
        if bundle_path.exists():
            shutil.rmtree(bundle_path)

    def test_save_with_tags(self):
        """Tags are preserved in saved bundle."""
        result = run_cli(
            'save', '--title', 'Tagged', '--tag', 'test', '--tag', 'smoke', '--global'
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data['saved'] is True
        bundle_path = Path(data['path'])
        if bundle_path.exists():
            shutil.rmtree(bundle_path)


class TestListCommand:
    def test_list_returns_output(self):
        """List command runs without error."""
        result = run_cli('list', '--global-only')
        assert result.returncode == 0


class TestShowCommand:
    def test_show_latest(self):
        """Show latest bundle works."""
        # Save one first
        save_result = run_cli('save', '--title', 'Show Test', '--global')
        if save_result.returncode != 0:
            pytest.skip('Save failed')
        save_data = json.loads(save_result.stdout)

        result = run_cli('show', 'latest', '--json')
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert 'entry' in data
        assert 'quality' in data

        # Clean up
        bundle_path = Path(save_data['path'])
        if bundle_path.exists():
            shutil.rmtree(bundle_path)


class TestLoadCommand:
    def test_load_latest(self):
        """Load latest produces resume text."""
        # Save one first
        save_result = run_cli('save', '--title', 'Load Test', '--global')
        if save_result.returncode != 0:
            pytest.skip('Save failed')
        save_data = json.loads(save_result.stdout)

        result = run_cli('load', 'latest')
        assert result.returncode == 0, result.stderr
        assert 'Context Handoff' in result.stdout

        # Clean up
        bundle_path = Path(save_data['path'])
        if bundle_path.exists():
            shutil.rmtree(bundle_path)

    def test_load_by_id(self):
        """Load by exact bundle ID resolves correctly."""
        save_result = run_cli('save', '--title', 'ID Test', '--slug', 'id-test', '--global')
        if save_result.returncode != 0:
            pytest.skip('Save failed')
        save_data = json.loads(save_result.stdout)
        bundle_id = save_data['bundle_id']

        result = run_cli('load', bundle_id)
        assert result.returncode == 0, result.stderr
        assert 'ID Test' in result.stdout

        # Clean up
        bundle_path = Path(save_data['path'])
        if bundle_path.exists():
            shutil.rmtree(bundle_path)

    def test_load_nonexistent(self):
        """Load with bogus query fails gracefully."""
        result = run_cli('load', 'definitely-does-not-exist-xyz123')
        assert result.returncode == 1
        assert 'error' in result.stdout.lower() or 'no bundle' in result.stdout.lower()


class TestScoreCommand:
    def test_score_example_bundle(self):
        """Score an existing example bundle."""
        example = REPO_ROOT / 'examples' / '2026-04-06-public-prototype'
        if not example.exists():
            pytest.skip('Example bundle not found')
        result = run_cli('score', str(example))
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert 'overall' in data
        assert 'score' in data
        assert 'dimensions' in data


class TestValidateCommand:
    def test_validate_example(self):
        """Validate an existing example bundle."""
        example = REPO_ROOT / 'examples' / '2026-04-06-public-prototype'
        if not example.exists():
            pytest.skip('Example bundle not found')
        result = run_cli('validate', str(example))
        assert result.returncode == 0, result.stderr


class TestEndToEnd:
    def test_save_list_show_load_cycle(self):
        """Full save -> list -> show -> load cycle."""
        # Save
        save_result = run_cli('save', '--title', 'E2E Test', '--slug', 'e2e-test', '--global')
        assert save_result.returncode == 0, save_result.stderr
        save_data = json.loads(save_result.stdout)
        bundle_id = save_data['bundle_id']

        try:
            # List
            list_result = run_cli('list', '--global-only')
            assert list_result.returncode == 0
            assert 'e2e-test' in list_result.stdout.lower() or 'E2E Test' in list_result.stdout

            # Show
            show_result = run_cli('show', bundle_id, '--json')
            assert show_result.returncode == 0, show_result.stderr
            show_data = json.loads(show_result.stdout)
            assert show_data['entry']['id'] == bundle_id

            # Load
            load_result = run_cli('load', bundle_id)
            assert load_result.returncode == 0, load_result.stderr
            assert 'E2E Test' in load_result.stdout
        finally:
            # Clean up
            bundle_path = Path(save_data['path'])
            if bundle_path.exists():
                shutil.rmtree(bundle_path)
