"""Orchestrator: dependency resolution, step execution, progress reporting."""

import heapq
from collections import deque

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lab_runner.config import Config
from lab_runner.modules import MODULE_REGISTRY
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step, StepResult, StepStatus

console = Console()


def resolve_dependencies(requested: list[int]) -> list[int]:
    """Topological sort of modules including all transitive dependencies."""
    all_needed: set[int] = set()
    queue = deque(requested)

    while queue:
        mid = queue.popleft()
        if mid in all_needed:
            continue
        if mid not in MODULE_REGISTRY:
            console.print(f"[red]Unknown module: {mid}[/red]")
            raise SystemExit(1)
        all_needed.add(mid)
        module: Module = MODULE_REGISTRY[mid]()
        for dep in module.dependencies:
            if dep not in all_needed:
                queue.append(dep)

    # Topological sort via Kahn's algorithm
    in_degree: dict[int, int] = {mid: 0 for mid in all_needed}
    adj: dict[int, list[int]] = {mid: [] for mid in all_needed}
    for mid in all_needed:
        module = MODULE_REGISTRY[mid]()
        for dep in module.dependencies:
            if dep in all_needed:
                adj[dep].append(mid)
                in_degree[mid] += 1

    # Use a min-heap so modules with lower IDs run first when multiple are ready
    heap = sorted(mid for mid, deg in in_degree.items() if deg == 0)
    heapq.heapify(heap)
    order: list[int] = []
    while heap:
        mid = heapq.heappop(heap)
        order.append(mid)
        for neighbor in adj[mid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                heapq.heappush(heap, neighbor)

    return order


class Runner:
    def __init__(self, config: Config):
        self.config = config

    def run_modules(self, module_ids: list[int]) -> bool:
        """Run modules in dependency order. Returns True if all succeeded."""
        order = resolve_dependencies(module_ids)
        modules = [(mid, MODULE_REGISTRY[mid]()) for mid in order]

        console.print()
        console.print(
            Panel(
                f"Running {len(modules)} module(s): "
                + ", ".join(f"[bold]{m.name}[/bold]" for _, m in modules),
                title="Lab Runner",
                border_style="blue",
            )
        )

        if self.config.dry_run:
            self._print_dry_run(modules)
            return True

        all_ok = True
        for mid, module in modules:
            if not self._run_module(module):
                all_ok = False
                break

        if all_ok:
            console.print()
            console.print("[bold green]All modules completed successfully.[/bold green]")
        return all_ok

    def verify_modules(self, module_ids: list[int]) -> bool:
        """Verify modules without running. Returns True if all pass."""
        order = resolve_dependencies(module_ids)
        all_ok = True

        for mid in order:
            module = MODULE_REGISTRY[mid]()
            steps = module.get_steps(self.config)
            passed = sum(1 for s in steps if s.verify(self.config))
            total = len(steps)
            status = "[green]PASS[/green]" if passed == total else "[yellow]PARTIAL[/yellow]"
            if passed == 0:
                status = "[red]MISSING[/red]"
            console.print(
                f"  Module {mid} ({module.name}): {status} ({passed}/{total} steps verified)"
            )
            if passed < total:
                all_ok = False

        return all_ok

    def show_status(self) -> None:
        """Show cluster status for all known modules."""
        table = Table(title="Cluster Status")
        table.add_column("Module", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Status")
        table.add_column("Steps", justify="right")

        for mid in sorted(MODULE_REGISTRY):
            module = MODULE_REGISTRY[mid]()
            steps = module.get_steps(self.config)
            passed = 0
            for s in steps:
                try:
                    if s.verify(self.config):
                        passed += 1
                except Exception:
                    pass
            total = len(steps)
            if passed == total:
                status = "[green]Complete[/green]"
            elif passed > 0:
                status = "[yellow]Partial[/yellow]"
            else:
                status = "[dim]Not started[/dim]"
            table.add_row(str(mid), module.name, status, f"{passed}/{total}")

        console.print(table)

    def _run_module(self, module: Module) -> bool:
        console.print()
        console.rule(f"[bold blue]Module {module.id}: {module.name}[/bold blue]")

        steps = module.get_steps(self.config)
        for i, step in enumerate(steps, 1):
            prefix = f"  [{i}/{len(steps)}]"

            # Check if already done
            if step.skip_if_done():
                try:
                    if step.verify(self.config):
                        console.print(
                            f"{prefix} [dim]{step.description} — already done, skipping[/dim]"
                        )
                        continue
                except Exception:
                    pass  # verification failed, proceed to run

            console.print(f"{prefix} {step.active_description}", end="")

            try:
                result = step.run(self.config)
            except Exception as e:
                result = StepResult.failed(str(e))

            if result.status == StepStatus.SUCCESS:
                console.print(f"\r{prefix} [green]✓[/green] {step.description}")
            elif result.status == StepStatus.SKIPPED:
                console.print(
                    f"\r{prefix} [dim]{step.description} — {result.message}[/dim]"
                )
            else:
                console.print(f"\r{prefix} [red]✗[/red] {step.description}")
                console.print(f"    [red]Error: {result.message}[/red]")
                if result.output and self.config.verbose:
                    console.print(Panel(result.output, title="Output", border_style="red"))
                return False

        console.print(f"  [green]Module {module.id} complete.[/green]")
        return True

    def run_modules_streaming(self, module_ids: list[int]):
        """Run modules in dependency order, yielding progress dicts for SSE."""
        try:
            order = resolve_dependencies(module_ids)
        except SystemExit:
            yield {"type": "error", "message": "Unknown module ID in request"}
            yield {"type": "complete", "success": False}
            return

        modules = [(mid, MODULE_REGISTRY[mid]()) for mid in order]

        for mid, module in modules:
            steps = module.get_steps(self.config)
            yield {
                "type": "module_start",
                "module_id": mid,
                "module_name": module.name,
                "total_steps": len(steps),
            }

            failed = False
            for i, step in enumerate(steps, 1):
                # Check if already done
                if step.skip_if_done():
                    try:
                        if step.verify(self.config):
                            yield {
                                "type": "step_done",
                                "step": i,
                                "total": len(steps),
                                "status": "skipped",
                                "description": step.description,
                            }
                            continue
                    except Exception:
                        pass

                yield {
                    "type": "step_start",
                    "step": i,
                    "total": len(steps),
                    "description": step.active_description,
                }

                try:
                    result = step.run(self.config)
                except Exception as e:
                    result = StepResult.failed(str(e))

                if result.status == StepStatus.SUCCESS:
                    yield {
                        "type": "step_done",
                        "step": i,
                        "total": len(steps),
                        "status": "success",
                        "description": step.description,
                    }
                elif result.status == StepStatus.SKIPPED:
                    yield {
                        "type": "step_done",
                        "step": i,
                        "total": len(steps),
                        "status": "skipped",
                        "description": step.description,
                    }
                else:
                    yield {
                        "type": "error",
                        "step": i,
                        "total": len(steps),
                        "description": step.description,
                        "message": result.message,
                        "output": result.output,
                    }
                    failed = True
                    break

            yield {
                "type": "module_done",
                "module_id": mid,
                "status": "failed" if failed else "success",
            }

            if failed:
                yield {"type": "complete", "success": False}
                return

        yield {"type": "complete", "success": True}

    def get_status(self) -> list[dict]:
        """Return status of all modules as a list of dicts (for JSON API)."""
        result = []
        for mid in sorted(MODULE_REGISTRY):
            module = MODULE_REGISTRY[mid]()
            steps = module.get_steps(self.config)
            passed = 0
            for s in steps:
                try:
                    if s.verify(self.config):
                        passed += 1
                except Exception:
                    pass
            total = len(steps)
            if passed == total:
                status = "complete"
            elif passed > 0:
                status = "partial"
            else:
                status = "not_started"
            result.append({
                "module_id": mid,
                "name": module.name,
                "status": status,
                "steps_passed": passed,
                "steps_total": total,
            })
        return result

    def _print_dry_run(self, modules: list[tuple[int, Module]]) -> None:
        console.print()
        console.print("[bold yellow]DRY RUN — no changes will be made[/bold yellow]")
        console.print()
        for mid, module in modules:
            console.print(f"[bold]Module {mid}: {module.name}[/bold]")
            steps = module.get_steps(self.config)
            for i, step in enumerate(steps, 1):
                console.print(f"  {i}. {step.description}")
            console.print()
