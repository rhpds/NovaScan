"""Detect Helm chart deployments and extract resource requests from values.yaml."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def detect(source_files: list[Path], config_files: list[Path]) -> dict:
    """Scan for Helm charts and extract resource specifications."""
    all_files = source_files + config_files
    charts = _find_charts(all_files)
    values_resources = {}
    template_resources = {}
    deploy_method = None

    for chart in charts:
        vr = _parse_values(chart / "values.yaml")
        if vr:
            values_resources.update(vr)
        tr = _parse_templates(chart / "templates")
        if tr:
            template_resources.update(tr)

    for f in config_files:
        if f.name == "Makefile" or f.name.endswith(".mk"):
            try:
                content = f.read_text(errors="ignore")
                if "helm" in content.lower() and ("install" in content or "upgrade" in content):
                    deploy_method = "helm-via-make"
            except OSError:
                pass

    all_resources = {**values_resources, **template_resources}
    total_cpu = sum(r.get("cpu_request", 0) for r in all_resources.values() if isinstance(r, dict))
    total_mem = sum(r.get("memory_request_gb", 0) for r in all_resources.values() if isinstance(r, dict))
    total_storage = sum(r.get("storage_gb", 0) for r in all_resources.values() if isinstance(r, dict))
    replicas = sum(r.get("replicas", 1) for r in all_resources.values() if isinstance(r, dict) and "cpu_request" in r)

    return {
        "charts_found": len(charts),
        "deploy_method": deploy_method,
        "components": all_resources,
        "total_cpu_request": round(total_cpu * max(replicas, 1) if total_cpu else 0, 2),
        "total_memory_gb": round(total_mem, 2),
        "total_storage_gb": round(total_storage, 2),
        "total_replicas": replicas,
    }


def _find_charts(files: list[Path]) -> list[Path]:
    """Find directories containing Chart.yaml."""
    seen = set()
    charts = []
    for f in files:
        if f.name == "Chart.yaml":
            parent = f.parent
            if str(parent) not in seen:
                seen.add(str(parent))
                charts.append(parent)
    return charts


def _parse_values(values_path: Path) -> dict[str, dict]:
    """Extract resource requests from a Helm values.yaml."""
    if not values_path.exists():
        return {}

    try:
        data = yaml.safe_load(values_path.read_text(errors="ignore"))
    except (yaml.YAMLError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}

    resources = {}
    _walk_values(data, "", resources)
    return resources


def _walk_values(data: dict, prefix: str, resources: dict):
    """Recursively walk values.yaml to find resource specs."""
    if not isinstance(data, dict):
        return

    if "resources" in data and isinstance(data["resources"], dict):
        res = data["resources"]
        requests = res.get("requests", {})
        limits = res.get("limits", {})
        if requests or limits:
            name = prefix.rstrip(".") or "main"
            raw_replicas = data.get("replicaCount", data.get("replicas", 1))
            replica_count = raw_replicas if isinstance(raw_replicas, int) else 1
            resources[name] = {
                "cpu_request": _parse_cpu(requests.get("cpu", limits.get("cpu", "0"))),
                "memory_request_gb": _parse_mem_gb(requests.get("memory", limits.get("memory", "0"))),
                "replicas": replica_count,
            }

    if "persistence" in data and isinstance(data["persistence"], dict):
        p = data["persistence"]
        if p.get("enabled", True) and p.get("size"):
            name = prefix.rstrip(".") or "main"
            if name not in resources:
                resources[name] = {}
            resources[name]["storage_gb"] = _parse_mem_gb(p["size"])

    if "storage" in data and isinstance(data["storage"], dict):
        s = data["storage"]
        if s.get("size"):
            name = prefix.rstrip(".") or "main"
            if name not in resources:
                resources[name] = {}
            resources[name]["storage_gb"] = _parse_mem_gb(s["size"])

    for key, val in data.items():
        if isinstance(val, dict) and key not in ("resources", "persistence", "storage", "metadata", "labels", "annotations"):
            _walk_values(val, f"{prefix}{key}.", resources)


def _parse_templates(templates_dir: Path) -> dict[str, dict]:
    """Extract resource requests from Helm template files."""
    if not templates_dir.exists():
        return {}

    resources = {}
    for f in templates_dir.rglob("*.yaml"):
        try:
            content = f.read_text(errors="ignore")
        except OSError:
            continue

        cpu_matches = re.findall(r'cpu:\s*["\']?(\d+(?:\.\d+)?m?)["\']?', content)
        mem_matches = re.findall(r'memory:\s*["\']?(\d+(?:\.\d+)?(?:Gi|Mi|G|M)?)["\']?', content)

        if cpu_matches or mem_matches:
            name = f.stem.replace("-", "_")
            cpu_vals = [_parse_cpu(c) for c in cpu_matches if _parse_cpu(c) > 0]
            mem_vals = [_parse_mem_gb(m) for m in mem_matches if _parse_mem_gb(m) > 0]

            if cpu_vals or mem_vals:
                resources[name] = {
                    "cpu_request": min(cpu_vals) if cpu_vals else 0,
                    "memory_request_gb": min(mem_vals) if mem_vals else 0,
                }

    return resources


def _parse_cpu(val) -> float:
    val = str(val).strip().strip('"').strip("'")
    if not val or val == "0":
        return 0.0
    if val.endswith("m"):
        try:
            return float(val[:-1]) / 1000
        except ValueError:
            return 0.0
    try:
        return float(val)
    except ValueError:
        return 0.0


def _parse_mem_gb(val) -> float:
    val = str(val).strip().strip('"').strip("'")
    if not val or val == "0":
        return 0.0
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(Gi|Mi|Ki|G|M|Ti)?$", val)
    if not match:
        try:
            return float(val)
        except ValueError:
            return 0.0
    num = float(match.group(1))
    unit = match.group(2) or ""
    multipliers = {"Ki": 1/1048576, "Mi": 1/1024, "Gi": 1, "Ti": 1024, "G": 1, "M": 1/1000}
    return num * multipliers.get(unit, 1)
