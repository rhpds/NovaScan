"""Generate agnosticv catalog item YAML from CheckSum scan results."""

from __future__ import annotations

import uuid
import math
from pathlib import Path

import yaml


def generate_agnosticv(capacity_plan: dict, seats: int = 1, repo_url: str = "") -> dict:
    """Generate a complete agnosticv tenant common.yaml from scan results."""
    tier = capacity_plan.get("recommended_tier", "partner")
    estimate = capacity_plan.get("resource_estimate", {})
    models = capacity_plan.get("models_detected", [])
    infra = capacity_plan.get("infrastructure", {})
    repo = capacity_plan.get("repo", "")

    repo_name = Path(repo).name if repo else "demo"
    slug = repo_name.lower().replace("_", "-").replace(" ", "-")
    maas_models = [m["name"] for m in models if m.get("source") == "maas"]

    cpu = max(int(math.ceil(estimate.get("cpu_cores", 8))), 8)
    mem = max(int(math.ceil(estimate.get("memory_gb", 16))), 16)
    storage = max(int(math.ceil(estimate.get("storage_gb", 20))), 20)

    config = {
        "config": "namespace",
        "cloud_provider": "none",
        "tag": "main",
        "requirements_content": _build_requirements(tier, infra),
        "workloads": _build_workloads(tier, infra),
    }

    config["common_password"] = "{{ lookup('password', output_dir ~ '/common_password', length=12, chars=['ascii_letters', 'digits']) }}"

    if tier in ("partner", "dedicated"):
        config["ocp4_workload_tenant_keycloak_username"] = "user-{{ guid }}"
        config["ocp4_workload_tenant_keycloak_user_password"] = "{{ common_password }}"
        config["ocp4_workload_tenant_keycloak_user_keycloak_namespace"] = "keycloak"
        config["ocp4_workload_tenant_keycloak_user_keycloak_realm"] = "sso"

    config["ocp4_workload_tenant_namespace_username"] = "user-{{ guid }}"
    config["ocp4_workload_tenant_namespace_use_cluster_quota"] = True
    config["ocp4_workload_tenant_namespace_suffixes"] = [{"suffix": slug}]

    config["ocp4_workload_tenant_namespace_default_quota"] = {
        "limits.cpu": str(cpu * 2),
        "requests.cpu": str(cpu),
        "limits.memory": f"{mem * 2}Gi",
        "requests.memory": f"{mem}Gi",
        "requests.storage": f"{storage}Gi",
    }

    config["ocp4_workload_tenant_namespace_default_limit_range"] = {
        "default": {"cpu": "2", "memory": "4Gi"},
        "defaultRequest": {"cpu": "100m", "memory": "256Mi"},
    }

    if maas_models:
        config["ocp4_workload_litellm_virtual_keys_duration"] = "7d"
        config["ocp4_workload_litellm_virtual_keys_models"] = maas_models

    if repo_url:
        config["quickstart_deploy_via_make_repo_url"] = repo_url
        config["quickstart_deploy_via_make_scm_ref"] = "main"
        config["quickstart_deploy_via_make_directory"] = "helm"
        config["quickstart_deploy_via_make_params"] = {
            "NAMESPACE": f"user-{{{{ guid }}}}-{slug}",
        }
        config["quickstart_deploy_via_make_uninstall_params"] = {
            "NAMESPACE": f"user-{{{{ guid }}}}-{slug}",
        }

    config["requester_email"] = f"rhdp-{{{{ guid }}}}@demo.redhat.com"
    config["catalog_item_name"] = f"ai-quickstarts.ai-qs-{slug}-tenant.event"

    config["openshift_api_url"] = "{{ sandbox_openshift_api_url }}"
    config["openshift_cluster_admin_token"] = "{{ cluster_admin_agnosticd_sa_token }}"

    config["ocp4_workload_showroom_passthrough_user_data"] = True

    config["__meta__"] = _build_meta(slug, repo_url, seats)

    return config


def _build_requirements(tier: str, infra: dict) -> dict:
    collections = [
        {
            "name": "https://github.com/agnosticd/namespaced_workloads.git",
            "type": "git",
            "version": "{{ tag }}",
        },
        {
            "name": "https://github.com/rhpds/rhpds.litellm_virtual_keys.git",
            "type": "git",
            "version": "{{ tag }}",
        },
        {
            "name": "https://github.com/agnosticd/ai_quickstarts.git",
            "type": "git",
            "version": "{{ tag }}",
        },
        {
            "name": "https://github.com/agnosticd/showroom.git",
            "type": "git",
            "version": "v1.6.8",
        },
    ]
    return {"collections": collections}


def _build_workloads(tier: str, infra: dict) -> list:
    workloads = []

    if tier in ("partner", "dedicated"):
        workloads.append("agnosticd.namespaced_workloads.ocp4_workload_tenant_keycloak_user")

    workloads.append("agnosticd.namespaced_workloads.ocp4_workload_tenant_namespace")
    workloads.append("rhpds.litellm_virtual_keys.ocp4_workload_litellm_virtual_keys")
    workloads.append("agnosticd.ai_quickstarts.quickstart_deploy_via_make")
    workloads.append("agnosticd.showroom.ocp4_workload_showroom")

    return workloads


def _build_meta(slug: str, repo_url: str, seats: int) -> dict:
    return {
        "access_control": {
            "allow_groups": ["rhpds-devs-quickstart-ai"],
        },
        "asset_uuid": str(uuid.uuid4()),
        "owners": {
            "maintainer": [
                {"name": "CHANGE_ME", "email": "CHANGE_ME@redhat.com"},
            ],
        },
        "sandbox_api": {
            "actions": {
                "destroy": {"catch_all": False},
            },
        },
        "catalog": {
            "display_name": f"AI Quickstart {slug.replace('-', ' ').title()}",
            "category": "Labs",
            "namespace": "babylon-catalog-{{ stage | default('?') }}",
            "keywords": ["openshift", "quickstart", "ai"],
            "labels": {"Provider": "RHDP"},
            "reportingLabels": {"primaryBU": "Hybrid_Platforms"},
            "parameters": [],
        },
        "deployer": {
            "scm_url": "https://github.com/agnosticd/agnosticd-v2",
            "scm_ref": "main",
            "execution_environment": {
                "image": "quay.io/agnosticd/ee-multicloud:chained-2026-02-23",
                "pull": "missing",
            },
            "actions": {
                "destroy": {"disable": False},
                "start": {"disable": False},
                "status": {"disable": True},
                "stop": {"disable": False},
                "update": {"disable": True},
            },
        },
    }


def write_agnosticv(config: dict, output_dir: Path):
    """Write a complete agnosticv catalog item directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    common_lines = [
        "---",
        "# Generated by CheckSum RHDP Capacity Scanner",
        "# Review and adjust before committing.",
        "",
        "#include /includes/agd-v2-mapping.yaml",
        "#include /includes/catalog-icon-openshift.yaml",
        "#include /includes/terms-of-service.yaml",
        "#include /includes/sandbox-api.yaml",
        "",
        "#include /includes/parameters/purpose.yaml",
        "#include /includes/access-restriction-quickstarts-ai.yaml",
        "#include /includes/secrets/litemaas-master_api.yaml",
        "",
    ]

    meta = config.pop("__meta__", {})
    body = yaml.dump(config, default_flow_style=False, sort_keys=False)
    meta_yaml = yaml.dump({"__meta__": meta}, default_flow_style=False, sort_keys=False)

    common_content = "\n".join(common_lines) + body + "\n" + meta_yaml
    (output_dir / "common.yaml").write_text(common_content)

    for stage in ["dev", "test", "prod"]:
        stage_content = yaml.dump({
            "__meta__": {
                "deployer": {"scm_ref": "main"},
                "sandboxes": [{
                    "kind": "OcpSandbox",
                    "cloud_selector": {
                        "purpose": stage,
                        "cloud": "cnv-dedicated-shared",
                    },
                }],
            },
        }, default_flow_style=False)
        (output_dir / f"{stage}.yaml").write_text(f"---\n{stage_content}")
