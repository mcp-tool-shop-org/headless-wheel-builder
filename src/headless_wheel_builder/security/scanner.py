"""Security scanner for Python packages."""

from __future__ import annotations

import asyncio
import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from headless_wheel_builder.security.models import (
    ScanResult,
    ScanType,
    SecurityIssue,
    Severity,
    VulnerabilityInfo,
)


@dataclass
class ScannerConfig:
    """Configuration for security scanning.

    Attributes:
        project_path: Path to project to scan
        fail_on_critical: Fail if critical issues found
        fail_on_high: Fail if high severity issues found
        include_dev_deps: Include development dependencies
        timeout: Scan timeout in seconds
        ignore_ids: Vulnerability IDs to ignore
    """

    project_path: str | Path = "."
    fail_on_critical: bool = True
    fail_on_high: bool = False
    include_dev_deps: bool = False
    timeout: int = 300
    ignore_ids: list[str] = field(default_factory=lambda: [])


class SecurityScanner:
    """Scanner for security vulnerabilities and issues.

    Integrates with pip-audit, safety, and bandit.
    """

    def __init__(self, config: ScannerConfig | None = None) -> None:
        """Initialize scanner.

        Args:
            config: Scanner configuration
        """
        self.config = config or ScannerConfig()

    async def scan_all(self) -> list[ScanResult]:
        """Run all security scans.

        Returns:
            List of scan results
        """
        results: list[ScanResult] = []

        # Run scans in parallel
        vuln_task = asyncio.create_task(self.scan_vulnerabilities())
        code_task = asyncio.create_task(self.scan_code_security())

        vuln_result = await vuln_task
        code_result = await code_task

        results.append(vuln_result)
        results.append(code_result)

        return results

    async def scan_vulnerabilities(self) -> ScanResult:
        """Scan for dependency vulnerabilities using pip-audit.

        Returns:
            Scan result with vulnerabilities
        """
        start_time = time.time()

        # Check if pip-audit is available
        pip_audit = shutil.which("pip-audit")
        if not pip_audit:
            return ScanResult(
                scan_type=ScanType.VULNERABILITY,
                success=False,
                error="pip-audit not found. Install with: pip install pip-audit",
                duration_seconds=time.time() - start_time,
            )

        try:
            # Run pip-audit
            args = ["pip-audit", "--format", "json"]

            project_path = Path(self.config.project_path)
            requirements = project_path / "requirements.txt"
            pyproject = project_path / "pyproject.toml"

            if requirements.exists():
                args.extend(["--requirement", str(requirements)])
            elif pyproject.exists():
                args.extend(["--local"])

            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project_path),
            )

            try:
                stdout, _stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ScanResult(
                    scan_type=ScanType.VULNERABILITY,
                    success=False,
                    error=f"Scan timed out after {self.config.timeout}s",
                    duration_seconds=time.time() - start_time,
                )

            vulnerabilities: list[VulnerabilityInfo] = []

            if stdout:
                try:
                    data = json.loads(stdout.decode())
                    vulnerabilities = self._parse_pip_audit_output(data)
                except json.JSONDecodeError:
                    pass

            # Filter ignored vulnerabilities
            if self.config.ignore_ids:
                vulnerabilities = [v for v in vulnerabilities if v.id not in self.config.ignore_ids]

            return ScanResult(
                scan_type=ScanType.VULNERABILITY,
                success=True,
                vulnerabilities=vulnerabilities,
                summary={
                    "total": len(vulnerabilities),
                    "by_severity": self._count_by_severity(vulnerabilities),
                },
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            return ScanResult(
                scan_type=ScanType.VULNERABILITY,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _parse_pip_audit_output(self, data: list[dict[str, Any]]) -> list[VulnerabilityInfo]:
        """Parse pip-audit JSON output."""
        vulnerabilities: list[VulnerabilityInfo] = []

        for item in data:
            package = item.get("name", "")
            version = item.get("version", "")
            vulns = item.get("vulns", [])

            for vuln in vulns:
                vuln_id = vuln.get("id", "UNKNOWN")
                fix_versions = vuln.get("fix_versions", [])
                fixed = fix_versions[0] if fix_versions else None

                # Parse aliases for severity (could be enhanced to check for CVE scores)
                _aliases = vuln.get("aliases", [])
                severity = Severity.UNKNOWN

                vulnerabilities.append(
                    VulnerabilityInfo(
                        id=vuln_id,
                        package=package,
                        installed_version=version,
                        fixed_version=fixed,
                        severity=severity,
                        description=vuln.get("description", ""),
                        url=vuln.get("url"),
                    )
                )

        return vulnerabilities

    def _count_by_severity(self, vulnerabilities: list[VulnerabilityInfo]) -> dict[str, int]:
        """Count vulnerabilities by severity."""
        counts: dict[str, int] = {}
        for vuln in vulnerabilities:
            key = vuln.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    async def scan_code_security(self) -> ScanResult:
        """Scan code for security issues using bandit.

        Returns:
            Scan result with security issues
        """
        start_time = time.time()

        # Check if bandit is available
        bandit = shutil.which("bandit")
        if not bandit:
            return ScanResult(
                scan_type=ScanType.CODE_SECURITY,
                success=False,
                error="bandit not found. Install with: pip install bandit",
                duration_seconds=time.time() - start_time,
            )

        try:
            project_path = Path(self.config.project_path)

            # Find Python files
            src_dir = project_path / "src"
            target = str(src_dir) if src_dir.exists() else str(project_path)

            args = [
                "bandit",
                "-r",
                target,
                "-f",
                "json",
                "-q",
            ]

            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, _stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ScanResult(
                    scan_type=ScanType.CODE_SECURITY,
                    success=False,
                    error=f"Scan timed out after {self.config.timeout}s",
                    duration_seconds=time.time() - start_time,
                )

            issues: list[SecurityIssue] = []

            if stdout:
                try:
                    data = json.loads(stdout.decode())
                    issues = self._parse_bandit_output(data)
                except json.JSONDecodeError:
                    pass

            return ScanResult(
                scan_type=ScanType.CODE_SECURITY,
                success=True,
                issues=issues,
                summary={
                    "total": len(issues),
                    "by_severity": self._count_issues_by_severity(issues),
                },
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            return ScanResult(
                scan_type=ScanType.CODE_SECURITY,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _parse_bandit_output(self, data: dict[str, Any]) -> list[SecurityIssue]:
        """Parse bandit JSON output."""
        issues: list[SecurityIssue] = []

        results = data.get("results", [])
        for result in results:
            severity_str = result.get("issue_severity", "MEDIUM").lower()
            severity = (
                Severity(severity_str)
                if severity_str in [s.value for s in Severity]
                else Severity.UNKNOWN
            )

            issues.append(
                SecurityIssue(
                    type=result.get("test_id", "UNKNOWN"),
                    severity=severity,
                    message=result.get("issue_text", ""),
                    file=result.get("filename"),
                    line=result.get("line_number"),
                    code=result.get("code"),
                    confidence=result.get("issue_confidence", "MEDIUM").lower(),
                )
            )

        return issues

    def _count_issues_by_severity(self, issues: list[SecurityIssue]) -> dict[str, int]:
        """Count issues by severity."""
        counts: dict[str, int] = {}
        for issue in issues:
            key = issue.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def should_fail(self, results: list[ScanResult]) -> bool:
        """Check if build should fail based on results.

        Args:
            results: List of scan results

        Returns:
            True if build should fail
        """
        for result in results:
            if self.config.fail_on_critical and result.has_critical:
                return True
            if self.config.fail_on_high and result.has_high:
                return True
        return False
