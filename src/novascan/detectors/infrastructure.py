"""Detect application infrastructure: containers, databases, queues, VMs, services."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

FIXTURE_DIRS = {"fixtures", "mocks", "testdata", "test_data", "mock_data", "__mocks__"}


def _is_fixture(path: Path) -> bool:
    parts = set(p.lower() for p in path.parts)
    return bool(parts & FIXTURE_DIRS)


def _filter_fixtures(files: list[Path]) -> list[Path]:
    return [f for f in files if not _is_fixture(f)]


def detect(source_files: list[Path], config_files: list[Path]) -> dict:
    """Scan for application infrastructure components."""
    from .helm import detect as detect_helm

    deploy_sources = _filter_fixtures(source_files)
    deploy_configs = _filter_fixtures(config_files)

    containers = _detect_containers(deploy_sources, deploy_configs)
    databases = _detect_databases(deploy_sources, deploy_configs)
    message_queues = _detect_message_queues(deploy_sources, deploy_configs)
    vms = _detect_vms(deploy_configs)
    k8s_workloads = _detect_k8s_workloads(deploy_configs)
    frontends = _detect_frontends(deploy_sources, deploy_configs)
    compose = _detect_compose(deploy_configs)
    helm = detect_helm(deploy_sources, deploy_configs)

    return {
        "containers": containers,
        "databases": databases,
        "message_queues": message_queues,
        "vms": vms,
        "k8s_workloads": k8s_workloads,
        "frontends": frontends,
        "compose_files": compose,
        "helm": helm,
        "topology": _classify_topology(
            containers, databases, message_queues, vms, k8s_workloads, frontends
        ),
    }


def _detect_containers(source_files: list[Path], config_files: list[Path]) -> dict:
    all_files = source_files + config_files
    containerfiles = []
    for f in all_files:
        if f.name in ("Containerfile", "Dockerfile") or f.name.startswith("Containerfile."):
            containerfiles.append(str(f))

    images = set()
    image_pattern = re.compile(r'image:\s*["\']?([a-z0-9][a-z0-9._/-]+(?::[a-z0-9._-]+)?)["\']?')
    for f in config_files:
        if f.suffix not in {".yaml", ".yml"}:
            continue
        try:
            content = f.read_text(errors="ignore")
            for match in image_pattern.finditer(content):
                img = match.group(1)
                if "/" in img and not img.startswith("$"):
                    images.add(img)
        except OSError:
            continue

    return {
        "containerfiles": len(containerfiles),
        "images_referenced": len(images),
        "image_list": sorted(images)[:20],
    }


DB_PATTERNS = {
    "postgresql": [r"postgresql\b", r"postgres\b", r"psycopg", r"asyncpg"],
    "redis": [r"\bredis\b", r"redis\.Redis"],
    "mongodb": [r"mongodb\b", r"pymongo", r"motor\."],
    "mysql": [r"\bmysql\b", r"mariadb"],
    "sqlite": [r"sqlite3?\b"],
    "elasticsearch": [r"elasticsearch\b", r"opensearch"],
}


def _detect_databases(source_files: list[Path], config_files: list[Path]) -> list[str]:
    detected = set()
    all_files = source_files + config_files
    for f in all_files:
        try:
            content = f.read_text(errors="ignore")
        except OSError:
            continue
        for db_type, patterns in DB_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected.add(db_type)
                    break
    return sorted(detected)


MQ_PATTERNS = {
    "kafka": [r"\bkafka\b", r"confluent_kafka", r"aiokafka"],
    "rabbitmq": [r"rabbitmq\b", r"\bpika\b", r"\bamqp\b"],
    "nats": [r"\bnats\b", r"nats\.connect"],
    "celery": [r"\bcelery\b"],
    "pulsar": [r"\bpulsar\b"],
}


def _detect_message_queues(source_files: list[Path], config_files: list[Path]) -> list[str]:
    detected = set()
    all_files = source_files + config_files
    for f in all_files:
        try:
            content = f.read_text(errors="ignore")
        except OSError:
            continue
        for mq_type, patterns in MQ_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected.add(mq_type)
                    break
    return sorted(detected)


def _detect_vms(config_files: list[Path]) -> dict:
    vm_count = 0
    kubevirt_refs = 0
    for f in config_files:
        if f.suffix not in {".yaml", ".yml", ".json"}:
            continue
        try:
            content = f.read_text(errors="ignore")
        except OSError:
            continue
        if "VirtualMachine" in content or "VirtualMachineInstance" in content:
            vm_count += content.count("kind: VirtualMachine")
            vm_count += content.count('"kind": "VirtualMachine"')
            vm_count += content.count('"kind":"VirtualMachine"')
        if "kubevirt.io" in content or "VirtualMachineInstance" in content:
            kubevirt_refs += 1

    return {
        "vm_count": vm_count,
        "kubevirt_references": kubevirt_refs,
        "needs_cnv": vm_count > 0,
    }


def _detect_k8s_workloads(config_files: list[Path]) -> dict:
    deployments = 0
    statefulsets = 0
    jobs = 0
    services = 0
    routes = 0
    pvcs = 0
    configmaps = 0
    secrets = 0

    for f in config_files:
        if f.suffix not in {".yaml", ".yml"}:
            continue
        try:
            content = f.read_text(errors="ignore")
            if "apiVersion:" not in content:
                continue
            for doc in yaml.safe_load_all(content):
                if not isinstance(doc, dict):
                    continue
                kind = doc.get("kind", "")
                if kind == "Deployment":
                    deployments += 1
                elif kind == "StatefulSet":
                    statefulsets += 1
                elif kind in ("Job", "CronJob"):
                    jobs += 1
                elif kind == "Service":
                    services += 1
                elif kind in ("Route", "Ingress"):
                    routes += 1
                elif kind == "PersistentVolumeClaim":
                    pvcs += 1
                elif kind == "ConfigMap":
                    configmaps += 1
                elif kind == "Secret":
                    secrets += 1
        except (yaml.YAMLError, OSError):
            continue

    return {
        "deployments": deployments,
        "statefulsets": statefulsets,
        "jobs": jobs,
        "services": services,
        "routes": routes,
        "pvcs": pvcs,
        "configmaps": configmaps,
        "secrets": secrets,
        "total_workloads": deployments + statefulsets + jobs,
    }


def _detect_frontends(source_files: list[Path], config_files: list[Path]) -> int:
    count = 0
    seen_dirs = set()
    for f in config_files:
        if f.name == "package.json":
            parent = str(f.parent)
            if parent not in seen_dirs:
                try:
                    content = f.read_text(errors="ignore")
                    if any(fw in content for fw in ["react", "vue", "angular", "svelte", "next", "patternfly"]):
                        count += 1
                        seen_dirs.add(parent)
                except OSError:
                    continue
    return count


def _detect_compose(config_files: list[Path]) -> int:
    return sum(
        1 for f in config_files
        if "compose" in f.name.lower() and f.suffix in {".yaml", ".yml"}
    )


TOPOLOGY_SIMPLE = "namespace"
TOPOLOGY_PLATFORM = "platform"
TOPOLOGY_CNV = "cnv"


def _classify_topology(
    containers: dict,
    databases: list,
    message_queues: list,
    vms: dict,
    k8s_workloads: dict,
    frontends: int,
) -> str:
    if vms.get("needs_cnv"):
        return TOPOLOGY_CNV

    total = k8s_workloads.get("total_workloads", 0)
    has_mq = len(message_queues) > 0
    has_db = len(databases) > 0

    if total > 15 or (total > 8 and has_mq) or frontends > 2:
        return TOPOLOGY_PLATFORM

    return TOPOLOGY_SIMPLE
