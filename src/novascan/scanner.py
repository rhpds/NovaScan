"""Core scanning logic — detect LLM usage in a repo."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .detectors import llm_imports, model_names, k8s_manifests, concurrency, infrastructure
from .catalog import lookup_models


def scan_repo(repo_path: Path) -> dict:
    """Scan a repository and return structured detection results."""
    repo_path = Path(repo_path).resolve()

    source_files = _collect_source_files(repo_path)
    config_files = _collect_config_files(repo_path)

    frameworks = llm_imports.detect(source_files)
    raw_models = model_names.detect(source_files + config_files)
    models = lookup_models(raw_models)
    k8s_resources = k8s_manifests.detect(config_files)
    concurrency_info = concurrency.detect(source_files)
    infra = infrastructure.detect(source_files, config_files)

    return {
        "repo": str(repo_path),
        "files_scanned": len(source_files) + len(config_files),
        "frameworks_detected": frameworks,
        "models_detected": models,
        "k8s_resources": k8s_resources,
        "concurrency": concurrency_info,
        "infrastructure": infra,
        "resource_estimate": _estimate_resources(models, k8s_resources, concurrency_info, infra),
    }


def _collect_source_files(repo_path: Path) -> list[Path]:
    """Collect Python, TypeScript, and shell source files."""
    extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".sh"}
    exclude_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "_archive"}
    files = []
    for f in repo_path.rglob("*"):
        if f.is_file() and f.suffix in extensions:
            if not any(d in f.parts for d in exclude_dirs):
                files.append(f)
    return files


def _collect_config_files(repo_path: Path) -> list[Path]:
    """Collect YAML, JSON, and TOML config files."""
    extensions = {".yaml", ".yml", ".json", ".toml"}
    exclude_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "_archive"}
    files = []
    for f in repo_path.rglob("*"):
        if f.is_file() and (f.suffix in extensions or f.name in {".env", ".env.example"}):
            if not any(d in f.parts for d in exclude_dirs):
                files.append(f)
    return files


def _estimate_resources(
    models: list, k8s_resources: dict, concurrency_info: dict, infra: Optional[dict] = None
) -> dict:
    """Estimate total resource requirements."""
    base_cpu = 4
    base_memory = 8
    storage_gb = 20
    gpu_count = 0

    local_models = [m for m in models if m.get("source") == "local"]
    local_cpu = min(len(local_models), 3) * 4
    local_mem = sum(m.get("memory_gb", 0) for m in local_models)

    for model in models:
        if "gpu" in model.get("hardware", []):
            gpu_count = max(gpu_count, 1)

    cpu_cores = base_cpu + local_cpu
    memory_gb = base_memory + local_mem

    k8s_cpu = k8s_resources.get("total_cpu_request", 0)
    k8s_mem = k8s_resources.get("total_memory_gb", 0)
    k8s_stor = k8s_resources.get("total_storage_gb", 0)

    if infra:
        helm = infra.get("helm", {})
        if helm.get("total_cpu_request", 0) > k8s_cpu:
            k8s_cpu = helm["total_cpu_request"]
        if helm.get("total_memory_gb", 0) > k8s_mem:
            k8s_mem = helm["total_memory_gb"]
        if helm.get("total_storage_gb", 0) > k8s_stor:
            k8s_stor = helm["total_storage_gb"]

    cpu_cores = max(cpu_cores, k8s_cpu) if k8s_cpu else cpu_cores
    memory_gb = max(memory_gb, k8s_mem) if k8s_mem else memory_gb
    storage_gb = max(storage_gb, k8s_stor) if k8s_stor else storage_gb

    max_concurrent = concurrency_info.get("max_concurrent", 1)
    maas_rpm = min(max_concurrent, 10) * 10

    return {
        "cpu_cores": cpu_cores,
        "memory_gb": memory_gb,
        "storage_gb": storage_gb,
        "gpu_count": gpu_count,
        "maas_rpm_estimate": maas_rpm,
        "local_inference": bool(local_models),
    }
