import type { SiteConfig } from '@mcptoolshop/site-theme';

export const config: SiteConfig = {
  title: 'Headless Wheel Builder',
  description: 'Universal, headless Python wheel builder supporting local paths, git repos, and CI/CD pipelines.',
  logoBadge: 'HW',
  brandName: 'Headless Wheel Builder',
  repoUrl: 'https://github.com/mcp-tool-shop-org/headless-wheel-builder',
  footerText: 'MIT Licensed — built by <a href="https://github.com/mcp-tool-shop-org" style="color:var(--color-muted);text-decoration:underline">mcp-tool-shop-org</a>',

  hero: {
    badge: 'Python · uv-powered · headless',
    headline: 'Replace the scripts.',
    headlineAccent: 'One CLI does it all.',
    description: 'Universal, headless Python wheel builder supporting local paths, git repos, and CI/CD pipelines.',
    primaryCta: { href: '#usage', label: 'Get started' },
    secondaryCta: { href: 'handbook/', label: 'Read the Handbook' },
    previews: [
      {
        label: 'Install',
        code: '# pip or uv\npip install headless-wheel-builder\n\n# with all extras\npip install headless-wheel-builder[all]',
      },
      {
        label: 'Build & release',
        code: '# build from anywhere\nhwb build https://github.com/user/repo@v2.0.0\n\n# draft release with approval workflow\nhwb release create -v 1.0.0 -p my-package --template two-stage\nhwb release submit rel-abc123\nhwb release approve rel-abc123 -a alice\nhwb release publish rel-abc123',
      },
      {
        label: 'Pipeline',
        code: '# run a complete build-to-release pipeline\nhwb pipeline run my-pipeline.yml\n\n# generate GitHub Actions workflow\nhwb actions generate ./my-project --output .github/workflows/ci.yml\n\n# coordinate releases across repos\nhwb multirepo release --tag v2.0.0',
      },
    ],
  },

  sections: [
    {
      kind: 'features',
      id: 'features',
      title: 'Beyond python -m build',
      subtitle: 'Everything after the build step — release workflows, dependency analysis, security scanning — in one tool.',
      features: [
        {
          title: 'Build from anywhere',
          desc: 'Local paths, git URLs with branch or tag, tarballs, multi-platform matrices. venv (uv-powered, 10-100x faster) or Docker (manylinux/musllinux).',
        },
        {
          title: 'Approval workflows',
          desc: 'Draft releases, multi-stage approval (simple, two-stage, or enterprise QA → Security → Release), auto-changelog from Conventional Commits.',
        },
        {
          title: 'Security & compliance',
          desc: 'Dependency graph analysis, license compliance checks, SBOM generation (CycloneDX), vulnerability scanning, and build metrics dashboard.',
        },
      ],
    },
    {
      kind: 'data-table',
      id: 'cli',
      title: 'CLI reference',
      subtitle: 'Every pipeline step, one command.',
      columns: ['Command', 'What it does'],
      rows: [
        ['hwb build', 'Build wheels from local path, git URL, or tarball'],
        ['hwb publish', 'Publish to PyPI, TestPyPI, private registries, or S3'],
        ['hwb release', 'Draft, approve, and publish releases with approval workflows'],
        ['hwb pipeline', 'Orchestrate build → test → release → publish pipelines'],
        ['hwb deps', 'Dependency graph analysis and license compliance checks'],
        ['hwb security', 'SBOM generation, vulnerability detection, license auditing'],
        ['hwb github', 'Headless GitHub: releases, PRs, issues, workflow triggers'],
        ['hwb multirepo', 'Build and coordinate releases across multiple repositories'],
        ['hwb metrics', 'Build performance tracking, success rates, cache hit analytics'],
        ['hwb cache', 'LRU artifact cache management with registry integration'],
      ],
    },
    {
      kind: 'code-cards',
      id: 'usage',
      title: 'Get started',
      cards: [
        {
          title: 'Install',
          code: 'pip install headless-wheel-builder\n# or with uv (recommended)\nuv pip install headless-wheel-builder',
        },
        {
          title: 'Build from git',
          code: 'hwb build https://github.com/user/repo@v2.0.0 \\\n  --isolation docker \\\n  --python 3.11 --python 3.12',
        },
        {
          title: 'Security audit',
          code: 'hwb security audit ./my-project\nhwb security sbom ./my-project --format cyclonedx\nhwb deps licenses numpy --check',
        },
        {
          title: 'Python API',
          code: 'from headless_wheel_builder import build_wheel\n\nresult = await build_wheel(\n  source=".",\n  output_dir="dist",\n  python="3.12",\n)\nprint(f"Built: {result.wheel_path}")',
        },
      ],
    },
    {
      kind: 'features',
      id: 'how-it-works',
      title: 'How it works',
      subtitle: 'A complete wheel lifecycle — from source to shipped — with no web UI required.',
      features: [
        {
          title: '1. Build',
          desc: 'Point hwb at any source — local directory, git URL, or tarball. It creates an isolated venv or Docker container and builds your wheels.',
        },
        {
          title: '2. Review & approve',
          desc: 'Draft a release, run it through your approval workflow, generate a changelog, and sign off — all from the CLI.',
        },
        {
          title: '3. Publish & notify',
          desc: 'Push to PyPI, private registries, or S3. Notify Slack, Discord, or Teams. Track metrics. Cache artifacts for the next run.',
        },
      ],
    },
  ],
};
