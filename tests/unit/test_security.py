"""Tests for security scanning."""

from __future__ import annotations

from headless_wheel_builder.security.models import (
    ScanResult,
    ScanType,
    SecurityIssue,
    Severity,
    VulnerabilityInfo,
)
from headless_wheel_builder.security.scanner import ScannerConfig, SecurityScanner


class TestSeverity:
    """Tests for Severity enum."""

    def test_all_levels_exist(self) -> None:
        """Test all expected severity levels exist."""
        levels = [s.value for s in Severity]
        assert "critical" in levels
        assert "high" in levels
        assert "medium" in levels
        assert "low" in levels
        assert "unknown" in levels

    def test_from_cvss_critical(self) -> None:
        """Test CVSS to severity conversion for critical."""
        assert Severity.from_cvss(9.0) == Severity.CRITICAL
        assert Severity.from_cvss(10.0) == Severity.CRITICAL

    def test_from_cvss_high(self) -> None:
        """Test CVSS to severity conversion for high."""
        assert Severity.from_cvss(7.0) == Severity.HIGH
        assert Severity.from_cvss(8.9) == Severity.HIGH

    def test_from_cvss_medium(self) -> None:
        """Test CVSS to severity conversion for medium."""
        assert Severity.from_cvss(4.0) == Severity.MEDIUM
        assert Severity.from_cvss(6.9) == Severity.MEDIUM

    def test_from_cvss_low(self) -> None:
        """Test CVSS to severity conversion for low."""
        assert Severity.from_cvss(0.1) == Severity.LOW
        assert Severity.from_cvss(3.9) == Severity.LOW

    def test_from_cvss_unknown(self) -> None:
        """Test CVSS to severity conversion for zero."""
        assert Severity.from_cvss(0) == Severity.UNKNOWN


class TestScanType:
    """Tests for ScanType enum."""

    def test_all_types_exist(self) -> None:
        """Test all expected scan types exist."""
        types = [t.value for t in ScanType]
        assert "vulnerability" in types
        assert "code_security" in types
        assert "license" in types
        assert "secrets" in types
        assert "all" in types


class TestVulnerabilityInfo:
    """Tests for VulnerabilityInfo model."""

    def test_minimal_vuln(self) -> None:
        """Test creating minimal vulnerability."""
        vuln = VulnerabilityInfo(
            id="CVE-2024-1234",
            package="requests",
            installed_version="2.25.0",
        )
        assert vuln.id == "CVE-2024-1234"
        assert vuln.package == "requests"
        assert vuln.fixed_version is None
        assert vuln.severity == Severity.UNKNOWN

    def test_full_vuln(self) -> None:
        """Test creating full vulnerability."""
        vuln = VulnerabilityInfo(
            id="CVE-2024-1234",
            package="requests",
            installed_version="2.25.0",
            fixed_version="2.26.0",
            severity=Severity.HIGH,
            description="Security issue in requests",
            url="https://nvd.nist.gov/vuln/detail/CVE-2024-1234",
            cvss_score=7.5,
        )
        assert vuln.fixed_version == "2.26.0"
        assert vuln.severity == Severity.HIGH
        assert vuln.cvss_score == 7.5

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        vuln = VulnerabilityInfo(
            id="CVE-2024-1234",
            package="requests",
            installed_version="2.25.0",
            severity=Severity.CRITICAL,
        )
        data = vuln.to_dict()
        assert data["id"] == "CVE-2024-1234"
        assert data["package"] == "requests"
        assert data["severity"] == "critical"


class TestSecurityIssue:
    """Tests for SecurityIssue model."""

    def test_minimal_issue(self) -> None:
        """Test creating minimal issue."""
        issue = SecurityIssue(
            type="B101",
            severity=Severity.LOW,
            message="Use of assert detected",
        )
        assert issue.type == "B101"
        assert issue.severity == Severity.LOW
        assert issue.file is None
        assert issue.line is None

    def test_full_issue(self) -> None:
        """Test creating full issue."""
        issue = SecurityIssue(
            type="B101",
            severity=Severity.MEDIUM,
            message="Use of assert detected",
            file="src/mymodule.py",
            line=42,
            code="assert user.is_admin",
            confidence="high",
        )
        assert issue.file == "src/mymodule.py"
        assert issue.line == 42
        assert issue.confidence == "high"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        issue = SecurityIssue(
            type="B101",
            severity=Severity.MEDIUM,
            message="Security issue",
        )
        data = issue.to_dict()
        assert data["type"] == "B101"
        assert data["severity"] == "medium"


class TestScanResult:
    """Tests for ScanResult model."""

    def test_empty_result(self) -> None:
        """Test empty scan result."""
        result = ScanResult(
            scan_type=ScanType.VULNERABILITY,
            success=True,
        )
        assert result.success is True
        assert len(result.vulnerabilities) == 0
        assert len(result.issues) == 0
        assert result.total_issues == 0

    def test_has_critical_vulnerability(self) -> None:
        """Test has_critical with critical vulnerability."""
        result = ScanResult(
            scan_type=ScanType.VULNERABILITY,
            success=True,
            vulnerabilities=[
                VulnerabilityInfo(
                    id="CVE-1",
                    package="pkg",
                    installed_version="1.0",
                    severity=Severity.CRITICAL,
                ),
            ],
        )
        assert result.has_critical is True

    def test_has_critical_issue(self) -> None:
        """Test has_critical with critical issue."""
        result = ScanResult(
            scan_type=ScanType.CODE_SECURITY,
            success=True,
            issues=[
                SecurityIssue(
                    type="B102",
                    severity=Severity.CRITICAL,
                    message="Critical issue",
                ),
            ],
        )
        assert result.has_critical is True

    def test_has_high(self) -> None:
        """Test has_high property."""
        result = ScanResult(
            scan_type=ScanType.VULNERABILITY,
            success=True,
            vulnerabilities=[
                VulnerabilityInfo(
                    id="CVE-1",
                    package="pkg",
                    installed_version="1.0",
                    severity=Severity.HIGH,
                ),
            ],
        )
        assert result.has_high is True

    def test_total_issues(self) -> None:
        """Test total_issues count."""
        result = ScanResult(
            scan_type=ScanType.ALL,
            success=True,
            vulnerabilities=[
                VulnerabilityInfo(id="CVE-1", package="pkg", installed_version="1.0"),
                VulnerabilityInfo(id="CVE-2", package="pkg", installed_version="1.0"),
            ],
            issues=[
                SecurityIssue(type="B101", severity=Severity.LOW, message="Issue"),
            ],
        )
        assert result.total_issues == 3

    def test_get_severity_counts(self) -> None:
        """Test severity count calculation."""
        result = ScanResult(
            scan_type=ScanType.ALL,
            success=True,
            vulnerabilities=[
                VulnerabilityInfo(
                    id="CVE-1",
                    package="pkg",
                    installed_version="1.0",
                    severity=Severity.CRITICAL,
                ),
                VulnerabilityInfo(
                    id="CVE-2",
                    package="pkg",
                    installed_version="1.0",
                    severity=Severity.HIGH,
                ),
                VulnerabilityInfo(
                    id="CVE-3",
                    package="pkg",
                    installed_version="1.0",
                    severity=Severity.HIGH,
                ),
            ],
            issues=[
                SecurityIssue(type="B101", severity=Severity.LOW, message="Issue"),
            ],
        )
        counts = result.get_severity_counts()
        assert counts["critical"] == 1
        assert counts["high"] == 2
        assert counts["low"] == 1

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = ScanResult(
            scan_type=ScanType.VULNERABILITY,
            success=True,
            duration_seconds=5.5,
        )
        data = result.to_dict()
        assert data["scan_type"] == "vulnerability"
        assert data["success"] is True
        assert data["duration_seconds"] == 5.5


class TestScannerConfig:
    """Tests for ScannerConfig model."""

    def test_defaults(self) -> None:
        """Test default configuration."""
        config = ScannerConfig()
        assert config.project_path == "."
        assert config.fail_on_critical is True
        assert config.fail_on_high is False
        assert config.timeout == 300
        assert config.ignore_ids == []

    def test_custom_values(self) -> None:
        """Test custom configuration."""
        config = ScannerConfig(
            project_path="/path/to/project",
            fail_on_critical=False,
            fail_on_high=True,
            timeout=60,
            ignore_ids=["CVE-2024-1234"],
        )
        assert config.project_path == "/path/to/project"
        assert config.fail_on_critical is False
        assert config.fail_on_high is True
        assert config.timeout == 60
        assert "CVE-2024-1234" in config.ignore_ids


class TestSecurityScanner:
    """Tests for SecurityScanner."""

    def test_init_default(self) -> None:
        """Test scanner with default config."""
        scanner = SecurityScanner()
        assert scanner.config.project_path == "."

    def test_init_custom_config(self) -> None:
        """Test scanner with custom config."""
        config = ScannerConfig(project_path="/custom/path")
        scanner = SecurityScanner(config)
        assert scanner.config.project_path == "/custom/path"

    def test_should_fail_critical(self) -> None:
        """Test should_fail with critical issues."""
        config = ScannerConfig(fail_on_critical=True)
        scanner = SecurityScanner(config)

        results = [
            ScanResult(
                scan_type=ScanType.VULNERABILITY,
                success=True,
                vulnerabilities=[
                    VulnerabilityInfo(
                        id="CVE-1",
                        package="pkg",
                        installed_version="1.0",
                        severity=Severity.CRITICAL,
                    ),
                ],
            ),
        ]
        assert scanner.should_fail(results) is True

    def test_should_fail_high(self) -> None:
        """Test should_fail with high issues when configured."""
        config = ScannerConfig(fail_on_high=True)
        scanner = SecurityScanner(config)

        results = [
            ScanResult(
                scan_type=ScanType.VULNERABILITY,
                success=True,
                vulnerabilities=[
                    VulnerabilityInfo(
                        id="CVE-1",
                        package="pkg",
                        installed_version="1.0",
                        severity=Severity.HIGH,
                    ),
                ],
            ),
        ]
        assert scanner.should_fail(results) is True

    def test_should_not_fail_low(self) -> None:
        """Test should_fail returns False for low issues."""
        config = ScannerConfig()
        scanner = SecurityScanner(config)

        results = [
            ScanResult(
                scan_type=ScanType.VULNERABILITY,
                success=True,
                vulnerabilities=[
                    VulnerabilityInfo(
                        id="CVE-1",
                        package="pkg",
                        installed_version="1.0",
                        severity=Severity.LOW,
                    ),
                ],
            ),
        ]
        assert scanner.should_fail(results) is False

    def test_parse_pip_audit_output(self) -> None:
        """Test parsing pip-audit JSON output."""
        scanner = SecurityScanner()
        data = [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "PYSEC-2023-123",
                        "fix_versions": ["2.26.0"],
                        "description": "Security issue",
                    },
                ],
            },
        ]
        vulns = scanner._parse_pip_audit_output(data)
        assert len(vulns) == 1
        assert vulns[0].id == "PYSEC-2023-123"
        assert vulns[0].package == "requests"
        assert vulns[0].fixed_version == "2.26.0"

    def test_parse_bandit_output(self) -> None:
        """Test parsing bandit JSON output."""
        scanner = SecurityScanner()
        data = {
            "results": [
                {
                    "test_id": "B101",
                    "issue_severity": "MEDIUM",
                    "issue_confidence": "HIGH",
                    "issue_text": "Use of assert detected",
                    "filename": "test.py",
                    "line_number": 10,
                },
            ],
        }
        issues = scanner._parse_bandit_output(data)
        assert len(issues) == 1
        assert issues[0].type == "B101"
        assert issues[0].severity == Severity.MEDIUM
        assert issues[0].file == "test.py"
        assert issues[0].line == 10
