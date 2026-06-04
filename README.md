# CheckSum — RHDP Capacity Planner

Scan demo repositories for LLM/AI usage patterns and recommend RHDP provisioning tiers.

## Install

```bash
pip install -e ".[dev]"
```

## Usage

```bash
# Scan a repo
checksum scan /path/to/demo-repo
checksum scan /path/to/demo-repo --format yaml

# Generate a capacity plan
checksum plan /path/to/demo-repo -o plan.yaml

# Validate against existing agnosticv config
checksum validate /path/to/demo-repo /path/to/agnosticv/common.yaml

# Batch scan multiple repos
checksum batch /path/to/repos-dir -o results/
```

## Tiers

| Tier | Resources | Use Case |
|------|-----------|----------|
| `pilot` | 2 CPU, 4Gi mem | MAAS API key only |
| `partner` | 20 CPU, 32Gi mem | Gateway + frontend + postgres, inference via MAAS |
| `dedicated` | 40 CPU, 64Gi mem | Full stack with local CPU inference pods |

## Detectors

- **LLM Imports** — openai, litellm, langchain, transformers, vllm, openvino, torch
- **Model Names** — Granite, Phi, Qwen, DeepSeek, Llama, CodeLlama, Nomic, etc.
- **K8s Manifests** — Resource requests from Deployments, Pods, PVCs
- **Concurrency** — ThreadPoolExecutor, asyncio, batch sizes

## Development

```bash
pytest
pytest --cov=checksum
```
