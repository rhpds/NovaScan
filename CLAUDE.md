# CLAUDE.md — Agent Instructions for NovaScan

## What This Is

RHDP capacity scanner. Scans any demo repository and produces right-sized provisioning recommendations: LLM tier, deployment topology, infrastructure requirements, lab capacity, and ready-to-commit AgnosticV catalog items.

## Architecture

```
CLI (click) → Scanner → Detectors → Catalog → Planner → Generator
                            ↓
              llm_imports, model_names, k8s_manifests,
              concurrency, infrastructure, helm
```

Pure Python, no external services needed. Read-only — never modifies the scanned repo.

## Development

```bash
pip install -e ".[dev]"

# Run tests
PYTHONPATH=src python3 -m pytest tests/ -v

# Or use make
make test
make test-cov
```

## Key Conventions

- **Python 3.9 compatible**: Use `from __future__ import annotations` in every file. Use `Optional[str]` not `str | None`.
- **Package path**: Source is `src/novascan/`. Tests use `PYTHONPATH=src`.
- **No side effects**: NovaScan is read-only. It scans and reports, never modifies.
- **False positive filtering**: Model name detector has allowlists/blocklists in `model_names.py`. Add new false positives there.
- **Fixture exclusion**: Infrastructure detector excludes `fixtures/`, `mocks/`, `testdata/` dirs.

## File Structure

```
src/novascan/
  cli.py              # Click CLI: scan, plan, validate, batch
  scanner.py           # Core orchestrator
  planner.py           # Tier recommendation + lab capacity
  catalog.py           # MAAS model catalog (12 models)
  generator.py         # AgnosticV YAML generation
  validator.py         # Compare scan vs existing agnosticv config
  output.py            # YAML writer
  detectors/
    llm_imports.py     # Framework detection (8 frameworks)
    model_names.py     # Model name extraction + false positive filtering
    k8s_manifests.py   # K8s resource parsing
    concurrency.py     # ThreadPool, asyncio, batch patterns
    infrastructure.py  # Containers, DBs, MQs, VMs, K8s workloads, Helm
    helm.py            # Helm chart values.yaml + template parsing
```

## Testing

85 tests across 7 stages + E2E. Validation matrix at `tests/validation_matrix.yaml` with 90% pass threshold.

## Related Repos

- **LiftOff** (`~/Documents/liftoff`): Provisioning engine that deploys what NovaScan recommends
- **Intel Demo** ([rhpds/red-hat-intel-partnership-demo](https://github.com/rhpds/red-hat-intel-partnership-demo)): Reference demo app
