#!/usr/bin/env python3
"""Tests for agnosticv catalog item generation."""

import pytest
import yaml
from pathlib import Path

from checksum.generator import generate_agnosticv, write_agnosticv


@pytest.fixture
def sample_plan():
    return {
        "repo": "/tmp/my-demo",
        "recommended_tier": "partner",
        "resource_estimate": {
            "cpu_cores": 12,
            "memory_gb": 24,
            "storage_gb": 50,
            "gpu_count": 0,
            "maas_rpm_estimate": 30,
            "local_inference": False,
        },
        "models_detected": [
            {"name": "granite-2b-cpu", "source": "maas", "params_b": 2, "hardware": ["cpu"]},
            {"name": "llama-scout-17b", "source": "maas", "params_b": 17, "hardware": ["gpu"]},
        ],
        "infrastructure": {
            "helm": {"deploy_method": "helm-via-make"},
        },
    }


class TestGenerateAgnosticv:

    def test_produces_namespace_config(self, sample_plan):
        config = generate_agnosticv(sample_plan)
        assert config["config"] == "namespace"
        assert config["cloud_provider"] == "none"

    def test_has_workloads(self, sample_plan):
        config = generate_agnosticv(sample_plan)
        assert len(config["workloads"]) >= 4
        assert any("tenant_namespace" in w for w in config["workloads"])
        assert any("litellm" in w for w in config["workloads"])

    def test_quotas_right_sized(self, sample_plan):
        config = generate_agnosticv(sample_plan)
        quota = config["ocp4_workload_tenant_namespace_default_quota"]
        assert int(quota["requests.cpu"]) == 12
        assert int(quota["limits.cpu"]) == 24

    def test_maas_models_populated(self, sample_plan):
        config = generate_agnosticv(sample_plan)
        models = config["ocp4_workload_litellm_virtual_keys_models"]
        assert "granite-2b-cpu" in models
        assert "llama-scout-17b" in models

    def test_has_meta(self, sample_plan):
        config = generate_agnosticv(sample_plan)
        meta = config["__meta__"]
        assert "asset_uuid" in meta
        assert "catalog" in meta
        assert "deployer" in meta

    def test_helm_make_params(self, sample_plan):
        config = generate_agnosticv(sample_plan, repo_url="https://github.com/rh-ai-quickstart/my-demo")
        assert config["quickstart_deploy_via_make_repo_url"] == "https://github.com/rh-ai-quickstart/my-demo"
        assert config["quickstart_deploy_via_make_directory"] == "helm"

    def test_namespace_suffix_from_repo_name(self, sample_plan):
        config = generate_agnosticv(sample_plan)
        suffix = config["ocp4_workload_tenant_namespace_suffixes"][0]["suffix"]
        assert suffix == "my-demo"


class TestWriteAgnosticv:

    def test_writes_all_files(self, sample_plan, tmp_path):
        config = generate_agnosticv(sample_plan)
        output_dir = tmp_path / "test-catalog"
        write_agnosticv(config, output_dir)

        assert (output_dir / "common.yaml").exists()
        assert (output_dir / "dev.yaml").exists()
        assert (output_dir / "test.yaml").exists()
        assert (output_dir / "prod.yaml").exists()

    def test_common_yaml_has_includes(self, sample_plan, tmp_path):
        config = generate_agnosticv(sample_plan)
        output_dir = tmp_path / "test-catalog"
        write_agnosticv(config, output_dir)
        content = (output_dir / "common.yaml").read_text()
        assert "#include /includes/sandbox-api.yaml" in content
        assert "#include /includes/secrets/litemaas-master_api.yaml" in content

    def test_stage_yamls_have_sandbox(self, sample_plan, tmp_path):
        config = generate_agnosticv(sample_plan)
        output_dir = tmp_path / "test-catalog"
        write_agnosticv(config, output_dir)

        for stage in ["dev", "test", "prod"]:
            data = yaml.safe_load((output_dir / f"{stage}.yaml").read_text())
            sandboxes = data["__meta__"]["sandboxes"]
            assert sandboxes[0]["kind"] == "OcpSandbox"
            assert sandboxes[0]["cloud_selector"]["purpose"] == stage
