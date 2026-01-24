"""CLI for security scanning."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from headless_wheel_builder.security.models import ScanResult, ScanType, Severity
from headless_wheel_builder.security.scanner import ScannerConfig, SecurityScanner

if TYPE_CHECKING:
    from collections.abc import Coroutine

console = Console()
error_console = Console(stderr=True)

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run async function."""
    return asyncio.run(coro)


@click.group(name="security")
def security() -> None:
    """Security scanning.

    Scan for vulnerabilities and security issues.
    """
    pass


@security.command("scan")
@click.option("--path", "-p", default=".", help="Project path to scan")
@click.option(
    "--type",
    "scan_type",
    type=click.Choice(["all", "vulnerability", "code"]),
    default="all",
    help="Type of scan",
)
@click.option("--fail-critical", is_flag=True, help="Fail on critical issues")
@click.option("--fail-high", is_flag=True, help="Fail on high severity issues")
@click.option("--ignore", multiple=True, help="Vulnerability IDs to ignore")
@click.option("--timeout", default=300, help="Scan timeout in seconds")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def scan(
    path: str,
    scan_type: str,
    fail_critical: bool,
    fail_high: bool,
    ignore: tuple[str, ...],
    timeout: int,
    json_output: bool,
) -> None:
    """Run security scan on a project.

    Examples:

        hwb security scan                        # Scan current directory

        hwb security scan -p ./myproject         # Scan specific path

        hwb security scan --type vulnerability   # Only dependency scan

        hwb security scan --fail-critical        # Exit 1 on critical issues
    """
    config = ScannerConfig(
        project_path=path,
        fail_on_critical=fail_critical,
        fail_on_high=fail_high,
        timeout=timeout,
        ignore_ids=list(ignore),
    )

    scanner = SecurityScanner(config)

    async def _scan():
        if scan_type == "vulnerability":
            return [await scanner.scan_vulnerabilities()]
        elif scan_type == "code":
            return [await scanner.scan_code_security()]
        else:
            return await scanner.scan_all()

    if not json_output:
        console.print("\n[bold blue]Running security scan...[/]")
        console.print(f"  Path: {path}")
        console.print(f"  Type: {scan_type}")
        console.print()

    results = run_async(_scan())

    if json_output:
        output = {
            "success": all(r.success for r in results),
            "should_fail": scanner.should_fail(results),
            "results": [r.to_dict() for r in results],
        }
        click.echo(json.dumps(output, indent=2))
    else:
        _print_scan_results(results)

    if scanner.should_fail(results):
        sys.exit(1)


@security.command("check")
@click.option("--path", "-p", default=".", help="Project path")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def quick_check(path: str, json_output: bool) -> None:
    """Quick security check (vulnerability scan only).

    A faster scan that only checks for known vulnerabilities
    in dependencies without code analysis.
    """
    config = ScannerConfig(project_path=path)
    scanner = SecurityScanner(config)

    async def _check():
        return await scanner.scan_vulnerabilities()

    if not json_output:
        console.print("\n[bold blue]Quick security check...[/]")
        console.print()

    result = run_async(_check())

    if json_output:
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _print_vulnerability_result(result)

    if result.has_critical or result.has_high:
        sys.exit(1)


@security.command("tools")
def list_tools() -> None:
    """List available security scanning tools and their status."""
    import shutil

    console.print("\n[bold]Security Scanning Tools[/]\n")

    table = Table()
    table.add_column("Tool", style="cyan")
    table.add_column("Purpose")
    table.add_column("Status")
    table.add_column("Install")

    tools = [
        ("pip-audit", "Dependency vulnerability scanning", "pip install pip-audit"),
        ("bandit", "Python code security analysis", "pip install bandit"),
        ("safety", "Dependency safety checks", "pip install safety"),
    ]

    for name, purpose, install in tools:
        available = shutil.which(name) is not None
        status = "[green]Available[/]" if available else "[yellow]Not installed[/]"
        table.add_row(name, purpose, status, install)

    console.print(table)
    console.print()


def _print_scan_results(results: list[ScanResult]) -> None:
    """Print scan results."""
    for result in results:
        if result.scan_type == ScanType.VULNERABILITY:
            _print_vulnerability_result(result)
        elif result.scan_type == ScanType.CODE_SECURITY:
            _print_code_security_result(result)
        console.print()


def _print_vulnerability_result(result: ScanResult) -> None:
    """Print vulnerability scan result."""
    if not result.success:
        console.print(
            Panel(
                f"[red]Scan failed:[/] {result.error}",
                title="Vulnerability Scan",
                border_style="red",
            )
        )
        return

    if not result.vulnerabilities:
        console.print(
            Panel(
                "[green]No vulnerabilities found[/]",
                title="Vulnerability Scan",
                border_style="green",
            )
        )
        return

    table = Table(title="Vulnerabilities Found")
    table.add_column("ID", style="cyan")
    table.add_column("Package")
    table.add_column("Installed")
    table.add_column("Fixed")
    table.add_column("Severity")

    for vuln in result.vulnerabilities:
        severity_style = _severity_style(vuln.severity)
        table.add_row(
            vuln.id,
            vuln.package,
            vuln.installed_version,
            vuln.fixed_version or "-",
            f"[{severity_style}]{vuln.severity.value}[/]",
        )

    console.print(table)

    counts = result.get_severity_counts()
    summary: list[str] = []
    if counts.get("critical", 0) > 0:
        summary.append(f"[red]{counts['critical']} critical[/]")
    if counts.get("high", 0) > 0:
        summary.append(f"[yellow]{counts['high']} high[/]")
    if counts.get("medium", 0) > 0:
        summary.append(f"[blue]{counts['medium']} medium[/]")
    if counts.get("low", 0) > 0:
        summary.append(f"[dim]{counts['low']} low[/]")

    console.print(f"\nTotal: {', '.join(summary)}")


def _print_code_security_result(result: ScanResult) -> None:
    """Print code security scan result."""
    if not result.success:
        console.print(
            Panel(
                f"[red]Scan failed:[/] {result.error}",
                title="Code Security Scan",
                border_style="red",
            )
        )
        return

    if not result.issues:
        console.print(
            Panel(
                "[green]No security issues found[/]",
                title="Code Security Scan",
                border_style="green",
            )
        )
        return

    table = Table(title="Security Issues Found")
    table.add_column("Type", style="cyan")
    table.add_column("File")
    table.add_column("Line")
    table.add_column("Severity")
    table.add_column("Message", max_width=40)

    for issue in result.issues:
        severity_style = _severity_style(issue.severity)
        file_name = Path(issue.file).name if issue.file else "-"
        table.add_row(
            issue.type,
            file_name,
            str(issue.line) if issue.line else "-",
            f"[{severity_style}]{issue.severity.value}[/]",
            issue.message[:40] + "..." if len(issue.message) > 40 else issue.message,
        )

    console.print(table)


def _severity_style(severity: Severity) -> str:
    """Get style for severity level."""
    styles = {
        Severity.CRITICAL: "red bold",
        Severity.HIGH: "red",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "dim",
        Severity.UNKNOWN: "dim",
    }
    return styles.get(severity, "dim")
