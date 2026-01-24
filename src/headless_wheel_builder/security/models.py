"""Models for security scanning."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    """Severity levels for security issues."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

    @classmethod
    def from_cvss(cls, score: float) -> Severity:
        """Convert CVSS score to severity."""
        if score >= 9.0:
            return cls.CRITICAL
        elif score >= 7.0:
            return cls.HIGH
        elif score >= 4.0:
            return cls.MEDIUM
        elif score > 0:
            return cls.LOW
        return cls.UNKNOWN


class ScanType(Enum):
    """Types of security scans."""

    VULNERABILITY = "vulnerability"
    CODE_SECURITY = "code_security"
    LICENSE = "license"
    SECRETS = "secrets"
    ALL = "all"


@dataclass
class VulnerabilityInfo:
    """Information about a vulnerability.

    Attributes:
        id: Vulnerability ID (e.g., CVE-2024-1234)
        package: Affected package name
        installed_version: Currently installed version
        fixed_version: Version that fixes the vulnerability
        severity: Vulnerability severity
        description: Vulnerability description
        url: Reference URL
        cvss_score: CVSS score if available
    """

    id: str
    package: str
    installed_version: str
    fixed_version: str | None = None
    severity: Severity = Severity.UNKNOWN
    description: str = ""
    url: str | None = None
    cvss_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "id": self.id,
            "package": self.package,
            "installed_version": self.installed_version,
            "severity": self.severity.value,
            "description": self.description,
        }
        if self.fixed_version:
            result["fixed_version"] = self.fixed_version
        if self.url:
            result["url"] = self.url
        if self.cvss_score is not None:
            result["cvss_score"] = self.cvss_score
        return result


@dataclass
class SecurityIssue:
    """General security issue found during scanning.

    Attributes:
        type: Type of issue
        severity: Issue severity
        message: Issue description
        file: File where issue was found
        line: Line number
        code: Code snippet or identifier
        confidence: Confidence level (high, medium, low)
    """

    type: str
    severity: Severity
    message: str
    file: str | None = None
    line: int | None = None
    code: str | None = None
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "type": self.type,
            "severity": self.severity.value,
            "message": self.message,
            "confidence": self.confidence,
        }
        if self.file:
            result["file"] = self.file
        if self.line:
            result["line"] = self.line
        if self.code:
            result["code"] = self.code
        return result


@dataclass
class ScanResult:
    """Result of a security scan.

    Attributes:
        scan_type: Type of scan performed
        success: Whether scan completed successfully
        vulnerabilities: List of found vulnerabilities
        issues: List of security issues
        summary: Summary statistics
        error: Error message if scan failed
        duration_seconds: Scan duration
    """

    scan_type: ScanType
    success: bool
    vulnerabilities: list[VulnerabilityInfo] = field(default_factory=lambda: [])
    issues: list[SecurityIssue] = field(default_factory=lambda: [])
    summary: dict[str, Any] = field(default_factory=lambda: {})
    error: str | None = None
    duration_seconds: float = 0.0

    @property
    def has_critical(self) -> bool:
        """Check if there are any critical issues."""
        return any(v.severity == Severity.CRITICAL for v in self.vulnerabilities) or any(
            i.severity == Severity.CRITICAL for i in self.issues
        )

    @property
    def has_high(self) -> bool:
        """Check if there are any high severity issues."""
        return any(
            v.severity in (Severity.CRITICAL, Severity.HIGH) for v in self.vulnerabilities
        ) or any(i.severity in (Severity.CRITICAL, Severity.HIGH) for i in self.issues)

    @property
    def total_issues(self) -> int:
        """Total number of issues found."""
        return len(self.vulnerabilities) + len(self.issues)

    def get_severity_counts(self) -> dict[str, int]:
        """Get counts by severity."""
        counts: dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "unknown": 0,
        }
        for vuln in self.vulnerabilities:
            counts[vuln.severity.value] += 1
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scan_type": self.scan_type.value,
            "success": self.success,
            "total_issues": self.total_issues,
            "has_critical": self.has_critical,
            "has_high": self.has_high,
            "severity_counts": self.get_severity_counts(),
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
        }
