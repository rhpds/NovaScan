#!/usr/bin/env python3
"""End-to-end: NovaScan scan → plan → generate → validate pipeline."""

import pytest
import yaml
from pathlib import Path

from novascan.scanner import scan_repo
from novascan.planner import recommend_tier
from novascan.generator import generate_agnosticv, write_agnosticv
from novascan.validator import compare_against_agnosticv

DEMO_REPO = Path("/Users/jkershaw/Documents/red_hat_intel_partner_demo")
LIFTOFF_REPO = Path("/Users/jkershaw/Documents/liftoff")


@pytest.fixture
def demo_scan():
    if not DEMO_REPO.exists():
        pytest.skip("Intel demo repo not available")
    return scan_repo(DEMO_REPO)


@pytest.fixture
def demo_plan(demo_scan):
    return recommend_tier(demo_scan, seats=1)


class TestE2EScan:

    def test_scan_finds_frameworks(self, demo_scan):
        assert len(demo_scan["frameworks_detected"]) > 0

    def test_scan_finds_models(self, demo_scan):
        assert len(demo_scan["models_detected"]) > 0

    def test_scan_finds_infrastructure(self, demo_scan):
        infra = demo_scan.get("infrastructure", {})
        assert infra.get("databases")
        assert infra.get("k8s_workloads", {}).get("total_workloads", 0) > 0

    def test_scan_finds_helm_chart(self, demo_scan):
        helm = demo_scan.get("infrastructure", {}).get("helm", {})
        assert helm.get("charts_found", 0) > 0


class TestE2EPlan:

    def test_recommends_tier(self, demo_plan):
        assert demo_plan["recommended_tier"] in ("pilot", "partner", "dedicated")

    def test_has_per_seat(self, demo_plan):
        assert "per_seat" in demo_plan
        assert demo_plan["per_seat"]["cpu_cores"] > 0

    def test_cpu_reasonable(self, demo_plan):
        cpu = demo_plan["per_seat"]["cpu_cores"]
        assert 4 <= cpu <= 40, f"CPU {cpu} seems unreasonable for a single-namespace demo"

    def test_has_topology(self, demo_plan):
        assert demo_plan["deployment_topology"] in ("namespace", "platform", "cnv")

    def test_detects_maas_models(self, demo_plan):
        maas = [m for m in demo_plan["models_detected"] if m.get("source") == "maas"]
        assert len(maas) >= 5


class TestE2EGenerate:

    def test_generates_valid_catalog(self, demo_plan, tmp_path):
        config = generate_agnosticv(
            demo_plan,
            repo_url="https://github.com/rhpds/red-hat-intel-partnership-demo",
            slug_override="intel-inference",
        )
        output = tmp_path / "generated"
        write_agnosticv(config, output)

        assert (output / "common.yaml").exists()
        assert (output / "dev.yaml").exists()
        assert (output / "test.yaml").exists()
        assert (output / "prod.yaml").exists()

    def test_generated_has_correct_slug(self, demo_plan, tmp_path):
        config = generate_agnosticv(demo_plan, slug_override="intel-inference")
        suffix = config["ocp4_workload_tenant_namespace_suffixes"][0]["suffix"]
        assert suffix == "intel-inference"

    def test_generated_has_workloads(self, demo_plan):
        config = generate_agnosticv(demo_plan)
        assert len(config["workloads"]) >= 4

    def test_generated_has_maas_models(self, demo_plan):
        config = generate_agnosticv(demo_plan)
        models = config.get("ocp4_workload_litellm_virtual_keys_models", [])
        assert len(models) >= 5

    def test_generated_has_production_fields(self, demo_plan):
        config = generate_agnosticv(
            demo_plan,
            repo_url="https://github.com/rhpds/red-hat-intel-partnership-demo",
        )
        assert "requester_email" in config
        assert "catalog_item_name" in config
        assert config.get("ocp4_workload_showroom_passthrough_user_data") is True
        meta = config.get("__meta__", {})
        assert "access_control" in meta


class TestE2EValidate:

    def test_validate_against_liftoff_tenant(self, demo_plan):
        tenant_path = LIFTOFF_REPO / "agnosticv/ai-qs-intel-inference-tenant/common.yaml"
        if not tenant_path.exists():
            pytest.skip("LiftOff repo not available")
        comparison = compare_against_agnosticv(demo_plan, tenant_path)
        assert comparison["actual_tier"] in ("pilot", "partner", "dedicated")
        assert "resource_deltas" in comparison

    def test_validate_against_liftoff_dedicated(self, demo_plan):
        ded_path = LIFTOFF_REPO / "agnosticv/ai-qs-intel-inference-dedicated/common.yaml"
        if not ded_path.exists():
            pytest.skip("LiftOff repo not available")
        comparison = compare_against_agnosticv(demo_plan, ded_path)
        assert comparison["tier_match"] is True, (
            f"Tier mismatch: recommended={comparison['recommended_tier']}, "
            f"actual={comparison['actual_tier']}"
        )
