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

Un outil universel de création de paquets Python (wheels) sans interface graphique, intégrant les opérations GitHub, la gestion des versions et l'automatisation complète des pipelines CI/CD. Créez des paquets, gérez les versions avec des flux d'approbation, analysez les dépendances et coordonnez les opérations sur plusieurs dépôts, le tout sans utiliser l'interface web.

Fait partie de [MCP Tool Shop](https://mcp-tool-shop.github.io/) -- des outils pratiques pour les développeurs qui ne vous gênent pas.

## Pourquoi un créateur de paquets sans interface graphique ?

La plupart des outils de création de paquets Python s'arrêtent à `python -m build`. Le créateur de paquets sans interface graphique va plus loin : il permet de créer des versions préliminaires avec des flux d'approbation, d'analyser les dépendances avec vérification de la conformité aux licences, de coordonner les opérations sur plusieurs dépôts et de publier sur les registres, le tout depuis une seule interface en ligne de commande. Si vous utilisez des pipelines CI/CD pour les paquets Python, cet outil remplace un ensemble de scripts par un seul outil.

## Nouveautés de la version 0.3.0

- **Gestion des versions**: Création de versions préliminaires avec des flux d'approbation en plusieurs étapes.
- **Analyse des dépendances**: Graphe complet des dépendances avec vérification de la conformité aux licences.
- **Pipelines CI/CD**: Orchestration des pipelines de création à publication.
- **Opérations sur plusieurs dépôts**: Coordination des créations entre les dépôts.
- **Notifications**: Intégrations Slack, Discord et webhooks.
- **Analyse de sécurité**: Génération de SBOM (Software Bill of Materials), audits de licences, vérification des vulnérabilités.
- **Métriques et analyses**: Suivi et rapports sur les performances des créations.
- **Mise en cache des artefacts**: Cache LRU (Least Recently Used) avec intégration au registre.

## Fonctionnalités

### Création de paquets
- **Création depuis n'importe où**: Chemins locaux, URL Git (avec branche/tag), archives tar.
- **Isolation de la création**: Environnements virtuels (basés sur `uv`, 10 à 100 fois plus rapides) ou Docker (manylinux/musllinux).
- **Multiplateforme**: Matrice de création pour Python 3.10 à 3.14, Linux/macOS/Windows.
- **Publication**: PyPI Trusted Publishers (OIDC), DevPi, Artifactory, S3.

### Gestion des versions
- **Création de versions préliminaires**: Création, examen et approbation des versions avant la publication.
- **Flux d'approbation**: Simples, en deux étapes, ou pour les entreprises (QA → Sécurité → Publication).
- **Prise en charge du retour en arrière**: Possibilité de revenir facilement aux versions précédemment publiées.
- **Génération de changelog**: Génération automatique à partir des commits conformes aux conventions.

### DevOps et CI/CD
- **Orchestration des pipelines**: Chaînage de la création, des tests, de la publication et de la mise en ligne.
- **Générateur de workflows GitHub Actions**: Création de workflows CI optimisés.
- **Opérations sur plusieurs dépôts**: Coordination des publications entre les dépôts.
- **Mise en cache des artefacts**: Réduction des temps de création grâce à une mise en cache intelligente.

### Analyse et sécurité
- **Graphes de dépendances**: Visualisation et analyse des dépendances des paquets.
- **Conformité aux licences**: Détection de GPL dans les projets permissifs, licences inconnues.
- **Analyse de sécurité**: Détection des vulnérabilités, génération de SBOM.
- **Tableau de bord des métriques**: Suivi des temps de création, des taux de succès et des taux de succès de la mise en cache.

### Intégrations
- **Notifications**: Slack, Discord, Microsoft Teams, webhooks personnalisés.
- **GitHub sans interface graphique**: Publications, demandes de tirage (PR), problèmes, workflows, entièrement scriptables.
- **Prise en charge des registres**: PyPI, TestPyPI, registres privés, S3.

## Installation

```bash
# With pip
pip install headless-wheel-builder

# With uv (recommended - faster)
uv pip install headless-wheel-builder

# With all optional dependencies
pip install headless-wheel-builder[all]
```

## Premiers pas

### Création de paquets

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

### Gestion des versions

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

### Analyse des dépendances

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

### Automatisation des pipelines

```bash
# Run a complete build-to-release pipeline
hwb pipeline run my-pipeline.yml

# Execute specific stages
hwb pipeline run my-pipeline.yml --stage build --stage test

# Generate GitHub Actions workflow
hwb actions generate ./my-project --output .github/workflows/ci.yml
```

### Notifications

```bash
# Configure Slack notifications
hwb notify config slack --webhook-url https://hooks.slack.com/...

# Send a build notification
hwb notify send slack "Build completed successfully" --status success

# Test webhook integration
hwb notify test discord
```

### Analyse de sécurité

```bash
# Full security audit
hwb security audit ./my-project

# Generate SBOM
hwb security sbom ./my-project --format cyclonedx

# License compliance check
hwb security licenses ./my-project --policy permissive
```

### Opérations sur plusieurs dépôts

```bash
# Build multiple repositories
hwb multirepo build repos.yml

# Sync versions across repos
hwb multirepo sync --version 2.0.0

# Coordinate releases
hwb multirepo release --tag v2.0.0
```

### Métriques et analyses

```bash
# Show build metrics
hwb metrics show

# Export metrics for monitoring
hwb metrics export --format prometheus

# Analyze build trends
hwb metrics trends --period 30d
```

### Gestion du cache

```bash
# Show cache statistics
hwb cache stats

# List cached packages
hwb cache list

# Prune old entries
hwb cache prune --max-size 1G
```

## Opérations GitHub sans interface graphique

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

## Configuration

Configuration dans `pyproject.toml` :

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

## Commandes de l'interface en ligne de commande

| Commande | Description |
| --------- | ------------- |
| `hwb build` | Création de paquets à partir du code source |
| `hwb publish` | Publication sur PyPI/registres |
| `hwb inspect` | Analyse de la configuration du projet |
| `hwb github` | Opérations GitHub (versions, demandes de tirage, problèmes) |
| `hwb release` | Gestion des versions (en projet) |
| `hwb pipeline` | Orchestration des pipelines CI/CD |
| `hwb deps` | Analyse du graphe des dépendances |
| `hwb actions` | Générateur de GitHub Actions |
| `hwb multirepo` | Opérations sur plusieurs dépôts |
| `hwb notify` | Gestion des notifications |
| `hwb security` | Analyse de sécurité |
| `hwb metrics` | Métriques et analyses de construction |
| `hwb cache` | Gestion du cache des artefacts |
| `hwb changelog` | Génération du journal des modifications |

## Prérequis

- Python 3.10+
- Git (pour la prise en charge des sources Git)
- Docker (facultatif, pour les constructions manylinux)
- uv (facultatif, pour des constructions plus rapides)

## Documentation

Consultez le répertoire [docs/](docs/) pour une documentation complète :

- [ROADMAP.md](docs/ROADMAP.md) - Phases et jalons du développement
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Conception et composants du système
- [API.md](docs/API.md) - Référence de l'API CLI et Python
- [SECURITY.md](docs/SECURITY.md) - Modèle de sécurité et bonnes pratiques
- [PUBLISHING.md](docs/PUBLISHING.md) - Flux de publication dans les registres
- [ISOLATION.md](docs/ISOLATION.md) - Stratégies d'isolation des constructions
- [VERSIONING.md](docs/VERSIONING.md) - Versionnement sémantique et journal des modifications
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - Directives de développement

## Licence

Licence MIT -- voir [LICENSE](LICENSE) pour les détails.

## Contributions

Les contributions sont les bienvenues ! Consultez [CONTRIBUTING.md](docs/CONTRIBUTING.md) pour connaître les directives.
