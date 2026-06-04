# Proposal: Right-Sizing RHDP AI Quickstart Provisioning with CheckSum

## The Problem

AI quickstart catalog items use blanket resource quotas that waste cluster capacity:

| Quickstart | Allocated CPU | Allocated Memory | Allocated Storage | Likely Need |
|---|---|---|---|---|
| product-rec | 40 | 64Gi | 150Gi | ~12 CPU, 24Gi |
| data-gov | 40 | 64Gi | 50Gi | ~12 CPU, 24Gi |
| ppe-comp | 40 | 64Gi | 100Gi | ~16 CPU, 32Gi |
| rag | 40 | 64Gi | 100Gi | ~20 CPU, 32Gi |
| it-self-service | 12 | 16Gi | 12Gi | ~12 CPU, 16Gi (correctly sized) |

4 of 5 quickstarts use the same `40 CPU / 64Gi` quota regardless of actual need. Only `it-self-service` was right-sized.

**Impact at scale**: With `max_placements: 25` on shared clusters, over-provisioned quotas mean:
- Fewer tenants per cluster (quota exhaustion before CPU exhaustion)
- More clusters needed for the same number of users
- Higher infrastructure cost per lab session

## The Solution: CheckSum

CheckSum is a capacity scanner that analyzes demo repos and produces right-sized provisioning configs.

**What it scans:**
- LLM models and frameworks (OpenAI, vLLM, LangChain, etc.)
- Application infrastructure (databases, message queues, K8s workloads, Helm charts)
- Resource requests from `values.yaml` and Helm templates
- Deployment topology (namespace vs. platform vs. CNV)

**What it produces:**
- Per-seat resource estimate (CPU, memory, storage)
- Lab capacity plan for N concurrent seats
- MAAS rate limit warnings
- Complete agnosticv catalog item (`common.yaml` + stage files)

**Example:**
```bash
# Scan a quickstart repo
checksum plan ~/repos/it-self-service-agent --seats 60

# Output:
#   Per seat:    12 CPU, 16Gi, 12Gi storage
#   Lab (60):    728 CPU, 992Gi memory
#   Cluster:     6 workers × 128 CPU
#   Warning:     MAAS RPM 600 exceeds 90 RPM limit

# Generate a right-sized agnosticv catalog item
checksum plan ~/repos/it-self-service-agent --seats 60 \
  --generate-agnosticv ./agnosticv/ai-qs-it-self-service-tenant/ \
  --repo-url https://github.com/rh-ai-quickstart/it-self-service-agent
```

## Integration Path

1. **Immediate**: Run CheckSum against all 5 existing quickstarts, produce right-sized quotas
2. **Process**: Make CheckSum part of the quickstart onboarding checklist — scan before writing agnosticv configs
3. **CI**: Add CheckSum validation to agnosticv PR reviews — flag over-provisioned quotas
4. **Long term**: CheckSum as a pre-flight step in the Babylon provisioning pipeline

## Current State

- 69 tests, all passing
- Scanned 28 repos (20 local + 8 rh-ai-quickstart)
- Available as Claude Code skill: `/checksum`
- Repo: ready to push to `rhpds/checksum`

## Ask

1. Review CheckSum and provide feedback on the provisioning model
2. Run it against the full quickstart catalog to validate recommendations
3. Discuss integration into the agnosticv review process
