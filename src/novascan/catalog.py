"""Model catalog — maps model names to hardware specs, Vertex AI pricing, and approval tiers."""

from __future__ import annotations

from pathlib import Path

import yaml

# Vertex AI pricing per million tokens (June 2026)
# Source: RHDP Vertex AI LLM Access Guidelines v1.0

BUILTIN_CATALOG = {
    # Tier 1: Self-Serve (< $0.10/user/session)
    "qwen3-14b": {
        "params_b": 14, "hardware": ["gpu"], "memory_gb": 28, "throughput_tps": 37,
        "vertex_ai_id": "qwen/qwen3-14b-instruct-maas",
        "input_price_per_m": 0.15, "output_price_per_m": 0.60,
        "tier": 1, "status": "active",
    },
    "llama-scout-17b": {
        "params_b": 17, "hardware": ["gpu"], "memory_gb": 34, "throughput_tps": 60,
        "vertex_ai_id": "meta/llama-4-scout-17b-16e-instruct-maas",
        "input_price_per_m": 0.15, "output_price_per_m": 0.60,
        "tier": 1, "status": "active",
    },
    "nomic-embed-text-v1-5": {
        "params_b": 0.14, "hardware": ["cpu"], "memory_gb": 1, "throughput_tps": 200,
        "vertex_ai_id": "nomic-embed-text-v1-5",
        "input_price_per_m": 0.10, "output_price_per_m": 0,
        "tier": 1, "status": "active",
    },
    "Llama-Guard-3-1B": {
        "params_b": 1, "hardware": ["cpu"], "memory_gb": 2, "throughput_tps": 100,
        "vertex_ai_id": "meta/llama-guard-*-maas",
        "input_price_per_m": 0.15, "output_price_per_m": 0.60,
        "tier": 1, "status": "active",
    },

    # Tier 2: Justified ($0.10 – $2.00/user/session)
    "qwen3-235b": {
        "params_b": 235, "hardware": ["gpu"], "memory_gb": 64, "throughput_tps": 15,
        "vertex_ai_id": "qwen/qwen3-235b-a22b-instruct-maas",
        "input_price_per_m": 0.15, "output_price_per_m": 0.60,
        "tier": 2, "status": "active",
    },
    "deepseek-r1-distill-qwen-14b": {
        "params_b": 14, "hardware": ["gpu"], "memory_gb": 28, "throughput_tps": 55,
        "vertex_ai_id": "deepseek/deepseek-r1-*-maas",
        "input_price_per_m": 0.15, "output_price_per_m": 0.60,
        "tier": 2, "status": "retiring", "replacement": "qwen3-14b", "retirement_month": "Month 2-3",
    },
    "claude-sonnet-4-6": {
        "params_b": 0, "hardware": ["gpu"], "memory_gb": 0, "throughput_tps": 80,
        "vertex_ai_id": "claude-sonnet-4@latest",
        "input_price_per_m": 3.00, "output_price_per_m": 15.00,
        "tier": 2, "status": "retiring", "replacement": "qwen3-14b", "retirement_month": "Month 3-4",
    },
    "gpt-oss-120b": {
        "params_b": 120, "hardware": ["gpu"], "memory_gb": 240, "throughput_tps": 20,
        "vertex_ai_id": "gpt-oss-120b",
        "input_price_per_m": 0.15, "output_price_per_m": 0.60,
        "tier": 2, "status": "retiring", "replacement": "qwen3-235b", "retirement_month": "Month 2-3",
    },

    # Tier 3: Exceptional (> $2.00/user/session, platform approval required)
    "claude-opus-4-6": {
        "params_b": 0, "hardware": ["gpu"], "memory_gb": 0, "throughput_tps": 40,
        "vertex_ai_id": "claude-opus-4@latest",
        "input_price_per_m": 15.00, "output_price_per_m": 75.00,
        "tier": 3, "status": "active",
    },

    # On-cluster models (infra-based cost, not per-token)
    "granite-3-2-8b-instruct": {
        "params_b": 8, "hardware": ["cpu", "gpu"], "memory_gb": 16, "throughput_tps": 12,
        "vertex_ai_id": None, "access": "on-cluster",
        "input_price_per_m": 0, "output_price_per_m": 0,
        "tier": 1, "status": "active",
    },
    "granite-4-0-h-tiny": {
        "params_b": 1, "hardware": ["cpu"], "memory_gb": 2, "throughput_tps": 40,
        "vertex_ai_id": None, "access": "on-cluster",
        "input_price_per_m": 0, "output_price_per_m": 0,
        "tier": 1, "status": "retiring", "replacement": "granite-3-2-8b-instruct", "retirement_month": "Month 4-5",
    },
    "granite-2b-cpu": {
        "params_b": 2, "hardware": ["cpu"], "memory_gb": 4, "throughput_tps": 26,
        "input_price_per_m": 0, "output_price_per_m": 0,
        "tier": 1, "status": "active",
    },

    # Retiring models
    "codellama-7b-instruct": {
        "params_b": 7, "hardware": ["cpu", "gpu"], "memory_gb": 14, "throughput_tps": 15,
        "input_price_per_m": 0.15, "output_price_per_m": 0.60,
        "tier": 1, "status": "retired", "replacement": "llama-scout-17b",
    },
    "microsoft-phi-4": {
        "params_b": 14, "hardware": ["gpu"], "memory_gb": 28, "throughput_tps": 47,
        "input_price_per_m": 0.15, "output_price_per_m": 0.60,
        "tier": 1, "status": "retired", "replacement": "qwen3-14b",
    },
    "phi3-mini-cpu": {
        "params_b": 3.8, "hardware": ["cpu"], "memory_gb": 8, "throughput_tps": 30,
        "input_price_per_m": 0, "output_price_per_m": 0,
        "tier": 1, "status": "active",
    },
    "qwen25-3b-cpu": {
        "params_b": 3, "hardware": ["cpu"], "memory_gb": 6, "throughput_tps": 24,
        "input_price_per_m": 0, "output_price_per_m": 0,
        "tier": 1, "status": "active",
    },
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0": {
        "params_b": 1.1, "hardware": ["cpu"], "memory_gb": 2.5, "throughput_tps": 35,
        "input_price_per_m": 0, "output_price_per_m": 0,
        "tier": 1, "status": "active",
    },
    "minimax-m2": {
        "params_b": 0, "hardware": ["gpu"], "memory_gb": 0, "throughput_tps": 50,
        "vertex_ai_id": "minimax-*-maas",
        "input_price_per_m": 0.15, "output_price_per_m": 0.60,
        "tier": 2, "status": "retiring", "replacement": "qwen3-235b", "retirement_month": "Month 2-3",
    },
}

MAAS_MODELS = {
    "codellama-7b-instruct", "deepseek-r1-distill-qwen-14b",
    "llama-scout-17b", "microsoft-phi-4", "qwen3-14b", "nomic-embed-text-v1-5",
    "qwen3-235b", "claude-opus-4-6", "claude-sonnet-4-6", "gpt-oss-120b",
    "Llama-Guard-3-1B", "minimax-m2",
}

TIER_LABELS = {1: "Self-Serve", 2: "Justified", 3: "Exceptional"}
TIER_THRESHOLDS = {1: 0.10, 2: 2.00, 3: float("inf")}

# Interaction pattern token estimates (from RHDP guidelines)
INTERACTION_PATTERNS = {
    "simple_qa": {"input": 750, "output": 350, "label": "Simple Q&A"},
    "chat_context": {"input": 2250, "output": 1000, "label": "Chat with context"},
    "rag": {"input": 3500, "output": 1250, "label": "RAG with documents"},
    "code_gen": {"input": 5000, "output": 2500, "label": "Code generation"},
    "agentic": {"input": 6500, "output": 3000, "label": "Agentic / tool-calling"},
    "embedding": {"input": 640, "output": 0, "label": "Embedding only"},
}


def estimate_session_cost(model_name: str, pattern: str = "chat_context",
                          requests_per_session: int = 20) -> dict:
    """Estimate per-user session cost for a model + interaction pattern."""
    info = BUILTIN_CATALOG.get(model_name, BUILTIN_CATALOG.get(_normalize_name(model_name), {}))
    tokens = INTERACTION_PATTERNS.get(pattern, INTERACTION_PATTERNS["chat_context"])

    input_rate = info.get("input_price_per_m", 0)
    output_rate = info.get("output_price_per_m", 0)

    cost_per_request = (
        (tokens["input"] / 1_000_000) * input_rate +
        (tokens["output"] / 1_000_000) * output_rate
    )
    session_cost = cost_per_request * requests_per_session

    tier = info.get("tier", 1)
    if session_cost < 0.10:
        approval_tier = 1
    elif session_cost < 2.00:
        approval_tier = 2
    else:
        approval_tier = 3

    return {
        "model": model_name,
        "pattern": tokens["label"],
        "cost_per_request": round(cost_per_request, 6),
        "session_cost": round(session_cost, 4),
        "approval_tier": approval_tier,
        "approval_label": TIER_LABELS[approval_tier],
        "model_tier": tier,
        "status": info.get("status", "unknown"),
        "replacement": info.get("replacement"),
        "retirement_month": info.get("retirement_month"),
    }


def estimate_event_cost(model_name: str, users: int, pattern: str = "chat_context",
                        requests_per_session: int = 20) -> dict:
    """Estimate total event cost for N users."""
    session = estimate_session_cost(model_name, pattern, requests_per_session)
    overhead = 1.15  # retries + regional premium
    total = session["session_cost"] * users * overhead
    return {
        **session,
        "users": users,
        "event_cost": round(total, 2),
        "overhead_factor": overhead,
    }


def get_consolidation_warnings(model_names: list) -> list:
    """Return warnings for models on the retirement/consolidation roadmap."""
    warnings = []
    for name in model_names:
        key = _normalize_name(name)
        info = BUILTIN_CATALOG.get(key, BUILTIN_CATALOG.get(name, {}))
        status = info.get("status", "unknown")
        if status == "retired":
            warnings.append({
                "model": name,
                "severity": "high",
                "message": f"{name} is RETIRED. Replace with {info.get('replacement', '?')}.",
            })
        elif status == "retiring":
            warnings.append({
                "model": name,
                "severity": "medium",
                "message": f"{name} scheduled for retirement ({info.get('retirement_month', '?')}). "
                           f"Migrate to {info.get('replacement', '?')}.",
            })
    return warnings


def lookup_models(raw_models: list[dict]) -> list[dict]:
    """Enrich raw model detections with catalog info including pricing."""
    enriched = []
    seen = set()
    for entry in raw_models:
        name = entry["name"]
        if name in seen:
            continue
        seen.add(name)

        catalog_key = _normalize_name(name)
        info = BUILTIN_CATALOG.get(catalog_key, BUILTIN_CATALOG.get(name, {}))

        enriched.append({
            "name": name,
            "params_b": info.get("params_b", _guess_params(name)),
            "hardware": info.get("hardware", _guess_hardware(name)),
            "memory_gb": info.get("memory_gb", 0),
            "source": "maas" if catalog_key in MAAS_MODELS or name in MAAS_MODELS else "local",
            "input_price_per_m": info.get("input_price_per_m", 0),
            "output_price_per_m": info.get("output_price_per_m", 0),
            "tier": info.get("tier", 1),
            "status": info.get("status", "unknown"),
            "replacement": info.get("replacement"),
            "files": entry.get("files", []),
        })
    return enriched


def _normalize_name(name: str) -> str:
    if "/" in name:
        name = name.split("/")[-1]
    return name.lower().replace("_", "-")


def _guess_params(name: str) -> float:
    import re
    match = re.search(r"(\d+)[bB]", name)
    if match:
        return float(match.group(1))
    return 0


def _guess_hardware(name: str) -> list[str]:
    params = _guess_params(name)
    if params > 4:
        return ["gpu"]
    elif params > 0:
        return ["cpu"]
    return ["unknown"]
