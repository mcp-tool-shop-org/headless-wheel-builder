---
title: DevOps
description: Pipeline orchestration, GitHub Actions generation, multi-repo operations, notifications, and metrics.
sidebar:
  order: 4
---

Headless Wheel Builder is designed to run unattended. Everything on this page works identically on a developer laptop and inside CI.

## Pipeline orchestration

Define multi-stage pipelines in YAML:

```yaml
# my-pipeline.yml
stages:
  - name: build
    command: hwb build . --python 3.11 --python 3.12
  - name: test
    command: pytest tests/
  - name: publish
    command: hwb publish dist/*.whl --to pypi
    depends_on: [build, test]
```

Run the full pipeline or pick individual stages:

```bash
hwb pipeline run my-pipeline.yml
hwb pipeline run my-pipeline.yml --stage build
```

## GitHub Actions generator

Generate a ready-to-commit CI workflow from your project:

```bash
hwb actions generate ./my-project --output .github/workflows/ci.yml
```

The generator reads your `pyproject.toml` and produces a workflow with build matrices, caching, and publish steps already configured.

## Multi-repo operations

When you manage a family of packages, coordinate them as a group:

```bash
# build all repos in a manifest
hwb multirepo build --manifest repos.yml

# sync versions across repos
hwb multirepo sync --version 2.0.0

# cut a coordinated release
hwb multirepo release --tag v2.0.0
```

## Notifications

Send build results to your team:

```bash
# Slack
hwb notify --channel slack --webhook $SLACK_URL --message "v1.0.0 published"

# Discord
hwb notify --channel discord --webhook $DISCORD_URL

# Microsoft Teams
hwb notify --channel teams --webhook $TEAMS_URL

# Generic webhook
hwb notify --channel webhook --url https://example.com/hook
```

Notifications include build status, duration, artifact count, and a link to the release.

## Artifact caching

Built wheels are cached locally using an LRU strategy:

```bash
# list cached artifacts
hwb cache list

# set max cache size
hwb cache config --max-size 5GB

# prune old entries
hwb cache prune
```

Cache hits skip the entire build step, cutting repeat builds from minutes to seconds.

## Metrics and analytics

Track your build health over time:

```bash
# show build stats
hwb metrics summary

# export to JSON for dashboards
hwb metrics export --format json --output metrics.json
```

Metrics include build success rates, average duration, cache hit ratios, and failure breakdowns by error type.
