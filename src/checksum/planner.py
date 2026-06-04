"""Capacity planning and tier recommendation."""

from __future__ import annotations


TIER_THRESHOLDS = {
    "pilot": {
        "max_cpu": 0,
        "max_memory_gb": 0,
        "local_inference": False,
        "description": "MAAS API key only — no cluster resources",
    },
    "partner": {
        "max_cpu": 20,
        "max_memory_gb": 32,
        "local_inference": False,
        "description": "Namespace with gateway + frontend + postgres, inference via MAAS",
    },
    "dedicated": {
        "max_cpu": 40,
        "max_memory_gb": 64,
        "local_inference": True,
        "description": "Full stack with local CPU inference pods in tenant namespace",
    },
}


def recommend_tier(scan_results: dict) -> dict:
    """Recommend an RHDP provisioning tier based on scan results."""
    estimate = scan_results.get("resource_estimate", {})
    models = scan_results.get("models_detected", [])
    frameworks = scan_results.get("frameworks_detected", [])
    infra = scan_results.get("infrastructure", {})

    needs_local = estimate.get("local_inference", False)
    needs_gateway = _needs_gateway(scan_results)
    cpu_cores = estimate.get("cpu_cores", 0)
    memory_gb = estimate.get("memory_gb", 0)

    if needs_local or cpu_cores > 20 or memory_gb > 32:
        tier = "dedicated"
        reasoning = _build_reasoning("dedicated", estimate, models, frameworks)
    elif needs_gateway or models or frameworks:
        tier = "partner"
        reasoning = _build_reasoning("partner", estimate, models, frameworks)
    else:
        tier = "pilot"
        reasoning = "No local inference or heavy compute detected. MAAS API key is sufficient."

    topology = infra.get("topology", "namespace") if infra else "namespace"
    infra_summary = _build_infra_summary(infra) if infra else {}

    return {
        "repo": scan_results.get("repo", ""),
        "recommended_tier": tier,
        "tier_reasoning": reasoning,
        "deployment_topology": topology,
        "infrastructure": infra_summary,
        "resource_estimate": estimate,
        "models_detected": models,
        "agnosticv_overrides": _generate_overrides(tier, estimate, models),
    }


def _needs_gateway(scan_results: dict) -> bool:
    """Check if the demo needs a gateway/frontend deployment."""
    frameworks = scan_results.get("frameworks_detected", [])
    models = scan_results.get("models_detected", [])
    return bool(frameworks) or bool(models)


def _build_reasoning(tier: str, estimate: dict, models: list, frameworks: list) -> str:
    model_count = len(models)
    gpu_models = [m for m in models if "gpu" in m.get("hardware", [])]
    cpu_models = [m for m in models if "cpu" in m.get("hardware", [])]

    parts = []
    if model_count:
        parts.append(f"{model_count} models detected ({len(cpu_models)} CPU, {len(gpu_models)} GPU)")
    if frameworks:
        parts.append(f"Frameworks: {', '.join(frameworks)}")
    if estimate.get("local_inference"):
        parts.append("Local inference deployment detected")
    parts.append(f"Est. {estimate.get('cpu_cores', '?')} CPU cores, {estimate.get('memory_gb', '?')}GB memory")

    return ". ".join(parts) + "."


def _generate_overrides(tier: str, estimate: dict, models: list) -> dict:
    """Generate agnosticv variable overrides for the recommended tier."""
    overrides = {}

    if tier in ("partner", "dedicated"):
        cpu = max(estimate.get("cpu_cores", 8), 8)
        mem = max(estimate.get("memory_gb", 16), 16)
        overrides["ocp4_workload_tenant_namespace_default_quota"] = {
            "limits.cpu": str(cpu * 2),
            "requests.cpu": str(cpu),
            "limits.memory": f"{mem * 2}Gi",
            "requests.memory": f"{mem}Gi",
            "requests.storage": f"{estimate.get('storage_gb', 50)}Gi",
        }

    maas_models = [m["name"] for m in models if m.get("source") == "maas"]
    if maas_models:
        overrides["ocp4_workload_litellm_virtual_keys_models"] = maas_models

    if tier == "dedicated":
        overrides["intel_rh_inference_local_cpu_backend"] = True

    return overrides


def _build_infra_summary(infra: dict) -> dict:
    """Build a concise infrastructure summary for the plan output."""
    summary = {}

    containers = infra.get("containers", {})
    if containers.get("containerfiles", 0) > 0:
        summary["container_images"] = containers["containerfiles"]

    dbs = infra.get("databases", [])
    if dbs:
        summary["databases"] = dbs

    mqs = infra.get("message_queues", [])
    if mqs:
        summary["message_queues"] = mqs

    vms = infra.get("vms", {})
    if vms.get("needs_cnv"):
        summary["cnv_vms"] = vms["vm_count"]

    k8s = infra.get("k8s_workloads", {})
    if k8s.get("total_workloads", 0) > 0:
        summary["k8s_workloads"] = k8s["total_workloads"]
        summary["k8s_services"] = k8s.get("services", 0)
        summary["k8s_pvcs"] = k8s.get("pvcs", 0)

    frontends = infra.get("frontends", 0)
    if frontends > 0:
        summary["frontends"] = frontends

    return summary
