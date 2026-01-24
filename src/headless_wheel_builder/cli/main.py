"""CLI entry point for Headless Wheel Builder."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from headless_wheel_builder import __version__
from headless_wheel_builder.actions.cli import actions as actions_group
from headless_wheel_builder.cache.cli import cache as cache_group
from headless_wheel_builder.changelog.cli import changelog as changelog_group
from headless_wheel_builder.core.builder import BuildConfig, BuildEngine, BuildResult
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


def run_async(coro):
    """Run an async function.

    On Windows, we use the default ProactorEventLoop which supports
    subprocesses. The older SelectorEventLoop doesn't support subprocess
    operations which are needed for build isolation.
    """
    # Note: Don't set WindowsSelectorEventLoopPolicy on Windows!
    # It doesn't support subprocess operations which we need.
    # Python 3.14+ uses ProactorEventLoop by default on Windows.
    return asyncio.run(coro)


@click.group()
@click.version_option(__version__, prog_name="hwb")
@click.option("-v", "--verbose", count=True, help="Increase verbosity")
@click.option("-q", "--quiet", is_flag=True, help="Suppress non-error output")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.pass_context
def cli(ctx: click.Context, verbose: int, quiet: bool, json_output: bool, no_color: bool) -> None:
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
) -> None:
    """Build wheels from source.

    SOURCE can be a local path, git URL, or archive URL.

    Examples:

        hwb build                           # Build from current directory

        hwb build /path/to/project          # Build from local path

        hwb build https://github.com/user/repo  # Build from git

        hwb build https://github.com/user/repo@v1.0.0  # Specific tag

        hwb build --python 3.11 --sdist     # Python 3.11 with sdist

        hwb build --isolation docker        # Build manylinux wheel in Docker

        hwb build --isolation docker --platform musllinux  # Alpine/musl wheel
    """
    verbose = ctx.obj.get("verbose", 0)
    quiet = ctx.obj.get("quiet", False)
    json_output = ctx.obj.get("json", False)

    # Parse config settings
    config_settings = {}
    for setting in config_setting:
        if "=" in setting:
            key, value = setting.split("=", 1)
            config_settings[key] = value
        else:
            config_settings[setting] = ""

    async def _build() -> BuildResult:
        # Determine if using Docker
        use_docker = isolation == "docker"

        # Create build config
        config = BuildConfig(
            output_dir=Path(output_dir),
            python_version=python,
            build_wheel=wheel,
            build_sdist=sdist,
            clean_output=clean,
            config_settings=config_settings if config_settings else None,
            use_docker=use_docker,
            docker_platform=platform,
            docker_image=docker_image,
            docker_architecture=arch,
        )

        engine = BuildEngine(config)

        if not quiet and not json_output:
            console.print(f"\n[bold blue]Building wheel for[/] {source}")
            console.print(f"  Python: {python}")
            console.print(f"  Output: {output_dir}")
            if use_docker:
                console.print(f"  Isolation: docker ({platform})")
                if docker_image:
                    console.print(f"  Image: {docker_image}")
                console.print(f"  Architecture: {arch}")
            elif isolation != "auto":
                console.print(f"  Isolation: {isolation}")
            console.print()

        # Build with progress indicator
        if not quiet and not json_output:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Building...", total=None)
                result = await engine.build(
                    source=source,
                    wheel=wheel,
                    sdist=sdist,
                )
                progress.remove_task(task)
        else:
            result = await engine.build(
                source=source,
                wheel=wheel,
                sdist=sdist,
            )

        return result

    try:
        result = run_async(_build())

        if json_output:
            import json

            output = {
                "success": result.success,
                "wheel": {
                    "path": str(result.wheel_path) if result.wheel_path else None,
                    "name": result.name,
                    "version": result.version,
                    "python_tag": result.python_tag,
                    "abi_tag": result.abi_tag,
                    "platform_tag": result.platform_tag,
                    "sha256": result.sha256,
                    "size_bytes": result.size_bytes,
                }
                if result.wheel_path
                else None,
                "sdist": str(result.sdist_path) if result.sdist_path else None,
                "duration_seconds": result.duration_seconds,
                "error": result.error,
            }
            if verbose:
                output["build_log"] = result.build_log
            click.echo(json.dumps(output, indent=2))
        elif not quiet:
            if result.success:
                _print_success(result, verbose)
            else:
                _print_failure(result, verbose)

        sys.exit(0 if result.success else 3)

    except HWBError as e:
        if json_output:
            import json

            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            error_console.print(f"\n[bold red]Error:[/] {e}")
            if verbose and isinstance(e, BuildError):
                error_console.print(f"\n[dim]{e.build_log}[/]")
        sys.exit(3)

    except KeyboardInterrupt:
        error_console.print("\n[yellow]Interrupted[/]")
        sys.exit(10)

    except Exception as e:
        if json_output:
            import json

            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            error_console.print(f"\n[bold red]Unexpected error:[/] {e}")
            if verbose:
                import traceback

                error_console.print(traceback.format_exc())
        sys.exit(1)


def _print_success(result: BuildResult, verbose: int) -> None:
    """Print successful build result."""
    console.print()

    if result.wheel_path:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="dim")
        table.add_column()

        table.add_row("Package", f"[bold]{result.name}[/]")
        table.add_row("Version", result.version or "unknown")
        table.add_row("Wheel", str(result.wheel_path))

        if result.size_bytes:
            size_kb = result.size_bytes / 1024
            size_str = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.1f} KB"
            table.add_row("Size", size_str)

        if result.python_tag:
            tags = f"{result.python_tag}-{result.abi_tag}-{result.platform_tag}"
            table.add_row("Tags", tags)

        table.add_row("Duration", f"{result.duration_seconds:.1f}s")

        console.print(Panel(table, title="[green]Build Successful[/]", border_style="green"))

    if result.sdist_path:
        console.print(f"  [dim]sdist:[/] {result.sdist_path}")

    if verbose and result.build_log:
        console.print("\n[dim]Build log:[/]")
        console.print(result.build_log)

    console.print()


def _print_failure(result: BuildResult, verbose: int) -> None:
    """Print failed build result."""
    console.print()
    console.print(
        Panel(
            f"[red]{result.error}[/]",
            title="[red]Build Failed[/]",
            border_style="red",
        )
    )

    if verbose and result.build_log:
        console.print("\n[dim]Build log:[/]")
        console.print(result.build_log)

    console.print()


@cli.command()
@click.argument("source", default=".")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
@click.option("--check", is_flag=True, help="Exit with error if issues found")
@click.pass_context
def inspect(ctx: click.Context, source: str, output_format: str, check: bool) -> None:
    """Analyze project configuration.

    Shows project metadata, build backend, dependencies, and potential issues.
    """
    from headless_wheel_builder.core.analyzer import ProjectAnalyzer
    from headless_wheel_builder.core.source import SourceResolver

    async def _inspect():
        resolver = SourceResolver()
        analyzer = ProjectAnalyzer()

        spec = resolver.parse_source(source)
        resolved = await resolver.resolve(spec)
        metadata = await analyzer.analyze(resolved.local_path)

        return metadata, resolved

    try:
        metadata, resolved = run_async(_inspect())

        if output_format == "json":
            import json

            output = {
                "name": metadata.name,
                "version": metadata.version,
                "path": str(resolved.local_path),
                "requires_python": metadata.requires_python,
                "backend": {
                    "name": metadata.backend.name if metadata.backend else None,
                    "module": metadata.backend.module if metadata.backend else None,
                    "requirements": metadata.backend.requirements if metadata.backend else [],
                },
                "dependencies": metadata.dependencies,
                "optional_dependencies": metadata.optional_dependencies,
                "has_extensions": metadata.has_extension_modules,
                "extension_languages": metadata.extension_languages,
                "files": {
                    "pyproject.toml": metadata.has_pyproject,
                    "setup.py": metadata.has_setup_py,
                    "setup.cfg": metadata.has_setup_cfg,
                },
            }
            click.echo(json.dumps(output, indent=2))
        else:
            _print_inspect_result(metadata, resolved.local_path)

    except HWBError as e:
        error_console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


def _print_inspect_result(metadata, source_path: Path) -> None:
    """Print inspection result."""
    console.print()
    console.print(f"[bold]Project:[/] {metadata.name or 'unknown'}")
    console.print(f"[bold]Version:[/] {metadata.version or 'dynamic'}")
    console.print(f"[bold]Path:[/] {source_path}")
    console.print()

    # Build system
    console.print("[bold underline]Build System[/]")
    if metadata.backend:
        console.print(f"  Backend: {metadata.backend.name} ({metadata.backend.module})")
        console.print(f"  Requirements: {', '.join(metadata.backend.requirements)}")
    else:
        console.print("  [yellow]No build system configured[/]")
    console.print()

    # Metadata
    if metadata.requires_python:
        console.print(f"[bold]Requires Python:[/] {metadata.requires_python}")

    # Dependencies
    if metadata.dependencies:
        console.print(f"\n[bold underline]Dependencies[/] ({len(metadata.dependencies)})")
        for dep in metadata.dependencies[:10]:
            console.print(f"  - {dep}")
        if len(metadata.dependencies) > 10:
            console.print(f"  ... and {len(metadata.dependencies) - 10} more")

    # Optional dependencies
    if metadata.optional_dependencies:
        console.print("\n[bold underline]Optional Dependencies[/]")
        for group, deps in metadata.optional_dependencies.items():
            console.print(f"  {group}: {len(deps)} packages")

    # Extensions
    if metadata.has_extension_modules:
        console.print("\n[bold underline]Extension Modules[/]")
        console.print(f"  Languages: {', '.join(metadata.extension_languages)}")
    else:
        console.print("\n[dim]Pure Python package (no extensions)[/]")

    # Files
    console.print("\n[bold underline]Configuration Files[/]")
    files = [
        ("pyproject.toml", metadata.has_pyproject),
        ("setup.py", metadata.has_setup_py),
        ("setup.cfg", metadata.has_setup_cfg),
    ]
    for name, exists in files:
        status = "[green]Y[/]" if exists else "[dim]-[/]"
        console.print(f"  {status} {name}")

    console.print()


@cli.command()
def version() -> None:
    """Show version information."""
    console.print(f"hwb version {__version__}")


@cli.command("images")
@click.option("--check", is_flag=True, help="Check if Docker is available")
def list_images(check: bool) -> None:
    """List available manylinux/musllinux Docker images.

    Shows all supported images for building portable Linux wheels.
    """
    from headless_wheel_builder.isolation.docker import MANYLINUX_IMAGES, DockerIsolation

    async def _check_docker():
        isolation = DockerIsolation()
        return await isolation.check_available()

    if check:
        available = run_async(_check_docker())
        if available:
            console.print("[green]Docker is available[/]")
        else:
            console.print("[red]Docker is not available[/]")
            console.print("Install Docker Desktop or ensure the Docker daemon is running.")
            sys.exit(1)
        return

    console.print("\n[bold]Available Docker Images[/]\n")

    # Group by platform type
    manylinux = {}
    musllinux = {}

    for name, url in MANYLINUX_IMAGES.items():
        if name.startswith("musl"):
            musllinux[name] = url
        else:
            manylinux[name] = url

    console.print("[bold underline]manylinux (glibc)[/]")
    console.print("[dim]For most Linux distributions (Ubuntu, Debian, Fedora, etc.)[/]\n")
    for name, url in sorted(manylinux.items()):
        console.print(f"  {name}")
        console.print(f"    [dim]{url}[/]")

    console.print("\n[bold underline]musllinux (musl)[/]")
    console.print("[dim]For Alpine Linux and other musl-based distributions[/]\n")
    for name, url in sorted(musllinux.items()):
        console.print(f"  {name}")
        console.print(f"    [dim]{url}[/]")

    console.print("\n[bold]Usage:[/]")
    console.print("  hwb build --isolation docker")
    console.print("  hwb build --isolation docker --platform manylinux")
    console.print(
        "  hwb build --isolation docker --docker-image quay.io/pypa/manylinux_2_28_x86_64"
    )
    console.print()


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--repository",
    "-r",
    type=click.Choice(["pypi", "testpypi", "s3"]),
    default="pypi",
    help="Target repository",
)
@click.option("--token", envvar="PYPI_TOKEN", help="PyPI API token")
@click.option("--repository-url", help="Custom repository URL")
@click.option("--skip-existing", is_flag=True, help="Skip if version already exists")
@click.option("--dry-run", is_flag=True, help="Validate without uploading")
@click.option("--attestations", is_flag=True, help="Generate attestations (PEP 740)")
@click.option("--bucket", help="S3 bucket (for S3 publishing)")
@click.option("--prefix", default="", help="S3 key prefix")
@click.option("--region", default="us-east-1", help="S3 region")
@click.option("--generate-index", is_flag=True, help="Generate PEP 503 index (S3 only)")
@click.pass_context
def publish(
    ctx: click.Context,
    files: tuple[Path, ...],
    repository: str,
    token: str | None,
    repository_url: str | None,
    skip_existing: bool,
    dry_run: bool,
    attestations: bool,
    bucket: str | None,
    prefix: str,
    region: str,
    generate_index: bool,
) -> None:
    """Publish wheels to PyPI, TestPyPI, or S3.

    FILES are the wheel/sdist files to publish. If not specified,
    publishes all files in dist/.

    Examples:

        hwb publish dist/*.whl                    # Publish to PyPI

        hwb publish -r testpypi dist/*.whl        # Publish to TestPyPI

        hwb publish --dry-run dist/*.whl          # Validate without uploading

        hwb publish -r s3 --bucket my-wheels dist/*.whl  # Publish to S3
    """
    from headless_wheel_builder.publish import PublishConfig, PublishResult

    verbose = ctx.obj.get("verbose", 0)
    quiet = ctx.obj.get("quiet", False)
    json_output = ctx.obj.get("json", False)

    # Find files if not specified
    file_list = list(files)
    if not file_list:
        dist_dir = Path("dist")
        if dist_dir.exists():
            file_list = list(dist_dir.glob("*.whl")) + list(dist_dir.glob("*.tar.gz"))

    if not file_list:
        error_console.print("[red]No files to publish[/]")
        error_console.print("Specify files or run 'hwb build' first to create dist/*.whl")
        sys.exit(1)

    async def _publish() -> PublishResult:
        publish_config = PublishConfig(
            files=file_list,
            skip_existing=skip_existing,
            dry_run=dry_run,
            verbose=verbose > 0,
        )

        if repository == "s3":
            if not bucket:
                raise click.UsageError("--bucket is required for S3 publishing")

            from headless_wheel_builder.publish.s3 import S3Config, S3Publisher

            s3_config = S3Config(
                bucket=bucket,
                prefix=prefix,
                region=region,
                generate_index=generate_index,
            )
            publisher = S3Publisher(s3_config)
        else:
            from headless_wheel_builder.publish.pypi import PyPIConfig, PyPIPublisher

            pypi_config = PyPIConfig(
                repository=repository,  # type: ignore
                repository_url=repository_url,
                token=token,
                attestations=attestations,
            )
            publisher = PyPIPublisher(pypi_config)

        if not quiet and not json_output:
            console.print(f"\n[bold blue]Publishing to[/] {repository}")
            console.print(f"  Files: {len(file_list)}")
            if dry_run:
                console.print("  [yellow]DRY RUN[/]")
            console.print()

        return await publisher.publish(publish_config)

    try:
        result = run_async(_publish())

        if json_output:
            import json

            output = {
                "success": result.success,
                "published": [str(p) for p in result.files_published],
                "skipped": [str(p) for p in result.files_skipped],
                "failed": [str(p) for p in result.files_failed],
                "urls": result.urls,
                "errors": result.errors,
            }
            click.echo(json.dumps(output, indent=2))
        elif not quiet:
            if result.success:
                _print_publish_success(result)
            else:
                _print_publish_failure(result)

        sys.exit(0 if result.success else 3)

    except HWBError as e:
        if json_output:
            import json

            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            error_console.print(f"\n[bold red]Error:[/] {e}")
        sys.exit(3)

    except Exception as e:
        if json_output:
            import json

            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            error_console.print(f"\n[bold red]Unexpected error:[/] {e}")
            if verbose:
                import traceback

                error_console.print(traceback.format_exc())
        sys.exit(1)


def _print_publish_success(result) -> None:
    """Print successful publish result."""
    from rich.table import Table

    console.print()

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Status", style="green")
    table.add_column("File")
    table.add_column("URL", style="dim")

    for i, path in enumerate(result.files_published):
        url = result.urls[i] if i < len(result.urls) else ""
        table.add_row("Published", path.name, url)

    for path in result.files_skipped:
        table.add_row("[yellow]Skipped[/]", path.name, "")

    console.print(Panel(table, title="[green]Publish Successful[/]", border_style="green"))
    console.print()


def _print_publish_failure(result) -> None:
    """Print failed publish result."""
    console.print()

    for path in result.files_failed:
        console.print(f"[red]Failed:[/] {path.name}")

    for error in result.errors:
        console.print(f"  [dim]{error}[/]")

    console.print()


@cli.command("version-next")
@click.option("--path", "-p", default=".", help="Path to git repository")
@click.option("--tag-prefix", default="v", help="Tag prefix (default: v)")
@click.option("--dry-run", is_flag=True, help="Don't create tag, just show what would happen")
@click.option("--tag", is_flag=True, help="Create git tag")
@click.option("--push", is_flag=True, help="Push tag to remote")
@click.option("--changelog", is_flag=True, help="Generate changelog")
@click.pass_context
def version_next(
    ctx: click.Context,
    path: str,
    tag_prefix: str,
    dry_run: bool,
    tag: bool,
    push: bool,
    changelog: bool,
) -> None:
    """Calculate and optionally create the next version.

    Analyzes commits since the last tag using Conventional Commits
    to determine the next version bump (major, minor, or patch).

    Examples:

        hwb version-next                      # Show next version

        hwb version-next --tag               # Create git tag

        hwb version-next --tag --push        # Create and push tag

        hwb version-next --changelog         # Generate changelog
    """
    from headless_wheel_builder.version import (
        determine_bump_from_commits,
        generate_changelog,
        get_commits_since_tag,
        get_latest_tag,
        parse_commit,
        parse_version,
    )

    ctx.obj.get("verbose", 0)
    json_output = ctx.obj.get("json", False)

    async def _version_next():
        repo_path = Path(path)

        # Get latest tag
        latest_tag = await get_latest_tag(repo_path, pattern=f"{tag_prefix}*")

        if latest_tag and latest_tag.version:
            current_version = latest_tag.version
            tag_name = latest_tag.name
        else:
            current_version = parse_version("0.0.0")
            tag_name = None

        # Get commits since tag
        raw_commits = await get_commits_since_tag(repo_path, tag_name)

        if not raw_commits:
            return {
                "current": str(current_version),
                "next": None,
                "bump": None,
                "commits": 0,
                "message": "No new commits since last tag",
            }

        # Parse commits
        commits = [parse_commit(msg, hash) for hash, msg in raw_commits]

        # Determine bump type
        bump_type = determine_bump_from_commits(commits)

        if bump_type is None:
            return {
                "current": str(current_version),
                "next": None,
                "bump": None,
                "commits": len(commits),
                "message": "No version bump needed (no feat/fix commits)",
            }

        # Calculate next version
        next_version = current_version.bump(bump_type)
        next_tag = f"{tag_prefix}{next_version}"

        result = {
            "current": str(current_version),
            "next": str(next_version),
            "bump": bump_type.value,
            "commits": len(commits),
            "tag": next_tag,
        }

        # Generate changelog if requested
        if changelog:
            changelog_md = generate_changelog(
                commits=commits,
                version=next_version,
                previous_version=current_version if tag_name else None,
            )
            result["changelog"] = changelog_md

        # Create tag if requested
        if tag and not dry_run:
            from headless_wheel_builder.version.git import create_tag as git_create_tag
            from headless_wheel_builder.version.git import push_tag

            message = f"Release {next_version}"
            await git_create_tag(repo_path, next_tag, message=message)
            result["tag_created"] = True

            if push:
                await push_tag(repo_path, next_tag)
                result["tag_pushed"] = True

        return result

    try:
        result = run_async(_version_next())

        if json_output:
            import json

            click.echo(json.dumps(result, indent=2))
        else:
            console.print()
            if result.get("next"):
                console.print(f"[bold]Current version:[/] {result['current']}")
                console.print(f"[bold]Next version:[/] [green]{result['next']}[/]")
                console.print(f"[bold]Bump type:[/] {result['bump']}")
                console.print(f"[bold]Commits:[/] {result['commits']}")

                if dry_run:
                    console.print(f"\n[yellow]DRY RUN:[/] Would create tag {result['tag']}")
                elif result.get("tag_created"):
                    console.print(f"\n[green]Created tag:[/] {result['tag']}")
                    if result.get("tag_pushed"):
                        console.print("[green]Tag pushed to remote[/]")

                if result.get("changelog"):
                    console.print("\n[bold underline]Changelog[/]")
                    console.print(result["changelog"])
            else:
                console.print(f"[bold]Current version:[/] {result['current']}")
                console.print(f"[dim]{result.get('message', 'No changes')}[/]")

            console.print()

    except HWBError as e:
        if json_output:
            import json

            click.echo(json.dumps({"error": str(e)}))
        else:
            error_console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    cli()


# Register subcommand groups
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


if __name__ == "__main__":
    main()
