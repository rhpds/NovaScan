# Scan a repo

Run NovaScan against a demo repository.

## Instructions

```bash
PYTHONPATH=src python3 -c "
from novascan.scanner import scan_repo
from novascan.planner import recommend_tier
from pathlib import Path
import yaml

repo_path = Path('$ARGUMENTS' or '.').expanduser().resolve()
results = scan_repo(repo_path)
plan = recommend_tier(results, seats=1)
print(yaml.dump(plan, default_flow_style=False))
"
```

Present: tier, topology, per-seat resources, infrastructure, models.

## Arguments

$ARGUMENTS - Repo path and optional seat count (e.g., `/scan ~/Documents/my-demo 60`).
