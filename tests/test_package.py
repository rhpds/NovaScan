#!/usr/bin/env python3
"""Stage 1: Package Structure — imports, CLI commands, Python compat."""

import pytest
from pathlib import Path


class TestPackageStructure:

    def test_pyproject_exists(self, project_root):
        assert (project_root / "pyproject.toml").exists()

    def test_pyproject_has_cli_entry(self, project_root):
        content = (project_root / "pyproject.toml").read_text()
        assert "novascan" in content

    def test_all_modules_import(self):
        import novascan.cli
        import novascan.scanner
        import novascan.planner
        import novascan.catalog
        import novascan.output
        import novascan.detectors.llm_imports
        import novascan.detectors.model_names
        import novascan.detectors.k8s_manifests
        import novascan.detectors.concurrency

    def test_cli_has_scan_command(self):
        from novascan.cli import main
        assert "scan" in main.commands

    def test_cli_has_plan_command(self):
        from novascan.cli import main
        assert "plan" in main.commands

    def test_cli_has_validate_command(self):
        from novascan.cli import main
        assert "validate" in main.commands


class TestPythonCompat:

    def test_future_annotations(self, src_root):
        novascan_dir = src_root / "novascan"
        for py_file in novascan_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            content = py_file.read_text()
            assert "from __future__ import annotations" in content, (
                f"{py_file.relative_to(src_root)} missing future annotations"
            )
