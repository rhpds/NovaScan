"""NovaScan CLI — scan repos and plan RHDP provisioning."""

from __future__ import annotations

import click
from pathlib import Path
from typing import Optional

from .scanner import scan_repo
from .planner import recommend_tier
from .output import write_plan
from .validator import compare_against_agnosticv


@click.group()
@click.version_option(version="0.1.0", package_name="rhdp-novascan")
def main():
    """NovaScan — scan demo repos, recommend RHDP provisioning tiers."""
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
@click.option("--seats", type=int, default=1, help="Number of concurrent seats/users for lab capacity planning")
@click.option("--generate-agnosticv", "agnosticv_dir", type=click.Path(path_type=Path), default=None,
              help="Generate a complete agnosticv catalog item directory")
@click.option("--repo-url", default="", help="Git URL for the demo repo (used in quickstart_deploy_via_make)")
@click.option("--slug", default="", help="Custom namespace suffix slug (default: derived from repo name)")
def plan(repo_path: Path, output: Optional[Path], seats: int, agnosticv_dir: Optional[Path], repo_url: str, slug: str):
    """Generate a capacity plan with tier recommendation."""
    results = scan_repo(repo_path)
    capacity_plan = recommend_tier(results, seats=seats)

    if agnosticv_dir:
        from .generator import generate_agnosticv, write_agnosticv
        config = generate_agnosticv(capacity_plan, seats=seats, repo_url=repo_url, slug_override=slug or None)
        write_agnosticv(config, agnosticv_dir)
        click.echo(f"AgnosticV catalog item written to {agnosticv_dir}/")
        click.echo(f"  common.yaml, dev.yaml, test.yaml, prod.yaml")
        click.echo(f"  Review and adjust before committing.")
    elif output:
        write_plan(capacity_plan, output)
        click.echo(f"Plan written to {output}")
    else:
        import yaml
        click.echo(yaml.dump(capacity_plan, default_flow_style=False))


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, path_type=Path))
@click.argument("agnosticv_path", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "fmt", type=click.Choice(["yaml", "table"]), default="table")
def validate(repo_path: Path, agnosticv_path: Path, fmt: str):
    """Validate an agnosticv config against a repo scan."""
    results = scan_repo(repo_path)
    capacity_plan = recommend_tier(results)
    comparison = compare_against_agnosticv(capacity_plan, agnosticv_path)

    if fmt == "yaml":
        import yaml
        click.echo(yaml.dump(comparison, default_flow_style=False))
    else:
        _print_validation_table(comparison)


@main.command()
@click.argument("repos_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
@click.option("--format", "fmt", type=click.Choice(["yaml", "table"]), default="table")
def batch(repos_dir: Path, output: Path | None, fmt: str):
    """Scan all repos in a directory and summarize."""
    from rich.console import Console
    from rich.table import Table

    repos_dir = Path(repos_dir)
    results = []

    for child in sorted(repos_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        try:
            scan_results = scan_repo(child)
            plan_result = recommend_tier(scan_results)
            results.append(plan_result)
        except Exception as e:
            click.echo(f"  [skip] {child.name}: {e}", err=True)

    if output:
        import yaml
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            yaml.dump(results, f, default_flow_style=False, sort_keys=False)
        click.echo(f"Batch results written to {output}")
    elif fmt == "yaml":
        import yaml
        click.echo(yaml.dump(results, default_flow_style=False))
    else:
        console = Console()
        table = Table(title="Batch Scan Summary")
        table.add_column("Repo", style="cyan")
        table.add_column("Tier", style="bold")
        table.add_column("CPU", justify="right")
        table.add_column("Memory (GB)", justify="right")
        table.add_column("Storage (GB)", justify="right")
        table.add_column("Models")
        table.add_column("Local Inference")

        for r in results:
            est = r.get("resource_estimate", {})
            models = r.get("models_detected", [])
            repo_name = Path(r.get("repo", "")).name
            tier = r["recommended_tier"]
            tier_style = {"pilot": "green", "partner": "yellow", "dedicated": "red"}.get(tier, "")
            table.add_row(
                repo_name,
                f"[{tier_style}]{tier}[/{tier_style}]",
                str(est.get("cpu_cores", "?")),
                str(round(est.get("memory_gb", 0), 1)),
                str(round(est.get("storage_gb", 0), 1)),
                str(len(models)),
                "yes" if est.get("local_inference") else "no",
            )
        console.print(table)


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


def _print_validation_table(comparison: dict):
    """Print validation comparison as a rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print(f"\n[bold]Repo:[/bold] {comparison.get('repo', '?')}")
    console.print(f"[bold]AgnosticV:[/bold] {comparison.get('agnosticv_path', '?')}")

    rec_tier = comparison.get("recommended_tier", "?")
    actual_tier = comparison.get("actual_tier", "?")
    match = comparison.get("tier_match", False)
    match_icon = "[green]MATCH[/green]" if match else "[red]MISMATCH[/red]"
    console.print(f"\n[bold]Tier:[/bold] recommended={rec_tier}, actual={actual_tier} {match_icon}")

    deltas = comparison.get("resource_deltas", {})
    if deltas:
        table = Table(title="Resource Comparison")
        table.add_column("Resource", style="cyan")
        table.add_column("Recommended", justify="right")
        table.add_column("Provisioned", justify="right")
        table.add_column("Delta", justify="right")
        table.add_column("Status")

        for key, delta in deltas.items():
            rec_val = str(delta.get("recommended", "—"))
            actual_val = str(delta.get("provisioned", "—"))
            diff = delta.get("delta", 0)
            if diff > 0:
                status = "[yellow]over-provisioned[/yellow]"
            elif diff < 0:
                status = "[red]under-provisioned[/red]"
            else:
                status = "[green]matched[/green]"
            table.add_row(key, rec_val, actual_val, str(diff), status)
        console.print(table)

    model_diff = comparison.get("model_coverage", {})
    if model_diff.get("missing_from_agnosticv") or model_diff.get("extra_in_agnosticv"):
        console.print("\n[bold]Model Coverage:[/bold]")
        if model_diff.get("missing_from_agnosticv"):
            console.print(f"  [red]Missing from agnosticv:[/red] {', '.join(model_diff['missing_from_agnosticv'])}")
        if model_diff.get("extra_in_agnosticv"):
            console.print(f"  [yellow]Extra in agnosticv:[/yellow] {', '.join(model_diff['extra_in_agnosticv'])}")
