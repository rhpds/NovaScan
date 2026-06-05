# Generate AgnosticV catalog item

Scan a repo and generate a complete agnosticv catalog item directory.

## Instructions

Parse arguments for: repo path, output directory, optional seat count, optional repo URL, optional slug.

```bash
PYTHONPATH=src python3 -c "
from novascan.scanner import scan_repo
from novascan.planner import recommend_tier
from novascan.generator import generate_agnosticv, write_agnosticv
from pathlib import Path

results = scan_repo(Path('REPO_PATH'))
plan = recommend_tier(results, seats=SEATS)
config = generate_agnosticv(plan, seats=SEATS, repo_url='REPO_URL', slug_override='SLUG')
write_agnosticv(config, Path('OUTPUT_DIR'))
print('Generated catalog item at OUTPUT_DIR')
"
```

## Arguments

$ARGUMENTS - repo_path output_dir [seats] [--repo-url URL] [--slug SLUG]
