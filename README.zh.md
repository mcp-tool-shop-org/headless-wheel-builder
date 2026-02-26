<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  
            <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/headless-wheel-builder/readme.png"
           alt="Headless Wheel Builder" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/headless-wheel-builder/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/headless-wheel-builder/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/headless-wheel-builder/"><img src="https://img.shields.io/pypi/v/headless-wheel-builder" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/headless-wheel-builder/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

一个通用的、无界面的 Python wheel 构建工具，集成了 GitHub 操作、发布管理以及完整的 CI/CD 流水线自动化功能。它可以构建 wheel 文件，通过审批流程管理发布，分析依赖关系，并协调多个仓库的操作——所有这些都可以在不使用 Web 界面的情况下完成。

它是 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 的一部分，提供实用且不干扰开发的工具。

## 为什么选择无界面 wheel 构建工具？

大多数 Python 构建工具都止步于 `python -m build`。无界面 wheel 构建工具可以做得更多：它可以创建带有审批流程的草稿版本，进行依赖分析（包括许可证合规性），协调多个仓库的操作，并通过单个命令行界面进行注册发布。如果您为 Python 包运行 CI/CD 流水线，那么它可以用一个工具替换掉一系列脚本。

## v0.3.0 的新功能

- **发布管理：** 创建带有多阶段审批流程的草稿版本。
- **依赖分析：** 完整的依赖关系图，并进行许可证合规性检查。
- **CI/CD 流水线：** 构建到发布的流水线编排。
- **多仓库操作：** 协调跨仓库的构建。
- **通知：** Slack、Discord 和 webhook 集成。
- **安全扫描：** SBOM（软件物料清单）生成、许可证审计、漏洞检查。
- **指标与分析：** 构建性能跟踪和报告。
- **工件缓存：** LRU（最近最少使用）缓存，并与注册表集成。

## 功能

### 核心构建
- **从任何地方构建：** 本地路径、Git URL（包含分支/标签）、tarball 文件。
- **构建隔离：** venv（基于 uv，速度可达 10-100 倍），或 Docker（manylinux/musllinux）。
- **多平台：** 构建矩阵，支持 Python 3.10-3.14，Linux/macOS/Windows。
- **发布：** PyPI 信任发布者（OIDC）、DevPi、Artifactory、S3。

### 发布管理
- **草稿版本：** 创建、审查和批准发布版本，然后再发布。
- **审批流程：** 简单、两阶段，或企业级（QA → 安全 → 发布）。
- **回滚支持：** 轻松回滚已发布的版本。
- **变更日志生成：** 从 Conventional Commits 自动生成。

### DevOps & CI/CD
- **流水线编排：** 链接构建 → 测试 → 发布 → 发布。
- **GitHub Actions 生成器：** 创建优化的 CI 工作流。
- **多仓库操作：** 协调跨仓库的发布。
- **工件缓存：** 通过智能缓存减少构建时间。

### 分析与安全
- **依赖关系图：** 可视化和分析包的依赖关系。
- **许可证合规性：** 检测项目中是否存在 GPL 许可证，以及识别未知的许可证。
- **安全扫描：** 漏洞检测、SBOM 生成。
- **指标仪表板：** 跟踪构建时间、成功率、缓存命中率。

### 集成
- **通知：** Slack、Discord、Microsoft Teams、自定义 webhook。
- **无界面 GitHub：** 发布、拉取请求、问题、工作流——完全可脚本化。
- **注册表支持：** PyPI、TestPyPI、私有注册表、S3。

## 安装

```bash
# With pip
pip install headless-wheel-builder

# With uv (recommended - faster)
uv pip install headless-wheel-builder

# With all optional dependencies
pip install headless-wheel-builder[all]
```

## 快速开始

### 构建 Wheel 文件

```bash
# Build from current directory
hwb build

# Build from git repository
hwb build https://github.com/user/repo

# Build specific version with Docker isolation
hwb build https://github.com/user/repo@v2.0.0 --isolation docker

# Build for multiple Python versions
hwb build --python 3.11 --python 3.12
```

### 发布管理

```bash
# Create a draft release
hwb release create -n "v1.0.0 Release" -v 1.0.0 -p my-package \
    --template two-stage --changelog CHANGELOG.md

# Submit for approval
hwb release submit rel-abc123

# Approve the release
hwb release approve rel-abc123 -a alice

# Publish when approved
hwb release publish rel-abc123

# View pending approvals
hwb release pending
```

### 依赖分析

```bash
# Show dependency tree
hwb deps tree requests

# Check for license issues
hwb deps licenses numpy --check

# Detect circular dependencies
hwb deps cycles ./my-project

# Get build order
hwb deps order ./my-project
```

### 流水线自动化

```bash
# Run a complete build-to-release pipeline
hwb pipeline run my-pipeline.yml

# Execute specific stages
hwb pipeline run my-pipeline.yml --stage build --stage test

# Generate GitHub Actions workflow
hwb actions generate ./my-project --output .github/workflows/ci.yml
```

### 通知

```bash
# Configure Slack notifications
hwb notify config slack --webhook-url https://hooks.slack.com/...

# Send a build notification
hwb notify send slack "Build completed successfully" --status success

# Test webhook integration
hwb notify test discord
```

### 安全扫描

```bash
# Full security audit
hwb security audit ./my-project

# Generate SBOM
hwb security sbom ./my-project --format cyclonedx

# License compliance check
hwb security licenses ./my-project --policy permissive
```

### 多仓库操作

```bash
# Build multiple repositories
hwb multirepo build repos.yml

# Sync versions across repos
hwb multirepo sync --version 2.0.0

# Coordinate releases
hwb multirepo release --tag v2.0.0
```

### 指标与分析

```bash
# Show build metrics
hwb metrics show

# Export metrics for monitoring
hwb metrics export --format prometheus

# Analyze build trends
hwb metrics trends --period 30d
```

### 缓存管理

```bash
# Show cache statistics
hwb cache stats

# List cached packages
hwb cache list

# Prune old entries
hwb cache prune --max-size 1G
```

## 无界面 GitHub 操作

```bash
# Create a release with assets
hwb github release v1.0.0 --repo owner/repo --files dist/*.whl

# Trigger a workflow
hwb github workflow run build.yml --repo owner/repo --ref main

# Create a pull request
hwb github pr create --repo owner/repo --head feature --base main \
    --title "Add new feature" --body "Description here"

# Create an issue
hwb github issue create --repo owner/repo --title "Bug report" --body "Details..."
```

## Python API

```python
import asyncio
from headless_wheel_builder import build_wheel
from headless_wheel_builder.release import ReleaseManager, ReleaseConfig
from headless_wheel_builder.depgraph import DependencyAnalyzer

# Build a wheel
async def build():
    result = await build_wheel(source=".", output_dir="dist", python="3.12")
    print(f"Built: {result.wheel_path}")

# Create and manage releases
def manage_releases():
    manager = ReleaseManager()

    # Create draft
    draft = manager.create_draft(
        name="v1.0.0",
        version="1.0.0",
        package="my-package",
        template="two-stage",
    )

    # Submit and approve
    manager.submit_for_approval(draft.id)
    manager.approve(draft.id, "alice")
    manager.publish(draft.id, "publisher")

# Analyze dependencies
async def analyze_deps():
    analyzer = DependencyAnalyzer()
    graph = await analyzer.build_graph("requests")

    print(f"Dependencies: {len(graph.nodes)}")
    print(f"Cycles: {graph.cycles}")
    print(f"License issues: {graph.license_issues}")

asyncio.run(build())
```

## 配置

在 `pyproject.toml` 文件中进行配置：

```toml
[tool.hwb]
output-dir = "dist"
python = "3.12"

[tool.hwb.build]
sdist = true
checksum = true

[tool.hwb.release]
require-approval = true
default-template = "two-stage"
auto-publish = false

[tool.hwb.notifications]
slack-webhook = "${SLACK_WEBHOOK_URL}"
on-success = true
on-failure = true

[tool.hwb.cache]
max-size = "1G"
max-age = "30d"
```

## 命令行

| 命令 | 描述 |
| --------- | ------------- |
| `hwb build` | 从源代码构建 wheel 文件 |
| `hwb publish` | 发布到 PyPI/注册表 |
| `hwb inspect` | 分析项目配置 |
| `hwb github` | GitHub 操作（发布、拉取请求、问题） |
| `hwb release` | 草稿发布管理 |
| `hwb pipeline` | CI/CD 流水线编排 |
| `hwb deps` | 依赖关系图分析 |
| `hwb actions` | GitHub Actions 生成器 |
| `hwb multirepo` | 多仓库操作 |
| `hwb notify` | 通知管理 |
| `hwb security` | 安全扫描 |
| `hwb metrics` | 构建指标与分析 |
| `hwb cache` | 构建产物缓存管理 |
| `hwb changelog` | 变更日志生成 |

## 需求

- Python 3.10+
- Git（用于支持 Git 源代码）
- Docker（可选，用于构建 manylinux 镜像）
- uv（可选，用于加速构建）

## 文档

请参阅 [docs/](docs/) 目录中的详细文档：

- [ROADMAP.md](docs/ROADMAP.md) - 开发阶段和里程碑
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - 系统设计和组件
- [API.md](docs/API.md) - CLI 和 Python API 参考
- [SECURITY.md](docs/SECURITY.md) - 安全模型和最佳实践
- [PUBLISHING.md](docs/PUBLISHING.md) - 注册表发布工作流程
- [ISOLATION.md](docs/ISOLATION.md) - 构建隔离策略
- [VERSIONING.md](docs/VERSIONING.md) - 语义版本控制和变更日志
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - 开发指南

## 许可证

MIT 许可证，详情请参阅 [LICENSE](LICENSE)。

## 贡献

欢迎贡献！请参阅 [CONTRIBUTING.md](docs/CONTRIBUTING.md) 了解指南。
