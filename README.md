# CheckSum — RHDP Capacity Scanner & Provisioning Planner

Scan any demo repository and produce a right-sized RHDP provisioning recommendation. Detects LLM models, application infrastructure, resource requirements, and generates ready-to-commit AgnosticV catalog items.

Pair with **LiftOff** (provisioning engine) for the full workflow: CheckSum scans, LiftOff deploys.

## Install

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# Scan a repo — what does it need?
checksum scan ~/Documents/my-demo

# Plan provisioning — what tier and topology?
checksum plan ~/Documents/my-demo

# Plan for a 60-seat lab
checksum plan ~/Documents/my-demo --seats 60

# Generate a complete agnosticv catalog item
checksum plan ~/Documents/my-demo --seats 60 \
  --generate-agnosticv ./agnosticv/ai-qs-my-demo-tenant/ \
  --repo-url https://github.com/rh-ai-quickstart/my-demo

# Validate existing agnosticv config against a repo scan
checksum validate ~/Documents/my-demo ~/agnosticv/my-demo-tenant/common.yaml

# Batch scan all repos in a directory
checksum batch ~/Documents/ -o results/all-repos.yaml
```

## What It Detects

### LLM Layer
- **Frameworks**: OpenAI, LiteLLM, LangChain, Transformers, vLLM, Torch, OpenVINO, Llama Index
- **Models**: Granite, Phi, Qwen, DeepSeek, Llama, CodeLlama, Nomic, Whisper, BERT/embedding models
- **MAAS catalog**: 12 known MAAS models mapped to parameter counts, hardware tier, and memory requirements
- **False positive filtering**: URL paths, shell variables, test fixtures, code snippets, and known non-model terms are excluded

### Application Infrastructure
- **Containers**: Containerfile/Dockerfile count, image references
- **Databases**: PostgreSQL, Redis, MongoDB, MySQL, SQLite, Elasticsearch
- **Message queues**: Kafka, RabbitMQ, NATS, Celery, Pulsar
- **K8s workloads**: Deployments, StatefulSets, Jobs, Services, PVCs, Routes
- **VMs/CNV**: VirtualMachine resources, kubevirt.io references
- **Helm charts**: Parses `values.yaml` and templates for actual resource requests
- **Frontends**: React, Vue, Angular, PatternFly detection via `package.json`
- **Fixture exclusion**: `fixtures/`, `mocks/`, `testdata/` directories excluded from counts

## Tier Recommendations

| Tier | Per Seat | When |
|------|----------|------|
| **pilot** | 2 CPU, 4Gi | No LLM usage — just an API key |
| **partner** | 8-20 CPU, 16-32Gi | Uses LLM frameworks/models, inference via MAAS |
| **dedicated** | 20-40+ CPU, 32-64Gi | Local inference pods, heavy compute |

## Deployment Topology

| Topology | When |
|----------|------|
| **namespace** | Simple app (<=15 workloads, no message queues) |
| **platform** | Complex app (>15 workloads, or has Kafka/RabbitMQ) |
| **cnv** | Requires VMs (VirtualMachine resources detected) |

## Lab Capacity Planning

With `--seats N`, CheckSum produces:

- **Per-seat estimate**: CPU, memory, storage for one user
- **Lab total**: per-seat x seats + shared infra overhead (Keycloak, OpenShift AI, ArgoCD)
- **Cluster sizing**: worker count x worker size (auto-selected from 16-128 core nodes)
- **Sandbox config**: `max_placements`, `max_cpu_usage_percentage`, `max_memory_usage_percentage`
- **AgnosticV overrides**: `worker_instance_count`, `ai_workers_cores`, `ai_workers_memory`
- **Warnings**: MAAS rate limit risk (>90 RPM), GPU sharing at scale

## AgnosticV Generation

`--generate-agnosticv` produces a complete catalog item directory matching the production RHDP pattern:

```
output/
  common.yaml    # Workloads, quotas, models, deploy config, Babylon meta
  dev.yaml       # Dev sandbox selector
  test.yaml      # Test sandbox selector
  prod.yaml      # Prod sandbox selector
```

Follows the `quickstart_deploy_via_make` pattern used by production AI quickstarts — the app's own Helm charts handle deployment, not custom Ansible roles.

## Validation

`checksum validate` compares a CheckSum scan against an existing agnosticv config:

- **Tier match**: Does the provisioned tier match the recommendation?
- **Resource deltas**: Over-provisioned or under-provisioned CPU/memory/storage?
- **Model coverage**: Missing models or unnecessary extras in the LiteLLM list?

## Claude Code Skill

CheckSum is available as a global Claude Code skill:

```
/checksum ~/Documents/my-demo
/checksum ~/Documents/my-demo 60
```

Skill file: `~/.claude/commands/checksum.md`

## Development

```bash
make test          # Run all tests
make test-cov      # Run with coverage report
make clean         # Remove build artifacts
```

## Testing

69 tests across 7 stages:

| Stage | Tests | What |
|-------|-------|------|
| 1. Package Structure | 8 | Imports, CLI commands, Python 3.9 compat |
| 2. Scanner & Detectors | 13 | Framework/model detection, false positives, catalog |
| 3. Planner | 3 | Tier recommendations |
| 4. Infrastructure | — | Covered by scanner integration tests |
| 5. Helm | — | Covered by infrastructure detector |
| 6. Lab Capacity | 6 | Multi-seat scaling, MAAS warnings |
| 7. AgnosticV Generation | 23 | Generator output, validator, Jinja loading |
| K8s Parsing | 10 | CPU/memory/storage edge cases |
| Package | 8 | Module structure, CLI, compat |
