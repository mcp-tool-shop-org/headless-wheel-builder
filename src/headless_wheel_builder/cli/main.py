"""CLI entry point for Headless Wheel Builder.

This module provides the main command-line interface using Click.
Actual command logic is delegated to focused modules in the commands package.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from headless_wheel_builder import __version__
from headless_wheel_builder.actions.cli import actions as actions_group
from headless_wheel_builder.cache.cli import cache as cache_group
from headless_wheel_builder.changelog.cli import changelog as changelog_group
from headless_wheel_builder.cli.commands import (
    execute_build,
    execute_inspect,
    run_async,
    validate_build_options,
)
from headless_wheel_builder.depgraph.cli import deps as deps_group
from headless_wheel_builder.exceptions import BuildError, HWBError
from headless_wheel_builder.github.cli import github as github_group
from headless_wheel_builder.metrics.cli import metrics as metrics_group
from headless_wheel_builder.multirepo.cli import multirepo as multirepo_group
from headless_wheel_builder.notify.cli import notify as notify_group
from headless_wheel_builder.pipeline.cli import pipeline as pipeline_group
from headless_wheel_builder.release.cli import release as release_group
from headless_wheel_builder.security.cli import security as security_group

console = Console()
error_console = Console(stderr=True)


@click.group()
@click.version_option(__version__, prog_name="hwb")
@click.option("-v", "--verbose", count=True, help="Increase verbosity")
@click.option("-q", "--quiet", is_flag=True, help="Suppress non-error output")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: int,
    quiet: bool,
    json_output: bool,
    no_color: bool,
) -> None:
    """Headless Wheel Builder - Build Python wheels anywhere."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["json"] = json_output
    ctx.obj["no_color"] = no_color

    if no_color:
        console._force_terminal = False


@cli.command()
@click.argument("source", default=".")
@click.option("-o", "--output", "output_dir", default="dist", help="Output directory")
@click.option("--python", default="3.12", help="Python version to use")
@click.option("--wheel/--no-wheel", default=True, help="Build wheel")
@click.option("--sdist/--no-sdist", default=False, help="Build source distribution")
@click.option("--clean", is_flag=True, help="Clean output directory before building")
@click.option(
    "--isolation",
    type=click.Choice(["auto", "venv", "docker", "none"]),
    default="auto",
    help="Build isolation strategy",
)
@click.option(
    "-C",
    "--config-setting",
    multiple=True,
    help="Pass config setting to build backend",
)
@click.option(
    "--platform",
    type=click.Choice(["auto", "manylinux", "musllinux"]),
    default="auto",
    help="Docker platform (only with --isolation docker)",
)
@click.option(
    "--docker-image",
    default=None,
    help="Specific Docker image to use (overrides --platform)",
)
@click.option(
    "--arch",
    type=click.Choice(["x86_64", "aarch64", "i686"]),
    default="x86_64",
    help="Target architecture for Docker builds",
)
@click.option(
    "--no-deps",
    is_flag=True,
    help="Don't install build dependencies (requires pre-installed)",
)
@click.pass_context
def build(
    ctx: click.Context,
    source: str,
    output_dir: str,
    python: str,
    wheel: bool,
    sdist: bool,
    clean: bool,
    isolation: str,
    config_setting: tuple[str, ...],
    platform: str,
    docker_image: str | None,
    arch: str,
    no_deps: bool,
) -> None:
    """Build wheels from a Python project.

    SOURCE is the project directory (default: current directory).
    """
    try:
        # Validate options
        validate_build_options(
            source=source,
            output_dir=output_dir,
            python=python,
            isolation=isolation,
            docker_image=docker_image,
            platform=platform,
        )

        # Execute build
        run_async(
            execute_build(
                source=source,
                output_dir=output_dir,
                python=python,
                wheel=wheel,
                sdist=sdist,
                clean=clean,
                isolation=isolation,
                config_settings=config_setting,
                platform=platform,
                docker_image=docker_image,
                arch=arch,
                no_deps=no_deps,
                verbose=ctx.obj.get("verbose", 0),
            )
        )
    except HWBError as e:
        error_console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)
    except KeyboardInterrupt:
        error_console.print("\n[yellow]Build interrupted by user[/yellow]")
        raise SystemExit(130)


@cli.command()
@click.argument("source", default=".")
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "table"]),
    default="text",
    help="Output format",
)
@click.option(
    "--check",
    is_flag=True,
    help="Only check for errors, don't print metadata",
)
@click.pass_context
def inspect(
    ctx: click.Context,
    source: str,
    output_format: str,
    check: bool,
) -> None:
    """Inspect a Python project and display its metadata.

    SOURCE is the project directory (default: current directory).
    """
    try:
        run_async(execute_inspect(source, output_format, check))
    except HWBError as e:
        error_console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("version")
def version() -> None:
    """Show version information."""
    console.print(f"Headless Wheel Builder {__version__}")


@cli.command("images")
@click.option(
    "--check",
    is_flag=True,
    help="Check if images are available",
)
def list_images(check: bool) -> None:
    """List available Docker images for builds."""
    from headless_wheel_builder.isolation.docker import MANYLINUX_IMAGES

    if check:
        # Check image availability
        console.print("[cyan]Checking Docker image availability...[/cyan]")
        # This would require Docker to be running
        console.print("[yellow]Docker check requires Docker daemon running[/yellow]")
        return

    console.print("\n[bold cyan]Available Manylinux Images:[/bold cyan]")
    for key, url in sorted(MANYLINUX_IMAGES.items()):
        console.print(f"  {key:<30} {url}")


@cli.command("version-next")
@click.argument("current_version")
@click.option(
    "--part",
    type=click.Choice(["major", "minor", "patch"]),
    default="patch",
    help="Version part to increment",
)
def version_next(current_version: str, part: str) -> None:
    """Calculate next version number."""
    from packaging.version import Version

    try:
        current = Version(current_version)
    except Exception as e:
        error_console.print(f"[red]Invalid version: {current_version}[/red]")
        raise SystemExit(1)

    parts = current.major, current.minor, current.micro
    major, minor, patch = parts

    if part == "major":
        next_version = f"{major + 1}.0.0"
    elif part == "minor":
        next_version = f"{major}.{minor + 1}.0"
    else:  # patch
        next_version = f"{major}.{minor}.{patch + 1}"

    console.print(next_version)


# Add command groups
cli.add_command(actions_group)
cli.add_command(cache_group)
cli.add_command(changelog_group)
cli.add_command(deps_group)
cli.add_command(github_group)
cli.add_command(metrics_group)
cli.add_command(multirepo_group)
cli.add_command(notify_group)
cli.add_command(pipeline_group)
cli.add_command(release_group)
cli.add_command(security_group)


def main() -> None:
    """Main entry point."""
    try:
        cli(obj={})
    except (BrokenPipeError, KeyboardInterrupt):
        # Handle broken pipe (when output is piped) and Ctrl+C
        sys.exit(130 if isinstance(sys.exc_info()[1], KeyboardInterrupt) else 1)
    except Exception as e:
        error_console.print(f"[red]Unexpected error: {e}[/red]")
        import traceback

        if "-v" in sys.argv or "--verbose" in sys.argv:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
