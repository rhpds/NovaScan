"""Parse Kubernetes manifests for resource requests."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def detect(config_files: list[Path]) -> dict:
    """Aggregate resource requests from K8s manifests."""
    total_cpu = 0.0
    total_memory_gb = 0.0
    total_storage_gb = 0.0
    manifest_count = 0

    for f in config_files:
        if f.suffix not in {".yaml", ".yml"}:
            continue
        try:
            content = f.read_text(errors="ignore")
            if "apiVersion:" not in content or "kind:" not in content:
                continue
            for doc in yaml.safe_load_all(content):
                if not isinstance(doc, dict):
                    continue
                if "kind" not in doc:
                    continue
                manifest_count += 1
                cpu, mem = _extract_resources(doc)
                total_cpu += cpu
                total_memory_gb += mem

                if doc.get("kind") == "PersistentVolumeClaim":
                    storage = doc.get("spec", {}).get("resources", {}).get("requests", {}).get("storage", "")
                    total_storage_gb += _parse_quantity_gb(storage)
        except (yaml.YAMLError, OSError):
            continue

    return {
        "manifest_count": manifest_count,
        "total_cpu_request": total_cpu,
        "total_memory_gb": total_memory_gb,
        "total_storage_gb": total_storage_gb,
    }


def _extract_resources(doc: dict) -> tuple[float, float]:
    """Walk a manifest for container resource requests. Returns (cpu, memory_gb)."""
    containers = []
    spec = doc.get("spec", {})
    if "template" in spec:
        containers = spec["template"].get("spec", {}).get("containers", [])
    elif "containers" in spec:
        containers = spec["containers"]

    cpu_total = 0.0
    mem_total = 0.0
    for c in containers:
        requests = c.get("resources", {}).get("requests", {})
        cpu = requests.get("cpu", "0")
        memory = requests.get("memory", "0")
        cpu_total += _parse_cpu(cpu)
        mem_total += _parse_quantity_gb(memory)
    return cpu_total, mem_total


def _parse_cpu(val: str) -> float:
    """Parse CPU quantity (e.g., '500m', '2', '1.5')."""
    val = str(val).strip()
    if val.endswith("m"):
        return float(val[:-1]) / 1000
    return float(val)


def _parse_quantity_gb(val: str) -> float:
    """Parse memory/storage quantity to GB."""
    val = str(val).strip()
    if not val or val == "0":
        return 0.0
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(Gi|Mi|Ki|G|M|K|Ti)?$", val)
    if not match:
        return 0.0
    num = float(match.group(1))
    unit = match.group(2) or ""
    multipliers = {"Ki": 1/1048576, "Mi": 1/1024, "Gi": 1, "Ti": 1024, "K": 1/1000000, "M": 1/1000, "G": 1}
    return num * multipliers.get(unit, 1)
