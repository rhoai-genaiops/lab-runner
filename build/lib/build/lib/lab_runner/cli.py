"""CLI interface for lab runner."""

import click
from rich.console import Console
from rich.table import Table

from lab_runner.config import Config
from lab_runner.modules import MODULE_REGISTRY
from lab_runner.runner import Runner, resolve_dependencies

console = Console()


def parse_modules(ctx, param, value: str | None) -> list[int] | None:
    if value is None:
        return None
    try:
        return [int(x.strip()) for x in value.split(",")]
    except ValueError:
        raise click.BadParameter("Module IDs must be comma-separated integers (e.g., 2,3,5)")


@click.group()
def cli():
    """Lab Runner — automated exercise verification for AI501."""


@cli.command()
@click.option("-u", "--username", required=True, help="OpenShift username (e.g., user1)")
@click.option("-p", "--password", required=True, help="OpenShift password")
@click.option(
    "-c",
    "--cluster-domain",
    required=True,
    help="Cluster apps domain (e.g., apps.cluster.example.com)",
)
@click.option(
    "-m",
    "--modules",
    callback=parse_modules,
    help="Comma-separated module IDs to run (e.g., 2,3,5)",
)
@click.option("--up-to", type=int, help="Run all modules up to and including this ID")
@click.option("--dry-run", is_flag=True, help="Preview steps without executing")
@click.option("--verbose", is_flag=True, help="Show detailed output on errors")
def run(username, password, cluster_domain, modules, up_to, dry_run, verbose):
    """Run lab modules (auto-resolves dependencies)."""
    config = Config(
        username=username,
        password=password,
        cluster_domain=cluster_domain,
        dry_run=dry_run,
        verbose=verbose,
    )
    runner = Runner(config)

    if up_to:
        module_ids = [mid for mid in sorted(MODULE_REGISTRY) if mid <= up_to]
    elif modules:
        module_ids = modules
    else:
        raise click.UsageError("Specify --modules (-m) or --up-to")

    # Validate all IDs exist
    for mid in module_ids:
        if mid not in MODULE_REGISTRY:
            raise click.UsageError(f"Unknown module ID: {mid}")

    success = runner.run_modules(module_ids)
    raise SystemExit(0 if success else 1)


@cli.command()
@click.option("-u", "--username", required=True)
@click.option("-p", "--password", required=True)
@click.option("-c", "--cluster-domain", required=True)
@click.option("-m", "--modules", required=True, callback=parse_modules)
@click.option("--verbose", is_flag=True)
def verify(username, password, cluster_domain, modules, verbose):
    """Verify module state without making changes."""
    config = Config(
        username=username,
        password=password,
        cluster_domain=cluster_domain,
        verbose=verbose,
    )
    runner = Runner(config)
    success = runner.verify_modules(modules)
    raise SystemExit(0 if success else 1)


@cli.command()
@click.option("-u", "--username", required=True)
@click.option("-p", "--password", required=True)
@click.option("-c", "--cluster-domain", required=True)
@click.option("--verbose", is_flag=True)
def status(username, password, cluster_domain, verbose):
    """Show deployed vs missing state for all modules."""
    config = Config(
        username=username,
        password=password,
        cluster_domain=cluster_domain,
        verbose=verbose,
    )
    runner = Runner(config)
    runner.show_status()


@cli.command(name="list")
def list_modules():
    """Show available modules with dependency graph."""
    table = Table(title="Available Modules")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Name", style="bold")
    table.add_column("Dependencies")

    for mid in sorted(MODULE_REGISTRY):
        module = MODULE_REGISTRY[mid]()
        deps = ", ".join(str(d) for d in module.dependencies) if module.dependencies else "—"
        table.add_row(str(mid), module.name, deps)

    console.print(table)

    console.print()
    console.print("[dim]Dependency graph:[/dim]")
    console.print("[dim]  Module 2 (Linguistics)[/dim]")
    console.print("[dim]    └─ Module 3 (Scale 101)[/dim]")
    console.print("[dim]        ├─ Module 4 (Scale 201) → Module 5 (RAG) → Module 8 (Agents)[/dim]")
    console.print("[dim]        ├─ Module 6 (Observability)[/dim]")
    console.print("[dim]        ├─ Module 7 (Guardrails) ──────────────────┘[/dim]")
    console.print("[dim]        ├─ Module 9 (On-Prem)[/dim]")
    console.print("[dim]        ├─ Module 10 (Optimization)[/dim]")
    console.print("[dim]        └─ Module 12 (Fine-Tuning)[/dim]")


if __name__ == "__main__":
    cli()
