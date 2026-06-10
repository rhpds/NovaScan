"""Validate novascan recommendations against existing agnosticv configs."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .parsing import parse_cpu, parse_mem_gb


def compare_against_agnosticv(capacity_plan: dict, agnosticv_path: Path) -> dict:
    """Compare a novascan capacity plan against an agnosticv config file."""
    agnosticv_path = Path(agnosticv_path)
    agnosticv = _load_agnosticv(agnosticv_path)

    actual_tier = _extract_tier(agnosticv)
    actual_quota = _extract_quota(agnosticv)
    actual_models = _extract_models(agnosticv)

    rec_tier = capacity_plan.get("recommended_tier", "unknown")
    rec_estimate = capacity_plan.get("resource_estimate", {})
    rec_overrides = capacity_plan.get("agnosticv_overrides", {})
    rec_models = [m["name"] for m in capacity_plan.get("models_detected", []) if m.get("source") == "maas"]

    resource_deltas = _compute_resource_deltas(rec_estimate, rec_overrides, actual_quota)
    model_coverage = _compute_model_coverage(rec_models, actual_models)

    return {
        "repo": capacity_plan.get("repo", ""),
        "agnosticv_path": str(agnosticv_path),
        "recommended_tier": rec_tier,
        "actual_tier": actual_tier,
        "tier_match": rec_tier == actual_tier,
        "resource_deltas": resource_deltas,
        "model_coverage": model_coverage,
        "tier_reasoning": capacity_plan.get("tier_reasoning", ""),
    }


def _load_agnosticv(path: Path) -> dict:
    """Load an agnosticv YAML file, stripping Jinja2/includes."""
    content = path.read_text(errors="ignore")
    cleaned = "\n".join(
        line for line in content.splitlines()
        if not line.strip().startswith("#include")
    )
    # Replace quoted Jinja2 expressions: "{{ ... }}" -> "__tpl__"
    cleaned = re.sub(r'"(\{\{[^}]*\}\})"', '"__tpl__"', cleaned)
    cleaned = re.sub(r"'(\{\{[^}]*\}\})'", "'__tpl__'", cleaned)
    # Replace bare Jinja2 expressions: {{ ... }} -> __tpl__
    cleaned = re.sub(r"\{\{[^}]*\}\}", "__tpl__", cleaned)
    # Replace Jinja2 blocks that might remain
    cleaned = re.sub(r"\{%[^%]*%\}", "", cleaned)
    try:
        return yaml.safe_load(cleaned) or {}
    except yaml.YAMLError:
        return {}


def _extract_tier(agnosticv: dict) -> str:
    """Extract the tier from an agnosticv config."""
    tier = agnosticv.get("intel_rh_inference_tier", "")
    if tier:
        return tier
    if agnosticv.get("intel_rh_inference_local_cpu_backend"):
        return "dedicated"
    workloads = agnosticv.get("workloads", [])
    workload_names = [w if isinstance(w, str) else w.get("name", "") for w in workloads]
    if any("cpu_inference" in w for w in workload_names):
        return "dedicated"
    if any("intel_rh_inference_demo" in w for w in workload_names):
        return "partner"
    if any("litellm_virtual_keys" in w for w in workload_names):
        return "pilot"
    return "unknown"


def _extract_quota(agnosticv: dict) -> dict:
    """Extract resource quota from agnosticv config."""
    quota = agnosticv.get("ocp4_workload_tenant_namespace_default_quota", {})
    if not quota:
        return {}
    return {
        "cpu": parse_cpu(quota.get("requests.cpu", "0")),
        "memory_gb": parse_mem_gb(quota.get("requests.memory", "0")),
        "storage_gb": parse_mem_gb(quota.get("requests.storage", "0")),
    }


def _extract_models(agnosticv: dict) -> list:
    """Extract model list from agnosticv LiteLLM config."""
    models = agnosticv.get("ocp4_workload_litellm_virtual_keys_models", [])
    cleaned = []
    for m in models:
        if isinstance(m, str) and not m.startswith("{{") and "__tpl__" not in m:
            cleaned.append(m)
    return cleaned



def _compute_resource_deltas(estimate: dict, overrides: dict, actual_quota: dict) -> dict:
    """Compute resource deltas between recommended and provisioned."""
    if not actual_quota:
        return {}

    rec_quota = overrides.get("ocp4_workload_tenant_namespace_default_quota", {})
    rec_cpu = parse_cpu(rec_quota.get("requests.cpu", str(estimate.get("cpu_cores", 0))))
    rec_mem = parse_mem_gb(rec_quota.get("requests.memory", f"{estimate.get('memory_gb', 0)}Gi"))
    rec_storage = parse_mem_gb(rec_quota.get("requests.storage", f"{estimate.get('storage_gb', 0)}Gi"))

    actual_cpu = actual_quota.get("cpu", 0)
    actual_mem = actual_quota.get("memory_gb", 0)
    actual_storage = actual_quota.get("storage_gb", 0)

    deltas = {}
    if actual_cpu or rec_cpu:
        deltas["cpu_cores"] = {
            "recommended": rec_cpu,
            "provisioned": actual_cpu,
            "delta": round(actual_cpu - rec_cpu, 2),
        }
    if actual_mem or rec_mem:
        deltas["memory_gb"] = {
            "recommended": round(rec_mem, 2),
            "provisioned": round(actual_mem, 2),
            "delta": round(actual_mem - rec_mem, 2),
        }
    if actual_storage or rec_storage:
        deltas["storage_gb"] = {
            "recommended": round(rec_storage, 2),
            "provisioned": round(actual_storage, 2),
            "delta": round(actual_storage - rec_storage, 2),
        }
    return deltas


def _compute_model_coverage(recommended_models: list, actual_models: list) -> dict:
    """Compare model lists between scan and agnosticv."""
    rec_set = set(recommended_models)
    actual_set = set(actual_models)
    return {
        "recommended_models": sorted(rec_set),
        "provisioned_models": sorted(actual_set),
        "missing_from_agnosticv": sorted(rec_set - actual_set),
        "extra_in_agnosticv": sorted(actual_set - rec_set),
    }
