# Claude Code Skills

NovaScan includes Claude Code slash commands for capacity scanning and provisioning generation.

## Available Skills

### `/scan`
Scan a demo repository and report provisioning requirements.

```
/scan ~/Documents/my-demo           # Scan a repo
/scan ~/Documents/my-demo 60        # Scan with 60-seat lab capacity
/scan .                              # Scan current directory
```

**Output:** Provisioning tier (pilot/partner/dedicated), deployment topology (namespace/platform/cnv), per-seat resources, infrastructure (databases, message queues, K8s workloads), LLM models detected, and MAAS warnings.

### `/generate`
Generate a complete AgnosticV catalog item from scan results.

```
/generate ~/Documents/my-demo ./output/ai-qs-my-demo-tenant/
/generate ~/Documents/my-demo ./output/ 60 --repo-url https://github.com/rh-ai-quickstart/my-demo --slug my-demo
```

**Output:** `common.yaml`, `dev.yaml`, `test.yaml`, `prod.yaml` — ready to commit to the AgnosticV repo.

### `/novascan` (global)
Same as `/scan` but available from any directory. Works across all projects.

```
/novascan ~/Documents/any-repo
/novascan ~/Documents/any-repo 25
```

## Setup

Project skills are in `.claude/commands/`. The global `/novascan` skill is at `~/.claude/commands/novascan.md`.

No installation needed — Claude Code loads them automatically.

## Integration with LiftOff

NovaScan scans → recommends → generates configs. LiftOff deploys them.

```
novascan plan ~/my-demo --seats 60 --generate-agnosticv ./agnosticv/tenant/
# Review the generated configs
# Copy to LiftOff repo → deploy via RHDP/Babylon
```
