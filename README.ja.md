<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/headless-wheel-builder/readme.png" alt="Headless Wheel Builder" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/headless-wheel-builder/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/headless-wheel-builder/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/headless-wheel-builder/"><img src="https://img.shields.io/pypi/v/headless-wheel-builder" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/headless-wheel-builder/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

汎用的な、ヘッドレスのPython wheelビルダで、GitHub連携、リリース管理、および完全なCI/CDパイプラインの自動化機能を統合しています。 wheelのビルド、承認ワークフローによるリリース管理、依存関係の分析、および複数のリポジトリを対象とした操作を、Web UIに触れることなく実行できます。

[MCP Tool Shop](https://mcp-tool-shop.github.io/)の一部です。これは、邪魔にならない実用的な開発ツールです。

## ヘッドレスwheelビルダの利点

多くのPythonビルドツールは`python -m build`で終わります。ヘッドレスwheelビルダは、承認ワークフローによるドラフトリリース、ライセンスコンプライアンスを含む依存関係分析、複数リポジトリの連携、およびレジストリへの公開など、さらに多くの機能を提供します。これらはすべて、単一のCLIから実行できます。PythonパッケージのCI/CDパイプラインを実行している場合、これは複数のスクリプトを1つのツールに置き換えることができます。

## v0.3.0の主な変更点

- **リリース管理**: 複数段階の承認ワークフローによるドラフトリリース
- **依存関係分析**: ライセンスコンプライアンスチェックを含む完全な依存関係グラフ
- **CI/CDパイプライン**: ビルドからリリースまでのパイプラインのオーケストレーション
- **複数リポジトリ操作**: 複数のリポジトリにまたがるビルドの連携
- **通知**: Slack、Discord、およびwebhook連携
- **セキュリティスキャン**: SBOM（ソフトウェア部品構成表）の生成、ライセンス監査、脆弱性チェック
- **メトリクスと分析**: ビルドパフォーマンスの追跡とレポート
- **アーティファクトキャッシュ**: レジストリ連携を含むLRUキャッシュ

## 機能

### コアビルド機能
- **どこからでもビルド**: ローカルパス、git URL（ブランチ/タグ付き）、tarball
- **ビルドの分離**: venv（uv搭載、10～100倍高速）、またはDocker（manylinux/musllinux）
- **マルチプラットフォーム**: Python 3.10～3.14、Linux/macOS/Windows向けのビルドマトリックス
- **公開**: PyPI Trusted Publishers (OIDC)、DevPi、Artifactory、S3

### リリース管理
- **ドラフトリリース**: 公開前にリリースを作成、レビュー、承認
- **承認ワークフロー**: シンプル、2段階、またはエンタープライズ（QA → セキュリティ → リリース）
- **ロールバック**: 公開されたリリースの簡単な復元
- **変更ログの生成**: Conventional Commitsから自動生成

### DevOps & CI/CD
- **パイプラインオーケストレーション**: ビルド → テスト → リリース → 公開の連携
- **GitHub Actionsジェネレーター**: 最適化されたCIワークフローの作成
- **複数リポジトリ操作**: 複数のリポジトリにまたがるリリースの連携
- **アーティファクトキャッシュ**: インテリジェントなキャッシュによるビルド時間の短縮

### 分析とセキュリティ
- **依存関係グラフ**: パッケージの依存関係を可視化および分析
- **ライセンスコンプライアンス**: 許可的なプロジェクトにおけるGPLの検出、不明なライセンスの検出
- **セキュリティスキャン**: 脆弱性の検出、SBOMの生成
- **メトリクスダッシュボード**: ビルド時間、成功率、キャッシュヒット率の追跡

### 連携機能
- **通知**: Slack、Discord、Microsoft Teams、カスタムwebhook
- **ヘッドレスGitHub**: リリース、プルリクエスト、課題、ワークフロー - すべてスクリプトで制御可能
- **レジストリサポート**: PyPI、TestPyPI、プライベートレジストリ、S3

## インストール

```bash
# With pip
pip install headless-wheel-builder

# With uv (recommended - faster)
uv pip install headless-wheel-builder

# With all optional dependencies
pip install headless-wheel-builder[all]
```

## クイックスタート

### wheelのビルド

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

### リリース管理

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

### 依存関係分析

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

### パイプラインの自動化

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

### セキュリティスキャン

```bash
# Full security audit
hwb security audit ./my-project

# Generate SBOM
hwb security sbom ./my-project --format cyclonedx

# License compliance check
hwb security licenses ./my-project --policy permissive
```

### 複数リポジトリ操作

```bash
# Build multiple repositories
hwb multirepo build repos.yml

# Sync versions across repos
hwb multirepo sync --version 2.0.0

# Coordinate releases
hwb multirepo release --tag v2.0.0
```

### メトリクスと分析

```bash
# Show build metrics
hwb metrics show

# Export metrics for monitoring
hwb metrics export --format prometheus

# Analyze build trends
hwb metrics trends --period 30d
```

### キャッシュ管理

```bash
# Show cache statistics
hwb cache stats

# List cached packages
hwb cache list

# Prune old entries
hwb cache prune --max-size 1G
```

## ヘッドレスGitHub操作

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

## 設定

`pyproject.toml`で設定します。

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

## CLIコマンド

| コマンド | 説明 |
| --------- | ------------- |
| `hwb build` | ソースからwheelをビルド |
| `hwb publish` | PyPI/レジストリに公開 |
| `hwb inspect` | プロジェクトの設定を分析 |
| `hwb github` | GitHubの操作（リリース、プルリクエスト、課題） |
| `hwb release` | ドラフトリリース管理 |
| `hwb pipeline` | CI/CDパイプラインのオーケストレーション |
| `hwb deps` | 依存関係グラフの分析 |
| `hwb actions` | GitHub Actionsジェネレーター |
| `hwb multirepo` | 複数リポジトリの操作 |
| `hwb notify` | 通知管理 |
| `hwb security` | セキュリティスキャン |
| `hwb metrics` | ビルドのメトリクスと分析 |
| `hwb cache` | 成果物のキャッシュ管理 |
| `hwb changelog` | 変更履歴の生成 |

## 要件

- Python 3.10以降
- Git（Gitソースコードのサポート用）
- Docker（オプション、manylinuxビルド用）
- uv（オプション、より高速なビルド用）

## ドキュメント

詳細なドキュメントは[docs/](docs/)ディレクトリをご覧ください。

- [ROADMAP.md](docs/ROADMAP.md) - 開発段階とマイルストーン
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - システム設計とコンポーネント
- [API.md](docs/API.md) - CLIおよびPython APIリファレンス
- [SECURITY.md](docs/SECURITY.md) - セキュリティモデルとベストプラクティス
- [PUBLISHING.md](docs/PUBLISHING.md) - レジストリへの公開ワークフロー
- [ISOLATION.md](docs/ISOLATION.md) - ビルドの分離戦略
- [VERSIONING.md](docs/VERSIONING.md) - セマンティックバージョニングと変更履歴
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - 開発ガイドライン

## ライセンス

MITライセンス -- 詳細については[LICENSE](LICENSE)をご覧ください。

## 貢献

貢献は大歓迎です！ガイドラインについては[CONTRIBUTING.md](docs/CONTRIBUTING.md)をご覧ください。
