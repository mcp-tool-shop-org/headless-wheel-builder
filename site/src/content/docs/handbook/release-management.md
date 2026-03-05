---
title: Release Management
description: Draft releases, run approval workflows, generate changelogs, and roll back with Headless Wheel Builder.
sidebar:
  order: 2
---

Headless Wheel Builder treats releases as first-class objects with a full lifecycle: draft, submit, approve, publish — with optional rollback at any stage.

## Draft a release

```bash
hwb release create -v 1.0.0 -p my-package
```

This creates a release record with status `draft`. Nothing is published yet.

## Approval workflows

Three built-in workflow templates control who can approve a release and when:

### Simple

One approver, one step. Good for solo projects:

```bash
hwb release create -v 1.0.0 -p my-package --template simple
hwb release submit rel-abc123
hwb release approve rel-abc123 -a alice
hwb release publish rel-abc123
```

### Two-stage

Requires two independent approvals before publishing:

```bash
hwb release create -v 2.0.0 -p my-package --template two-stage
hwb release submit rel-def456
hwb release approve rel-def456 -a alice --stage 1
hwb release approve rel-def456 -a bob --stage 2
hwb release publish rel-def456
```

### Enterprise

A three-stage pipeline: QA, Security, and Release. Each stage has its own approver pool:

```bash
hwb release create -v 3.0.0 -p my-package --template enterprise
hwb release submit rel-ghi789
hwb release approve rel-ghi789 -a qa-team --stage qa
hwb release approve rel-ghi789 -a security-team --stage security
hwb release approve rel-ghi789 -a release-mgr --stage release
hwb release publish rel-ghi789
```

## Release lifecycle

Every release moves through these states:

| State       | Description                                   |
|-------------|-----------------------------------------------|
| `draft`     | Created but not yet submitted for review      |
| `submitted` | Waiting for approval                          |
| `approved`  | All required approvals received               |
| `published` | Artifacts pushed to registries                |
| `rolled-back` | Publication reversed                       |

## Rollback

If something goes wrong after publishing:

```bash
hwb release rollback rel-abc123
```

Rollback removes published artifacts from the target registry and marks the release as `rolled-back`.

## Changelog generation

Headless Wheel Builder generates changelogs from Conventional Commits:

```bash
hwb changelog generate --from v0.9.0 --to v1.0.0
```

Commit prefixes (`feat:`, `fix:`, `chore:`, `breaking:`) are grouped into sections automatically. The output is Markdown, ready for GitHub Releases or your `CHANGELOG.md`.
