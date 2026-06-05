"""Tests for the NovaScan scanner."""

import pytest
from pathlib import Path

from novascan.scanner import scan_repo


@pytest.fixture
def project_root():
    return Path(__file__).parent.parent.parent


def test_scan_self(project_root):
    """NovaScan should be able to scan the parent Intel demo repo."""
    demo_repo = project_root
    if not (demo_repo / "gateway").exists():
        pytest.skip("Not running from within the Intel demo repo")
    results = scan_repo(demo_repo)
    assert results["files_scanned"] > 0
    assert len(results["models_detected"]) > 0
    assert "transformers" in results["frameworks_detected"] or "openai" in results["frameworks_detected"]


def test_scan_empty_dir(tmp_path):
    """Scanning an empty directory should not crash."""
    results = scan_repo(tmp_path)
    assert results["files_scanned"] == 0
    assert results["models_detected"] == []
