"""CheckSum CLI — scan repos and plan RHDP provisioning."""

from __future__ import annotations

import click
from pathlib import Path

from .scanner import scan_repo
from .planner import recommend_tier
from .output import write_plan


@click.group()
@click.version_option()
def main():
    """CheckSum — scan demo repos, recommend RHDP provisioning tiers."""
    pass


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "fmt", type=click.Choice(["yaml", "json", "table"]), default="table")
def scan(repo_path: Path, fmt: str):
    """Scan a demo repo and report detected LLM usage."""
    results = scan_repo(repo_path)
    if fmt == "table":
        _print_scan_table(results)
    elif fmt == "yaml":
        import yaml
        click.echo(yaml.dump(results, default_flow_style=False))
    else:
        import json
        click.echo(json.dumps(results, indent=2))


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
def plan(repo_path: Path, output: Path | None):
    """Generate a capacity plan with tier recommendation."""
    results = scan_repo(repo_path)
    capacity_plan = recommend_tier(results)
    if output:
        write_plan(capacity_plan, output)
        click.echo(f"Plan written to {output}")
    else:
        import yaml
        click.echo(yaml.dump(capacity_plan, default_flow_style=False))


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, path_type=Path))
@click.argument("agnosticv_path", type=click.Path(exists=True, path_type=Path))
def validate(repo_path: Path, agnosticv_path: Path):
    """Validate an agnosticv config against a repo scan."""
    results = scan_repo(repo_path)
    capacity_plan = recommend_tier(results)
    click.echo(f"Recommended tier: {capacity_plan['recommended_tier']}")
    click.echo(f"Reasoning: {capacity_plan['tier_reasoning']}")


def _print_scan_table(results: dict):
    """Print scan results as a rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if results.get("models_detected"):
        table = Table(title="Models Detected")
        table.add_column("Model", style="cyan")
        table.add_column("Params (B)", justify="right")
        table.add_column("Hardware", style="green")
        table.add_column("Source")
        table.add_column("Files")
        for m in results["models_detected"]:
            table.add_row(
                m["name"],
                str(m.get("params_b", "?")),
                ", ".join(m.get("hardware", ["unknown"])),
                m.get("source", "unknown"),
                ", ".join(m.get("files", [])[:3]),
            )
        console.print(table)

    if results.get("frameworks_detected"):
        console.print(f"\n[bold]Frameworks:[/bold] {', '.join(results['frameworks_detected'])}")

    if results.get("resource_estimate"):
        r = results["resource_estimate"]
        console.print(f"\n[bold]Resource Estimate:[/bold]")
        console.print(f"  CPU: {r.get('cpu_cores', '?')} cores")
        console.print(f"  Memory: {r.get('memory_gb', '?')} GB")
        console.print(f"  Storage: {r.get('storage_gb', '?')} GB")
        console.print(f"  GPU: {r.get('gpu_count', 0)}")
