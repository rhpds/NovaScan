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


SHARED_INFRA_OVERHEAD = {
    "cpu": 8,
    "memory_gb": 32,
    "description": "Keycloak + OpenShift AI + ArgoCD + console embed",
}

WORKER_SIZES = [
    {"cores": 16, "memory_gb": 64},
    {"cores": 32, "memory_gb": 128},
    {"cores": 64, "memory_gb": 256},
    {"cores": 96, "memory_gb": 384},
    {"cores": 128, "memory_gb": 512},
]


def recommend_tier(scan_results: dict, seats: int = 1) -> dict:
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

    cost_analysis = _build_cost_analysis(models, seats)

    result = {
        "repo": scan_results.get("repo", ""),
        "recommended_tier": tier,
        "tier_reasoning": reasoning,
        "deployment_topology": topology,
        "infrastructure": infra_summary,
        "per_seat": {
            "cpu_cores": cpu_cores,
            "memory_gb": memory_gb,
            "storage_gb": estimate.get("storage_gb", 20),
        },
        "cost_analysis": cost_analysis,
        "resource_estimate": estimate,
        "models_detected": models,
        "agnosticv_overrides": _generate_overrides(tier, estimate, models),
    }

    if seats > 1:
        result["lab_capacity"] = _plan_lab_capacity(estimate, seats)

    warnings = _check_warnings(estimate, seats)
    if warnings:
        result["warnings"] = warnings

    return result


def _plan_lab_capacity(per_seat: dict, seats: int) -> dict:
    """Calculate total cluster resources for a multi-seat lab."""
    seat_cpu = per_seat.get("cpu_cores", 4)
    seat_mem = per_seat.get("memory_gb", 8)
    seat_storage = per_seat.get("storage_gb", 20)

    total_cpu = (seat_cpu * seats) + SHARED_INFRA_OVERHEAD["cpu"]
    total_mem = (seat_mem * seats) + SHARED_INFRA_OVERHEAD["memory_gb"]
    total_storage = seat_storage * seats

    maas_rpm = per_seat.get("maas_rpm_estimate", 10) * seats

    worker_size = _pick_worker_size(total_cpu, total_mem)
    worker_count = max(
        _ceil_div(total_cpu, worker_size["cores"]),
        _ceil_div(total_mem, worker_size["memory_gb"]),
    )
    worker_count = max(worker_count, 2)

    return {
        "seats": seats,
        "total_cpu": total_cpu,
        "total_memory_gb": total_mem,
        "total_storage_gb": total_storage,
        "shared_infra_overhead": SHARED_INFRA_OVERHEAD["description"],
        "maas_rpm_total": maas_rpm,
        "cluster_sizing": {
            "worker_count": worker_count,
            "worker_cores": worker_size["cores"],
            "worker_memory_gb": worker_size["memory_gb"],
            "total_cluster_cpu": worker_count * worker_size["cores"],
            "total_cluster_memory_gb": worker_count * worker_size["memory_gb"],
        },
        "sandbox_config": {
            "max_placements": seats,
            "max_cpu_usage_percentage": 100,
            "max_memory_usage_percentage": 80,
        },
        "agnosticv_cluster_overrides": {
            "worker_instance_count": worker_count,
            "ai_workers_cores": worker_size["cores"],
            "ai_workers_memory": f"{worker_size['memory_gb']}Gi",
        },
    }


def _pick_worker_size(total_cpu: float, total_mem: float) -> dict:
    """Pick the smallest worker size that keeps count reasonable."""
    for size in WORKER_SIZES:
        count = max(
            _ceil_div(total_cpu, size["cores"]),
            _ceil_div(total_mem, size["memory_gb"]),
        )
        if count <= 8:
            return size
    return WORKER_SIZES[-1]


def _ceil_div(a: float, b: float) -> int:
    return int(-(-a // b))


MAAS_RPM_LIMIT = 90


def _check_warnings(estimate: dict, seats: int) -> list[str]:
    """Check for provisioning warnings."""
    warnings = []
    rpm = estimate.get("maas_rpm_estimate", 0)
    total_rpm = rpm * seats

    if total_rpm > MAAS_RPM_LIMIT:
        warnings.append(
            f"MAAS rate limit risk: {total_rpm} RPM estimated across {seats} seats "
            f"exceeds MAAS limit of {MAAS_RPM_LIMIT} RPM. Consider dedicated inference pods "
            f"or request a higher MAAS quota."
        )

    if estimate.get("gpu_count", 0) > 0 and seats > 10:
        warnings.append(
            f"GPU sharing: {seats} seats sharing GPU-class models via MAAS. "
            f"Expect increased latency at peak concurrency."
        )

    return warnings


def _build_cost_analysis(models: list, seats: int) -> dict:
    """Build cost analysis from detected models."""
    from .catalog import estimate_session_cost, estimate_event_cost, get_consolidation_warnings

    if not models:
        return {"total_per_session": 0, "total_event": 0, "approval_tier": 1, "models": []}

    model_costs = []
    total_session = 0
    max_tier = 1
    maas_models = [m for m in models if m.get("source") == "maas"]

    for m in maas_models:
        # Guess interaction pattern from model type
        name = m["name"]
        if "embed" in name.lower() or "nomic" in name.lower():
            pattern = "embedding"
            requests = 50
        elif m.get("params_b", 0) > 100:
            pattern = "agentic"
            requests = 10
        elif m.get("params_b", 0) > 10:
            pattern = "chat_context"
            requests = 20
        else:
            pattern = "simple_qa"
            requests = 20

        cost = estimate_session_cost(name, pattern, requests)
        model_costs.append(cost)
        total_session += cost["session_cost"]
        max_tier = max(max_tier, cost["approval_tier"])

    # Event cost
    overhead = 1.15
    event_cost = total_session * seats * overhead if seats > 1 else total_session

    # Consolidation warnings
    all_model_names = [m["name"] for m in models]
    consolidation = get_consolidation_warnings(all_model_names)

    # Cost-saving recommendations
    recommendations = []
    expensive = [c for c in model_costs if c["session_cost"] > 0.50]
    for c in expensive:
        if c.get("replacement"):
            alt = estimate_session_cost(c["replacement"], "chat_context", 20)
            savings = c["session_cost"] - alt["session_cost"]
            if savings > 0:
                recommendations.append(
                    f"Replace {c['model']} (${c['session_cost']:.2f}/session) with "
                    f"{c['replacement']} (${alt['session_cost']:.4f}/session) — "
                    f"save ${savings:.2f}/user, ${savings * seats * overhead:.0f}/event"
                )
        elif c["session_cost"] > 1.00:
            recommendations.append(
                f"{c['model']} costs ${c['session_cost']:.2f}/user/session — "
                f"consider qwen3-14b at ~$0.02/session (open model, 100x cheaper)"
            )

    return {
        "per_session_cost": round(total_session, 4),
        "event_cost": round(event_cost, 2) if seats > 1 else None,
        "seats": seats if seats > 1 else None,
        "approval_tier": max_tier,
        "approval_label": {1: "Self-Serve", 2: "Justified", 3: "Exceptional"}.get(max_tier, "?"),
        "model_costs": [
            {"model": c["model"], "pattern": c["pattern"], "session_cost": c["session_cost"],
             "status": c["status"], "replacement": c.get("replacement")}
            for c in model_costs
        ],
        "consolidation_warnings": consolidation,
        "cost_recommendations": recommendations,
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
