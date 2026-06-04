"""Output formatters for capacity plans."""

from pathlib import Path

import yaml


def write_plan(plan: dict, output_path: Path):
    """Write a capacity plan to a YAML file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(plan, f, default_flow_style=False, sort_keys=False)
