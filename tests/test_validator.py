#!/usr/bin/env python3
"""Tests for agnosticv validator."""

import pytest
from pathlib import Path

from novascan.validator import (
    _extract_tier,
    _extract_quota,
    _extract_models,
    _load_agnosticv,
)
from novascan.parsing import parse_cpu, parse_mem_gb


class TestExtractTier:

    def test_explicit_tier(self):
        assert _extract_tier({"intel_rh_inference_tier": "partner"}) == "partner"

    def test_dedicated_from_local_cpu(self):
        assert _extract_tier({"intel_rh_inference_local_cpu_backend": True}) == "dedicated"

    def test_dedicated_from_workloads(self):
        assert _extract_tier({"workloads": ["some.cpu_inference.role"]}) == "dedicated"

    def test_partner_from_workloads(self):
        assert _extract_tier({"workloads": ["some.intel_rh_inference_demo.role"]}) == "partner"

    def test_pilot_from_workloads(self):
        assert _extract_tier({"workloads": ["some.litellm_virtual_keys.role"]}) == "pilot"

    def test_unknown_empty(self):
        assert _extract_tier({}) == "unknown"


class TestExtractQuota:

    def test_parses_quota(self):
        quota = _extract_quota({
            "ocp4_workload_tenant_namespace_default_quota": {
                "requests.cpu": "12",
                "requests.memory": "32Gi",
                "requests.storage": "50Gi",
            }
        })
        assert quota["cpu"] == 12.0
        assert quota["memory_gb"] == 32.0
        assert quota["storage_gb"] == 50.0

    def test_empty_without_quota(self):
        assert _extract_quota({}) == {}


class TestExtractModels:

    def test_extracts_model_list(self):
        models = _extract_models({
            "ocp4_workload_litellm_virtual_keys_models": [
                "granite-2b-cpu",
                "{{ some_var }}",
                "llama-scout-17b",
            ]
        })
        assert models == ["granite-2b-cpu", "llama-scout-17b"]

    def test_empty_without_models(self):
        assert _extract_models({}) == []


class TestParseCpuStr:

    def test_whole_number(self):
        assert parse_cpu("12") == 12.0

    def test_quoted(self):
        assert parse_cpu('"40"') == 40.0

    def test_millicores(self):
        assert parse_cpu("500m") == 0.5

    def test_zero(self):
        assert parse_cpu("0") == 0.0


class TestParseMemStr:

    def test_gi(self):
        assert parse_mem_gb("64Gi") == 64.0

    def test_mi(self):
        assert abs(parse_mem_gb("512Mi") - 0.5) < 0.01

    def test_ti(self):
        assert parse_mem_gb("1Ti") == 1024.0

    def test_bare(self):
        assert parse_mem_gb("0") == 0.0


class TestLoadAgnosticv:

    def test_loads_with_jinja(self, tmp_path):
        f = tmp_path / "common.yaml"
        f.write_text("""---
#include /includes/sandbox-api.yaml
config: namespace
namespace: "user-{{ guid }}-demo"
password: "{{ common_password }}"
workloads:
  - some.workload
""")
        data = _load_agnosticv(f)
        assert data["config"] == "namespace"
        assert isinstance(data["workloads"], list)
