<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/headless-wheel-builder/readme.png" alt="Headless Wheel Builder" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/headless-wheel-builder/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/headless-wheel-builder/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/mcp-tool-shop-org/headless-wheel-builder"><img src="https://codecov.io/gh/mcp-tool-shop-org/headless-wheel-builder/branch/main/graph/badge.svg" alt="codecov"></a>
  <a href="https://pypi.org/project/headless-wheel-builder/"><img src="https://img.shields.io/pypi/v/headless-wheel-builder" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/headless-wheel-builder/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Um construtor universal de pacotes Python (wheels) que funciona sem interface gráfica, com integração com o GitHub, gerenciamento de lançamentos e automação completa de pipelines de CI/CD. Crie pacotes, gerencie lançamentos com fluxos de aprovação, analise dependências e coordene operações em vários repositórios — tudo isso sem precisar usar a interface web.

Parte do [MCP Tool Shop](https://mcp-tool-shop.github.io/) -- ferramentas práticas para desenvolvedores que não atrapalham o seu fluxo de trabalho.

## Por que um construtor de pacotes sem interface gráfica?

A maioria das ferramentas de construção do Python para apenas `python -m build`. O construtor de pacotes sem interface gráfica vai além: permite criar lançamentos com fluxos de aprovação, análise de dependências com verificação de conformidade de licenças, coordenação entre vários repositórios e publicação em registros — tudo a partir de uma única linha de comando. Se você usa pipelines de CI/CD para pacotes Python, esta ferramenta substitui um conjunto de scripts por uma única ferramenta.

## O que há de novo na versão 0.3.0

- **Gerenciamento de Lançamentos**: Criação de lançamentos com fluxos de aprovação em várias etapas.
- **Análise de Dependências**: Gráfico completo de dependências com verificação de conformidade de licenças.
- **Pipelines de CI/CD**: Orquestração de pipelines de construção para lançamento.
- **Operações em Vários Repositórios**: Coordenação de construções entre repositórios.
- **Notificações**: Integrações com Slack, Discord e webhooks.
- **Análise de Segurança**: Geração de SBOM (Software Bill of Materials), auditoria de licenças, verificação de vulnerabilidades.
- **Métricas e Análises**: Rastreamento e relatórios de desempenho da construção.
- **Cache de Artefatos**: Cache LRU (Least Recently Used) com integração com o registro.

## Funcionalidades

### Construção Central
- **Construa de qualquer lugar**: Caminhos locais, URLs do Git (com branch/tag), arquivos tarball.
- **Isolamento da construção**: venv (impulsionado por uv, 10 a 100 vezes mais rápido) ou Docker (manylinux/musllinux).
- **Multiplataforma**: Matriz de construção para Python 3.10-3.14, Linux/macOS/Windows.
- **Publicação**: PyPI Trusted Publishers (OIDC), DevPi, Artifactory, S3.

### Gerenciamento de Lançamentos
- **Lançamentos preliminares**: Crie, revise e aprove lançamentos antes de publicá-los.
- **Fluxos de aprovação**: Simples, de duas etapas ou corporativos (QA → Segurança → Lançamento).
- **Suporte para reversão**: Reverter facilmente lançamentos publicados.
- **Geração de changelog**: Geração automática a partir de commits convencionais.

### DevOps e CI/CD
- **Orquestração de pipelines**: Crie uma cadeia de construção → teste → lançamento → publicação.
- **Gerador de ações do GitHub**: Crie fluxos de CI otimizados.
- **Operações em vários repositórios**: Coordene lançamentos entre repositórios.
- **Cache de artefatos**: Reduza os tempos de construção com cache inteligente.

### Análise e Segurança
- **Gráficos de dependências**: Visualize e analise as dependências dos pacotes.
- **Conformidade de licenças**: Detecte licenças GPL em projetos permissivos, licenças desconhecidas.
- **Análise de segurança**: Detecção de vulnerabilidades, geração de SBOM.
- **Painel de métricas**: Acompanhe os tempos de construção, as taxas de sucesso e os acertos de cache.

### Integrações
- **Notificações**: Slack, Discord, Microsoft Teams, webhooks personalizados.
- **GitHub sem interface gráfica**: Lançamentos, PRs, issues, fluxos de trabalho — totalmente scriptáveis.
- **Suporte a registros**: PyPI, TestPyPI, registros privados, S3.

## Instalação

```bash
# With pip
pip install headless-wheel-builder

# With uv (recommended - faster)
uv pip install headless-wheel-builder

# With all optional dependencies
pip install headless-wheel-builder[all]
```

## Início Rápido

### Construir Pacotes

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

### Gerenciamento de Lançamentos

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

### Análise de Dependências

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

### Automação de Pipelines

```bash
# Run a complete build-to-release pipeline
hwb pipeline run my-pipeline.yml

# Execute specific stages
hwb pipeline run my-pipeline.yml --stage build --stage test

# Generate GitHub Actions workflow
hwb actions generate ./my-project --output .github/workflows/ci.yml
```

### Notificações

```bash
# Configure Slack notifications
hwb notify config slack --webhook-url https://hooks.slack.com/...

# Send a build notification
hwb notify send slack "Build completed successfully" --status success

# Test webhook integration
hwb notify test discord
```

### Análise de Segurança

```bash
# Full security audit
hwb security audit ./my-project

# Generate SBOM
hwb security sbom ./my-project --format cyclonedx

# License compliance check
hwb security licenses ./my-project --policy permissive
```

### Operações em Vários Repositórios

```bash
# Build multiple repositories
hwb multirepo build repos.yml

# Sync versions across repos
hwb multirepo sync --version 2.0.0

# Coordinate releases
hwb multirepo release --tag v2.0.0
```

### Métricas e Análises

```bash
# Show build metrics
hwb metrics show

# Export metrics for monitoring
hwb metrics export --format prometheus

# Analyze build trends
hwb metrics trends --period 30d
```

### Gerenciamento de Cache

```bash
# Show cache statistics
hwb cache stats

# List cached packages
hwb cache list

# Prune old entries
hwb cache prune --max-size 1G
```

## Operações do GitHub sem Interface Gráfica

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

## API Python

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

## Configuração

Configure em `pyproject.toml`:

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

## Comandos da Linha de Comando

| Comando | Descrição |
|---------|-------------|
| `hwb build` | Construir pacotes a partir do código-fonte |
| `hwb publish` | Publicar no PyPI/registros |
| `hwb inspect` | Analisar a configuração do projeto |
| `hwb github` | Operações do GitHub (lançamentos, PRs, issues) |
| `hwb release` | Gerenciamento de lançamentos preliminares |
| `hwb pipeline` | Orquestração de pipelines CI/CD |
| `hwb deps` | Análise de grafos de dependências |
| `hwb actions` | Gerador de GitHub Actions |
| `hwb multirepo` | Operações com múltiplos repositórios |
| `hwb notify` | Gerenciamento de notificações |
| `hwb security` | Análise de segurança |
| `hwb metrics` | Métricas e análises de build |
| `hwb cache` | Gerenciamento de cache de artefatos |
| `hwb changelog` | Geração de changelog |

## Requisitos

- Python 3.10+
- Git (para suporte a fontes Git)
- Docker (opcional, para builds "manylinux")
- uv (opcional, para builds mais rápidos)

## Documentação

Consulte o diretório [docs/](docs/) para documentação completa:

- [ROADMAP.md](docs/ROADMAP.md) - Fases e marcos de desenvolvimento
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Design e componentes do sistema
- [API.md](docs/API.md) - Referência da API da linha de comando e da API Python
- [SECURITY.md](docs/SECURITY.md) - Modelo de segurança e melhores práticas
- [PUBLISHING.md](docs/PUBLISHING.md) - Fluxos de trabalho de publicação no registro
- [ISOLATION.md](docs/ISOLATION.md) - Estratégias de isolamento de builds
- [VERSIONING.md](docs/VERSIONING.md) - Versionamento semântico e changelog
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - Diretrizes de desenvolvimento

## Segurança e Privacidade

**Dados acessados:** Código-fonte Python (somente leitura para análise), artefatos de build (dist/), pyproject.toml, histórico do Git, contêineres Docker, APIs de registro de pacotes.

**Dados NÃO acessados:** Credenciais de usuário diretamente (usa variáveis de ambiente e tokens OIDC), arquivos do sistema fora do projeto. Nenhuma telemetria é coletada ou enviada. Tokens são lidos apenas de variáveis de ambiente e nunca são registrados.

**Permissões:** Leitura/escrita do sistema de arquivos para builds, socket Docker (opcional), rede para publicação no registro e API do GitHub. Consulte [SECURITY.md](SECURITY.md) para a política completa.

## Licença

Licença MIT -- veja [LICENSE](LICENSE) para detalhes.

## Contribuições

Contribuições são bem-vindas! Consulte [CONTRIBUTING.md](docs/CONTRIBUTING.md) para diretrizes.

---

Criado por <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
