"""Build command implementation for Headless Wheel Builder CLI.

This module handles the 'build' command which compiles Python projects
into wheels and source distributions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console

from headless_wheel_builder.core.builder import BuildConfig, BuildEngine

console = Console()
error_console = Console(stderr=True)


def validate_build_options(
    source: str,
    output_dir: str,
    python: str,
    isolation: str,
    docker_image: str | None,
    platform: str,
) -> None:
    """Validate build command options.

    Args:
        source: Source directory path
        output_dir: Output directory path
        python: Python version
        isolation: Isolation strategy
        docker_image: Optional Docker image override
        platform: Docker platform type

    Raises:
        click.BadParameter: If options are invalid
    """
    source_path = Path(source).resolve()
    if not source_path.exists():
        raise click.BadParameter(f"Source directory not found: {source}")

    if not source_path.is_dir():
        raise click.BadParameter(f"Source is not a directory: {source}")

    # Validate pyproject.toml exists
    if not (source_path / "pyproject.toml").exists():
        raise click.BadParameter(
            f"No pyproject.toml found in {source}",
            param_hint="source",
        )

    # Validate Python version format
    if not python or not any(c.isdigit() for c in python):
        raise click.BadParameter(
            f"Invalid Python version format: {python}",
            param_hint="python",
        )

    # Docker-specific validation
    if isolation == "docker" and docker_image and platform != "auto":
        raise click.BadParameter(
            "Cannot use both --docker-image and --platform",
            param_hint="docker-image",
        )


def run_async(coro):
    """Run an async function synchronously.

    On Windows, uses ProactorEventLoop which supports subprocess operations.
    On other platforms, uses the default event loop.

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine
    """
    return asyncio.run(coro)


async def execute_build(
    source: str,
    output_dir: str,
    python: str,
    wheel: bool,
    sdist: bool,
    clean: bool,
    isolation: str,
    config_settings: tuple[str, ...],
    platform: str,
    docker_image: str | None,
    arch: str,
    no_deps: bool,
    verbose: int,
) -> None:
    """Execute the build operation.

    Args:
        source: Source directory
        output_dir: Output directory
        python: Python version
        wheel: Build wheel
        sdist: Build source distribution
        clean: Clean output directory first
        isolation: Isolation strategy
        config_settings: Build backend config settings
        platform: Docker platform
        docker_image: Specific Docker image
        arch: Target architecture
        no_deps: Don't install build dependencies
        verbose: Verbosity level
    """
    source_path = Path(source).resolve()
    output_path = Path(output_dir).resolve()

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Create build config
    config = BuildConfig(
        source=source_path,
        output=output_path,
        python_version=python,
        build_wheel=wheel,
        build_sdist=sdist,
        clean_output=clean,
        isolation_strategy=isolation,
        docker_platform=platform,
        docker_image=docker_image,
        docker_arch=arch,
        no_dependencies=no_deps,
        config_settings=dict(_parse_config_settings(config_settings)),
        verbose=verbose,
    )

    # Execute build
    engine = BuildEngine(config=config)
    result = await engine.build()

    # Print results
    if result.success:
        _print_build_success(result, verbose)
    else:
        _print_build_failure(result, verbose)
        raise SystemExit(1)


def _parse_config_settings(
    settings: tuple[str, ...],
) -> list[tuple[str, str]]:
    """Parse config settings from Click option.

    Args:
        settings: Config settings in KEY=VALUE format

    Returns:
        List of (key, value) tuples

    Raises:
        click.BadParameter: If format is invalid
    """
    parsed = []
    for setting in settings:
        if "=" not in setting:
            raise click.BadParameter(
                f"Config setting must be KEY=VALUE format: {setting}",
                param_hint="config-setting",
            )
        key, value = setting.split("=", 1)
        parsed.append((key, value))
    return parsed


def _print_build_success(result, verbose: int) -> None:
    """Print successful build results.

    Args:
        result: BuildResult object
        verbose: Verbosity level
    """
    from rich.panel import Panel
    from rich.table import Table

    table = Table(title="Build Summary", show_header=True, header_style="bold cyan")
    table.add_column("Artifact", style="green")
    table.add_column("Size", justify="right")
    table.add_column("Python", justify="center")

    if result.wheel_path:
        size_mb = result.wheel_path.stat().st_size / (1024 * 1024)
        table.add_row(
            result.wheel_path.name,
            f"{size_mb:.2f} MB",
            result.python_tag or "N/A",
        )

    if result.sdist_path:
        size_mb = result.sdist_path.stat().st_size / (1024 * 1024)
        table.add_row(
            result.sdist_path.name,
            f"{size_mb:.2f} MB",
            "source",
        )

    console.print(Panel(table, title="✓ Build Successful"))

    if verbose > 0:
        console.print(f"Output: {result.wheel_path or result.sdist_path}")


def _print_build_failure(result, verbose: int) -> None:
    """Print failed build results.

    Args:
        result: BuildResult object
        verbose: Verbosity level
    """
    from rich.panel import Panel

    error_console.print(Panel(f"✗ Build Failed\n{result.error}", style="red"))

    if verbose > 0 and result.build_log:
        error_console.print("\n[dim]Build Log:[/dim]")
        error_console.print(result.build_log[:500])  # Show first 500 chars
