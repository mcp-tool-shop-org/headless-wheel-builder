---
title: Security
description: Vulnerability scanning, SBOM generation, license compliance, and dependency graph analysis.
sidebar:
  order: 5
---

Headless Wheel Builder includes built-in security tooling so you do not need a separate scanner in your pipeline.

## Security scanning

### Vulnerability audit

Scan your project for known vulnerabilities:

```bash
hwb security audit ./my-project
```

The audit checks your dependency tree against public advisory databases and reports findings with severity levels.

### SBOM generation

Produce a Software Bill of Materials in CycloneDX format:

```bash
hwb security sbom ./my-project --format cyclonedx
hwb security sbom ./my-project --format cyclonedx --output sbom.json
```

SBOMs are increasingly required for compliance and supply chain security.

### License compliance

Check that all dependencies use approved licenses:

```bash
hwb security licenses ./my-project --allow MIT,Apache-2.0,BSD-3-Clause
```

Fails with a non-zero exit code if any dependency uses a license outside the allow list.

## Dependency graph analysis

### Tree visualization

See your full dependency tree:

```bash
hwb deps tree ./my-project
```

### License overview

List every dependency and its license:

```bash
hwb deps licenses numpy
hwb deps licenses ./my-project --check
```

### Cycle detection

Find circular dependencies that can cause import errors:

```bash
hwb deps cycles ./my-project
```

### Build order

Compute a topological build order for a set of interdependent packages:

```bash
hwb deps build-order ./packages/
```

## Python API

Use the security tools programmatically:

```python
from headless_wheel_builder.security import audit, generate_sbom
from headless_wheel_builder.deps import dependency_tree, check_licenses

# run a vulnerability audit
findings = await audit(source="./my-project")
for f in findings:
    print(f"{f.severity}: {f.package} {f.version} - {f.advisory}")

# generate an SBOM
sbom = await generate_sbom(source="./my-project", format="cyclonedx")
sbom.write("sbom.json")

# inspect the dependency tree
tree = await dependency_tree(source="./my-project")
print(tree.render())

# check license compliance
result = await check_licenses(
    source="./my-project",
    allowed=["MIT", "Apache-2.0", "BSD-3-Clause"],
)
if not result.compliant:
    for violation in result.violations:
        print(f"{violation.package}: {violation.license}")
```

## Integrating with CI

A typical CI step combines audit and SBOM generation:

```yaml
- name: Security checks
  run: |
    hwb security audit . --fail-on high
    hwb security sbom . --format cyclonedx --output sbom.json
    hwb security licenses . --allow MIT,Apache-2.0,BSD-3-Clause
```

The `--fail-on` flag controls the minimum severity that causes a non-zero exit: `low`, `medium`, `high`, or `critical`.
