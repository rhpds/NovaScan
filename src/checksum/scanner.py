"""Core scanning logic — detect LLM usage in a repo."""

from __future__ import annotations

from pathlib import Path

from .detectors import llm_imports, model_names, k8s_manifests, concurrency
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

    return {
        "repo": str(repo_path),
        "files_scanned": len(source_files) + len(config_files),
        "frameworks_detected": frameworks,
        "models_detected": models,
        "k8s_resources": k8s_resources,
        "concurrency": concurrency_info,
        "resource_estimate": _estimate_resources(models, k8s_resources, concurrency_info),
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
    extensions = {".yaml", ".yml", ".json", ".toml", ".env", ".env.example"}
    exclude_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "_archive"}
    files = []
    for f in repo_path.rglob("*"):
        if f.is_file() and (f.suffix in extensions or f.name in {".env", ".env.example"}):
            if not any(d in f.parts for d in exclude_dirs):
                files.append(f)
    return files


def _estimate_resources(models: list, k8s_resources: dict, concurrency_info: dict) -> dict:
    """Estimate total resource requirements."""
    cpu_cores = 4
    memory_gb = 8
    storage_gb = 20
    gpu_count = 0

    for model in models:
        if "gpu" in model.get("hardware", []):
            gpu_count = max(gpu_count, 1)
        mem = model.get("memory_gb", 0)
        if model.get("source") == "local":
            memory_gb += mem
            cpu_cores += 4

    if k8s_resources.get("total_cpu_request"):
        cpu_cores = max(cpu_cores, k8s_resources["total_cpu_request"])
    if k8s_resources.get("total_memory_gb"):
        memory_gb = max(memory_gb, k8s_resources["total_memory_gb"])
    if k8s_resources.get("total_storage_gb"):
        storage_gb = max(storage_gb, k8s_resources["total_storage_gb"])

    max_concurrent = concurrency_info.get("max_concurrent", 1)
    maas_rpm = max_concurrent * 10

    return {
        "cpu_cores": cpu_cores,
        "memory_gb": memory_gb,
        "storage_gb": storage_gb,
        "gpu_count": gpu_count,
        "maas_rpm_estimate": maas_rpm,
        "local_inference": any(m.get("source") == "local" for m in models),
    }
