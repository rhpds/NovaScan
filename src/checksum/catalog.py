"""Model catalog — maps model names to hardware specs."""

from __future__ import annotations

from pathlib import Path

import yaml

BUILTIN_CATALOG = {
    "granite-2b-cpu": {"params_b": 2, "hardware": ["cpu"], "memory_gb": 4, "throughput_tps": 26},
    "granite-4-0-h-tiny": {"params_b": 1, "hardware": ["cpu"], "memory_gb": 2, "throughput_tps": 40},
    "phi3-mini-cpu": {"params_b": 3.8, "hardware": ["cpu"], "memory_gb": 8, "throughput_tps": 30},
    "qwen25-3b-cpu": {"params_b": 3, "hardware": ["cpu"], "memory_gb": 6, "throughput_tps": 24},
    "codellama-7b-instruct": {"params_b": 7, "hardware": ["cpu", "gpu"], "memory_gb": 14, "throughput_tps": 15},
    "granite-3-2-8b-instruct": {"params_b": 8, "hardware": ["cpu", "gpu"], "memory_gb": 16, "throughput_tps": 12},
    "deepseek-r1-distill-qwen-14b": {"params_b": 14, "hardware": ["gpu"], "memory_gb": 28, "throughput_tps": 55},
    "llama-scout-17b": {"params_b": 17, "hardware": ["gpu"], "memory_gb": 34, "throughput_tps": 60},
    "microsoft-phi-4": {"params_b": 14, "hardware": ["gpu"], "memory_gb": 28, "throughput_tps": 47},
    "qwen3-14b": {"params_b": 14, "hardware": ["gpu"], "memory_gb": 28, "throughput_tps": 37},
    "nomic-embed-text-v1-5": {"params_b": 0.14, "hardware": ["cpu"], "memory_gb": 1, "throughput_tps": 200},
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0": {"params_b": 1.1, "hardware": ["cpu"], "memory_gb": 2.5, "throughput_tps": 35},
}

MAAS_MODELS = {
    "granite-2b-cpu", "granite-4-0-h-tiny", "phi3-mini-cpu", "qwen25-3b-cpu",
    "codellama-7b-instruct", "granite-3-2-8b-instruct", "deepseek-r1-distill-qwen-14b",
    "llama-scout-17b", "microsoft-phi-4", "qwen3-14b", "nomic-embed-text-v1-5",
}


def lookup_models(raw_models: list[dict]) -> list[dict]:
    """Enrich raw model detections with catalog info."""
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
            "files": entry.get("files", []),
        })
    return enriched


def _normalize_name(name: str) -> str:
    """Strip org prefix from HuggingFace model names."""
    if "/" in name:
        name = name.split("/")[-1]
    return name.lower().replace("_", "-")


def _guess_params(name: str) -> float:
    """Guess parameter count from model name."""
    import re
    match = re.search(r"(\d+)[bB]", name)
    if match:
        return float(match.group(1))
    return 0


def _guess_hardware(name: str) -> list[str]:
    """Guess hardware tier from model name."""
    params = _guess_params(name)
    if params > 4:
        return ["gpu"]
    elif params > 0:
        return ["cpu"]
    return ["unknown"]
