# Headless Wheel Builder - Security Documentation

> **Purpose**: Security model, threat analysis, and mitigation strategies for secure wheel building and publishing.
> **Last Updated**: 2026-01-23

---

## 2026 Best Practices Applied

> **Sources**: [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/security-model/), [SLSA Supply Chain Security](https://slsa.dev/), [OpenSSF Scorecard](https://securityscorecards.dev/), [Sigstore](https://www.sigstore.dev/), [PEP 458 TUF](https://peps.python.org/pep-0458/), [Trail of Bits - Trusted Publishing](https://blog.trailofbits.com/2023/05/23/trusted-publishing-a-new-benchmark-for-packaging-security/)

This security model follows 2026 supply chain security best practices:

1. **SLSA Level 3 Target**: Builds are isolated, reproducible, and auditable. Build provenance is captured.

2. **Trusted Publishers Over Tokens**: OIDC-based publishing eliminates long-lived secrets. Short-lived tokens (15 min) minimize breach impact.

3. **Build Isolation Mandatory**: All builds run in isolated environments. No access to host secrets or network (configurable).

4. **Defense in Depth**: Multiple security layers - isolation, validation, attestation, signing.

5. **Principle of Least Privilege**: Build processes have minimal permissions. Network access disabled by default.

6. **Sigstore Integration Ready**: Architecture supports keyless signing with Sigstore for package attestation.

7. **Dependency Pinning**: Build dependencies are pinned and verified. Hash checking enabled.

8. **Audit Logging**: All operations are logged for forensic analysis.

---

## Threat Model

### Assets

| Asset | Value | Protection |
|-------|-------|------------|
| Source code | High | Build isolation, no exfiltration |
| Build output (wheels) | High | Validation, signing |
| PyPI credentials | Critical | Trusted Publishers, no persistence |
| Private registry credentials | High | Credential isolation, encryption |
| Build logs | Medium | Sanitization, no secrets |
| Build environment | Medium | Ephemeral, no persistence |

### Threat Actors

| Actor | Motivation | Capability |
|-------|------------|------------|
| Malicious package author | Supply chain attack | Arbitrary code in setup.py |
| Compromised CI | Credential theft | Access to environment |
| Network attacker | MITM, data theft | Network interception |
| Malicious dependency | Backdoor installation | Code execution during build |
| Insider threat | Data exfiltration | Legitimate access |

### Attack Vectors

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ATTACK SURFACE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   SOURCE     │    │    BUILD     │    │   PUBLISH    │              │
│  │   INPUT      │    │   PROCESS    │    │   OUTPUT     │              │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│         │                   │                   │                       │
│  ┌──────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐              │
│  │ • Malicious  │    │ • Arbitrary  │    │ • Credential │              │
│  │   setup.py   │    │   code exec  │    │   theft      │              │
│  │ • Dependency │    │ • Network    │    │ • Package    │              │
│  │   confusion  │    │   exfil      │    │   tampering  │              │
│  │ • Git repo   │    │ • Env var    │    │ • Typosquat  │              │
│  │   injection  │    │   leakage    │    │              │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Security Controls

### 1. Build Isolation

**Control**: All builds execute in isolated environments with no access to host secrets.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HOST SYSTEM                                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    ISOLATION BOUNDARY                          │ │
│  │  ┌─────────────────────────────────────────────────────────┐  │ │
│  │  │               BUILD ENVIRONMENT                          │  │ │
│  │  │                                                          │  │ │
│  │  │  Allowed:                    Blocked:                    │  │ │
│  │  │  ✓ Source files (read-only) ✗ Host filesystem            │  │ │
│  │  │  ✓ Build dependencies       ✗ Environment variables      │  │ │
│  │  │  ✓ Output directory (write) ✗ Network (configurable)     │  │ │
│  │  │  ✓ Temp space               ✗ Other processes            │  │ │
│  │  │                             ✗ Credentials/secrets        │  │ │
│  │  └─────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Protected:                                                          │
│  • ~/.pypirc                                                         │
│  • Environment variables (PYPI_TOKEN, etc.)                          │
│  • SSH keys                                                          │
│  • Git credentials                                                   │
│  • AWS/GCP/Azure credentials                                         │
└─────────────────────────────────────────────────────────────────────┘
```

**Implementation (venv)**:
```python
def create_isolated_env(source_path: Path) -> dict[str, str]:
    """Create isolated environment variables for build."""
    # Start with minimal environment
    env = {
        "PATH": get_minimal_path(),
        "HOME": str(temp_home),  # Isolated home directory
        "TMPDIR": str(temp_dir),
        "LANG": "C.UTF-8",
    }

    # Explicitly exclude sensitive variables
    excluded = {
        "PYPI_TOKEN", "TEST_PYPI_TOKEN", "TWINE_PASSWORD",
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
        "GITHUB_TOKEN", "GITLAB_TOKEN",
        "SSH_AUTH_SOCK", "SSH_AGENT_PID",
    }

    # Only include safe, necessary variables
    safe_vars = {"PYTHONPATH", "PYTHONHASHSEED"}
    for var in safe_vars:
        if var in os.environ:
            env[var] = os.environ[var]

    return env
```

**Implementation (Docker)**:
```python
def get_docker_args(source_path: Path, output_path: Path) -> list[str]:
    """Get Docker arguments with security restrictions."""
    return [
        "docker", "run",
        "--rm",
        "--network=none",           # No network access
        "--read-only",              # Read-only root filesystem
        "--tmpfs", "/tmp:size=1G",  # Writable temp
        "--cap-drop=ALL",           # Drop all capabilities
        "--security-opt=no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}",  # Non-root
        "-v", f"{source_path}:/src:ro",            # Source read-only
        "-v", f"{output_path}:/output:rw",         # Output writable
        "-e", "HOME=/tmp/home",
    ]
```

### 2. Trusted Publishers (OIDC)

**Control**: Use short-lived OIDC tokens instead of long-lived API keys.

**How it works**:
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│   GitHub     │     │    HWB       │     │    PyPI      │     │  OIDC    │
│   Actions    │     │              │     │              │     │ Provider │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘     └────┬─────┘
       │                    │                    │                   │
       │ 1. CI triggered    │                    │                   │
       │───────────────────►│                    │                   │
       │                    │                    │                   │
       │ 2. Request OIDC    │                    │                   │
       │    token           │                    │                   │
       │────────────────────────────────────────────────────────────►│
       │                    │                    │                   │
       │◄────────────────────────────────────────────────────────────│
       │ 3. ID token        │                    │                   │
       │    (signed JWT)    │                    │                   │
       │                    │                    │                   │
       │ 4. Exchange token  │                    │                   │
       │───────────────────►│                    │                   │
       │                    │ 5. Token + claims  │                   │
       │                    │───────────────────►│                   │
       │                    │                    │                   │
       │                    │                    │ 6. Verify token  │
       │                    │                    │──────────────────►│
       │                    │                    │                   │
       │                    │                    │◄──────────────────│
       │                    │                    │    Valid          │
       │                    │                    │                   │
       │                    │ 7. PyPI API token  │                   │
       │                    │    (15 min TTL)    │                   │
       │                    │◄───────────────────│                   │
       │                    │                    │                   │
       │                    │ 8. Upload wheel    │                   │
       │                    │───────────────────►│                   │
       │                    │                    │                   │
```

**Security Benefits**:
- No secrets to store or rotate
- Tokens expire in 15 minutes
- Audit trail in CI provider
- Repository/workflow verified cryptographically

**Configuration**:
```yaml
# In PyPI project settings, configure Trusted Publisher:
# - GitHub repository: user/repo
# - Workflow name: release.yml
# - Environment: release (optional)

# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']

permissions:
  id-token: write  # Required for Trusted Publishing

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: release  # Optional: adds approval requirement

    steps:
      - uses: actions/checkout@v4

      - name: Build and publish
        run: |
          hwb build
          hwb publish --trusted-publisher
```

### 3. Credential Handling

**Control**: Credentials are never stored, logged, or cached.

**Rules**:
1. API tokens read from environment variables only
2. Tokens passed to subprocesses via stdin, not command line
3. Build logs sanitized to remove any token patterns
4. No credential caching in any file

**Implementation**:
```python
class CredentialHandler:
    """Secure credential handling."""

    # Patterns that look like secrets
    SECRET_PATTERNS = [
        r"pypi-[A-Za-z0-9_-]{32,}",           # PyPI tokens
        r"ghp_[A-Za-z0-9]{36,}",              # GitHub tokens
        r"glpat-[A-Za-z0-9-]{20,}",           # GitLab tokens
        r"AKIA[A-Z0-9]{16}",                   # AWS access keys
        r"[A-Za-z0-9+/]{40,}={0,2}",          # Base64 secrets
    ]

    @staticmethod
    def get_token(env_var: str) -> str | None:
        """Get token from environment (never from file)."""
        return os.environ.get(env_var)

    @staticmethod
    def sanitize_log(log: str) -> str:
        """Remove potential secrets from log output."""
        sanitized = log
        for pattern in CredentialHandler.SECRET_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized)
        return sanitized

    @staticmethod
    def pass_token_securely(token: str, process: subprocess.Popen) -> None:
        """Pass token via stdin, not command line."""
        process.stdin.write(token.encode())
        process.stdin.close()
```

### 4. Source Validation

**Control**: Validate source before execution.

**Checks**:
```python
class SourceValidator:
    """Validate source before building."""

    # Suspicious patterns in setup.py
    DANGEROUS_PATTERNS = [
        r"os\.system\(",
        r"subprocess\.(run|Popen|call)\(",
        r"eval\(",
        r"exec\(",
        r"__import__\(",
        r"urllib\.request\.urlopen\(",
        r"requests\.(get|post)\(",
        r"socket\.",
    ]

    # Suspicious filenames
    SUSPICIOUS_FILES = [
        ".env",
        ".pypirc",
        "credentials",
        "secrets",
    ]

    async def validate(self, source_path: Path) -> ValidationResult:
        """Validate source for security issues."""
        issues = []

        # Check setup.py for dangerous patterns
        setup_py = source_path / "setup.py"
        if setup_py.exists():
            content = setup_py.read_text()
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, content):
                    issues.append(SecurityIssue(
                        severity="warning",
                        message=f"setup.py contains potentially dangerous pattern: {pattern}",
                        file="setup.py"
                    ))

        # Check for suspicious files
        for file in self.SUSPICIOUS_FILES:
            if (source_path / file).exists():
                issues.append(SecurityIssue(
                    severity="warning",
                    message=f"Source contains suspicious file: {file}",
                    file=file
                ))

        # Check pyproject.toml for network-fetching build deps
        pyproject = source_path / "pyproject.toml"
        if pyproject.exists():
            issues.extend(await self._check_build_deps(pyproject))

        return ValidationResult(issues=issues, passed=not any(
            i.severity == "error" for i in issues
        ))
```

### 5. Wheel Validation

**Control**: Validate built wheels before publishing.

**Checks**:
```python
class WheelValidator:
    """Validate wheel structure and content."""

    async def validate(self, wheel_path: Path) -> ValidationResult:
        """Validate wheel for security and correctness."""
        issues = []

        with zipfile.ZipFile(wheel_path) as whl:
            # Check for absolute paths
            for name in whl.namelist():
                if name.startswith("/") or ".." in name:
                    issues.append(SecurityIssue(
                        severity="error",
                        message=f"Wheel contains unsafe path: {name}"
                    ))

            # Check for executable files outside expected locations
            for info in whl.infolist():
                if info.external_attr >> 16 & 0o111:  # Executable
                    if not self._is_expected_executable(info.filename):
                        issues.append(SecurityIssue(
                            severity="warning",
                            message=f"Unexpected executable: {info.filename}"
                        ))

            # Verify RECORD file
            record_valid = await self._verify_record(whl)
            if not record_valid:
                issues.append(SecurityIssue(
                    severity="error",
                    message="RECORD file has invalid hashes"
                ))

            # Check for data files in wrong location
            issues.extend(await self._check_data_files(whl))

        return ValidationResult(issues=issues)
```

### 6. Network Isolation

**Control**: Network access disabled by default during builds.

**Rationale**: Prevents exfiltration of secrets and ensures reproducibility.

**Configuration**:
```toml
[tool.hwb.security]
# Network isolation (default: true)
network-isolation = true

# If network needed, whitelist specific hosts
network-allowed-hosts = [
    "pypi.org",
    "files.pythonhosted.org",
]
```

**Implementation**:
```python
# Docker: --network=none
# venv: Use unshare on Linux, or firewall rules

def apply_network_isolation():
    """Apply network isolation to build process."""
    if sys.platform == "linux":
        # Use network namespace
        os.unshare(os.CLONE_NEWNET)
        # Bring up loopback
        subprocess.run(["ip", "link", "set", "lo", "up"])
    elif sys.platform == "darwin":
        # macOS: Use sandbox-exec
        pass  # Configured in sandbox profile
    elif sys.platform == "win32":
        # Windows: Use Windows Sandbox or firewall
        pass
```

### 7. Supply Chain Security

**Control**: Verify integrity of build dependencies.

**Implementation**:
```python
class DependencyVerifier:
    """Verify build dependencies."""

    async def install_verified(
        self,
        requirements: list[str],
        env: BuildEnvironment,
        hashes_file: Path | None = None
    ) -> None:
        """Install dependencies with hash verification."""
        # Generate requirements with hashes
        if hashes_file and hashes_file.exists():
            # Use pre-computed hashes
            cmd = [
                "pip", "install",
                "--require-hashes",
                "-r", str(hashes_file)
            ]
        else:
            # Fetch and verify hashes from PyPI
            requirements_with_hashes = await self._resolve_with_hashes(requirements)
            cmd = [
                "pip", "install",
                "--require-hashes",
                *requirements_with_hashes
            ]

        await self._run_in_env(cmd, env)

    async def _resolve_with_hashes(self, requirements: list[str]) -> list[str]:
        """Resolve requirements and fetch hashes from PyPI."""
        result = []
        for req in requirements:
            # Query PyPI JSON API for hashes
            pkg_info = await self._fetch_pypi_info(req)
            hash_value = pkg_info["digests"]["sha256"]
            result.append(f"{req} --hash=sha256:{hash_value}")
        return result
```

---

## Audit Logging

All security-relevant operations are logged.

**Log Format**:
```json
{
  "timestamp": "2026-01-23T12:00:00Z",
  "event": "build.started",
  "source": "https://github.com/user/repo",
  "isolation": "docker",
  "image": "quay.io/pypa/manylinux_2_28_x86_64",
  "user": "ci",
  "environment": {
    "ci_provider": "github_actions",
    "workflow": "release.yml",
    "run_id": "12345"
  }
}

{
  "timestamp": "2026-01-23T12:01:00Z",
  "event": "publish.completed",
  "package": "mypackage",
  "version": "1.0.0",
  "registry": "pypi.org",
  "authentication": "trusted_publisher",
  "oidc_issuer": "https://token.actions.githubusercontent.com"
}
```

**Log Locations**:
```
~/.hwb/logs/
├── build-2026-01-23.log
├── publish-2026-01-23.log
└── audit-2026-01-23.json
```

---

## Security Checklist

### For Package Authors

- [ ] Use Trusted Publishers instead of API tokens
- [ ] Pin build dependencies with hashes
- [ ] Enable 2FA on PyPI account
- [ ] Use `pyproject.toml` instead of `setup.py` (no code execution)
- [ ] Review `SECURITY.md` in your package
- [ ] Sign releases with Sigstore (when available)

### For CI/CD

- [ ] Use dedicated CI environment for publishing
- [ ] Enable branch protection on release branch
- [ ] Require approval for release workflow
- [ ] Pin action versions with SHA
- [ ] Use `permissions: id-token: write` (minimum required)
- [ ] Don't store PyPI tokens as secrets

### For Organizations

- [ ] Use private package registry with access controls
- [ ] Implement package scanning in CI
- [ ] Monitor for typosquatting
- [ ] Set up Dependabot/Renovate for updates
- [ ] Conduct regular security audits

---

## Incident Response

### If API Token is Compromised

1. **Immediately revoke** the token on PyPI
2. Check PyPI for unauthorized releases
3. Yank any malicious versions
4. Rotate all other secrets in the same environment
5. Review audit logs
6. Notify users if malicious package was published
7. **Migrate to Trusted Publishers**

### If Package is Compromised

1. Yank the compromised version(s)
2. Publish patched version with incremented version
3. File security advisory on GitHub
4. Notify downstream users
5. Report to PyPI security team
6. Conduct post-mortem

---

## Future Security Enhancements

### Sigstore Integration
- Keyless signing with Sigstore
- Transparency log for audit
- Automated verification

### SLSA Provenance
- Build provenance attestation
- SLSA Level 3 compliance
- Reproducible builds

### SBOMs
- Generate Software Bill of Materials
- CycloneDX/SPDX format
- Dependency vulnerability tracking

---

## Changelog

| Date | Changes |
|------|---------|
| 2026-01-23 | Initial security documentation |
