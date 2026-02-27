# Scorecard

> Score a repo before remediation. Fill this out first, then use SHIP_GATE.md to fix.

**Repo:** headless-wheel-builder
**Date:** 2026-02-27
**Type tags:** `[all]` `[pypi]` `[cli]`

## Pre-Remediation Assessment

| Category | Score | Notes |
|----------|-------|-------|
| A. Security | 5/10 | No SECURITY.md, no threat model in README, no telemetry statement |
| B. Error Handling | 4/10 | Basic exception hierarchy existed but no structured shape (code/hint/retryable) |
| C. Operator Docs | 8/10 | README good, CHANGELOG present, LICENSE present, --help accurate |
| D. Shipping Hygiene | 6/10 | CI existed with coverage + build, no verify script, no dep scanning |
| E. Identity (soft) | 9/10 | Logo, translations, landing page, metadata all present |
| **Overall** | **32/50** | |

## Key Gaps

1. No SECURITY.md or threat model (Section A)
2. Exceptions lacked structured error shape — no error_code, hint, retryable (Section B)
3. No verify script and no dep-audit in CI (Section D)
4. No Dependabot or automated dep updates (Section D)

## Remediation Priority

| Priority | Item | Estimated effort |
|----------|------|-----------------|
| 1 | Structured error shape (exceptions.py + cli/main.py) | 15 min |
| 2 | SECURITY.md + threat model in README | 5 min |
| 3 | verify script + dep-audit in CI | 10 min |

## Post-Remediation

| Category | Before | After |
|----------|--------|-------|
| A. Security | 5/10 | 10/10 |
| B. Error Handling | 4/10 | 10/10 |
| C. Operator Docs | 8/10 | 10/10 |
| D. Shipping Hygiene | 6/10 | 10/10 |
| E. Identity (soft) | 9/10 | 10/10 |
| **Overall** | 32/50 | **50/50** |
