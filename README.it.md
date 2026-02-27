<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

Un costruttore di pacchetti Python universale e senza interfaccia grafica, con integrazione di GitHub, gestione delle release e automazione completa della pipeline CI/CD. Crea pacchetti, gestisci le release con flussi di approvazione, analizza le dipendenze e coordina le operazioni su più repository, il tutto senza dover interagire con l'interfaccia web.

Parte di [MCP Tool Shop](https://mcp-tool-shop.github.io/) -- strumenti pratici per sviluppatori che non ti ostacolano.

## Perché un costruttore di pacchetti senza interfaccia grafica?

La maggior parte degli strumenti di build Python si fermano a `python -m build`. Questo costruttore di pacchetti va oltre: crea release preliminari con flussi di approvazione, analisi delle dipendenze con verifica della conformità delle licenze, coordinamento tra più repository e pubblicazione sui registri, il tutto da un'unica interfaccia a riga di comando. Se utilizzi pipeline CI/CD per i pacchetti Python, questo strumento sostituisce una serie di script con un'unica soluzione.

## Novità nella versione 0.3.0

- **Gestione delle release**: Creazione di release preliminari con flussi di approvazione a più fasi.
- **Analisi delle dipendenze**: Grafico completo delle dipendenze con verifica della conformità delle licenze.
- **Pipeline CI/CD**: Orchestrazione della pipeline di build-to-release.
- **Operazioni su più repository**: Coordinamento delle build tra i repository.
- **Notifiche**: Integrazioni con Slack, Discord e webhook.
- **Analisi della sicurezza**: Generazione di SBOM (Software Bill of Materials), audit delle licenze, controlli delle vulnerabilità.
- **Metriche e analisi**: Monitoraggio e reportistica delle prestazioni delle build.
- **Caching degli artefatti**: Cache LRU (Least Recently Used) con integrazione del registro.

## Funzionalità

### Costruzione di base
- **Costruisci da qualsiasi posizione**: Percorsi locali, URL Git (con branch/tag), archivi tar.
- **Isolamento della build**: venv (basato su uv, da 10 a 100 volte più veloce) o Docker (manylinux/musllinux).
- **Multi-piattaforma**: Matrice di build per Python 3.10-3.14, Linux/macOS/Windows.
- **Pubblicazione**: PyPI Trusted Publishers (OIDC), DevPi, Artifactory, S3.

### Gestione delle release
- **Release preliminari**: Crea, esamina e approva le release prima della pubblicazione.
- **Flussi di approvazione**: Semplici, a due fasi o aziendali (QA → Sicurezza → Release).
- **Supporto per il rollback**: Ripristina facilmente le release pubblicate.
- **Generazione del changelog**: Generazione automatica dai commit convenzionali.

### DevOps e CI/CD
- **Orchestrazione della pipeline**: Catena build → test → release → pubblicazione.
- **Generatore di GitHub Actions**: Crea flussi di lavoro CI ottimizzati.
- **Operazioni su più repository**: Coordina le release tra i repository.
- **Caching degli artefatti**: Riduci i tempi di build con un caching intelligente.

### Analisi e sicurezza
- **Grafici delle dipendenze**: Visualizza e analizza le dipendenze dei pacchetti.
- **Conformità delle licenze**: Rileva la presenza di licenze GPL in progetti permissivi, licenze sconosciute.
- **Analisi della sicurezza**: Rilevamento delle vulnerabilità, generazione di SBOM.
- **Dashboard delle metriche**: Monitora i tempi di build, i tassi di successo, i colpi di cache.

### Integrazioni
- **Notifiche**: Slack, Discord, Microsoft Teams, webhook personalizzati.
- **GitHub senza interfaccia grafica**: Release, PR, issue, workflow: completamente scriptabili.
- **Supporto per i registri**: PyPI, TestPyPI, registri privati, S3.

## Installazione

```bash
# With pip
pip install headless-wheel-builder

# With uv (recommended - faster)
uv pip install headless-wheel-builder

# With all optional dependencies
pip install headless-wheel-builder[all]
```

## Guida rapida

### Crea pacchetti

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

### Gestione delle release

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

### Analisi delle dipendenze

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

### Automazione della pipeline

```bash
# Run a complete build-to-release pipeline
hwb pipeline run my-pipeline.yml

# Execute specific stages
hwb pipeline run my-pipeline.yml --stage build --stage test

# Generate GitHub Actions workflow
hwb actions generate ./my-project --output .github/workflows/ci.yml
```

### Notifiche

```bash
# Configure Slack notifications
hwb notify config slack --webhook-url https://hooks.slack.com/...

# Send a build notification
hwb notify send slack "Build completed successfully" --status success

# Test webhook integration
hwb notify test discord
```

### Analisi della sicurezza

```bash
# Full security audit
hwb security audit ./my-project

# Generate SBOM
hwb security sbom ./my-project --format cyclonedx

# License compliance check
hwb security licenses ./my-project --policy permissive
```

### Operazioni su più repository

```bash
# Build multiple repositories
hwb multirepo build repos.yml

# Sync versions across repos
hwb multirepo sync --version 2.0.0

# Coordinate releases
hwb multirepo release --tag v2.0.0
```

### Metriche e analisi

```bash
# Show build metrics
hwb metrics show

# Export metrics for monitoring
hwb metrics export --format prometheus

# Analyze build trends
hwb metrics trends --period 30d
```

### Gestione della cache

```bash
# Show cache statistics
hwb cache stats

# List cached packages
hwb cache list

# Prune old entries
hwb cache prune --max-size 1G
```

## Operazioni di GitHub senza interfaccia grafica

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

## Configurazione

Configura in `pyproject.toml`:

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

## Comandi della riga di comando

| Comando | Descrizione |
|---------|-------------|
| `hwb build` | Crea pacchetti dal codice sorgente |
| `hwb publish` | Pubblica su PyPI/registri |
| `hwb inspect` | Analizza la configurazione del progetto |
| `hwb github` | Operazioni di GitHub (release, PR, issue) |
| `hwb release` | Gestione delle release preliminari |
| `hwb pipeline` | Orchestrazione della pipeline CI/CD |
| `hwb deps` | Analisi del grafo delle dipendenze |
| `hwb actions` | Generatore di GitHub Actions |
| `hwb multirepo` | Operazioni su più repository |
| `hwb notify` | Gestione delle notifiche |
| `hwb security` | Analisi della sicurezza |
| `hwb metrics` | Metriche e analisi dei build |
| `hwb cache` | Gestione della cache degli artefatti |
| `hwb changelog` | Generazione del changelog |

## Requisiti

- Python 3.10+
- Git (per il supporto del codice sorgente Git)
- Docker (opzionale, per i build manylinux)
- uv (opzionale, per build più veloci)

## Documentazione

Consultare la directory [docs/](docs/) per la documentazione completa:

- [ROADMAP.md](docs/ROADMAP.md) - Fasi di sviluppo e obiettivi
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Progettazione del sistema e componenti
- [API.md](docs/API.md) - Riferimento dell'API CLI e Python
- [SECURITY.md](docs/SECURITY.md) - Modello di sicurezza e buone pratiche
- [PUBLISHING.md](docs/PUBLISHING.md) - Flussi di pubblicazione nel registro
- [ISOLATION.md](docs/ISOLATION.md) - Strategie di isolamento dei build
- [VERSIONING.md](docs/VERSIONING.md) - Versioning semantico e changelog
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - Linee guida per lo sviluppo

## Sicurezza e Privacy

**Dati accessibili:** codice sorgente Python (solo lettura per l'analisi), artefatti di build (dist/), pyproject.toml, cronologia Git, container Docker, API del registro dei pacchetti.

**Dati NON accessibili:** credenziali utente direttamente (utilizza variabili d'ambiente e token OIDC), file di sistema al di fuori del progetto. Non vengono raccolti o trasmessi dati di telemetria. I token vengono letti solo dalle variabili d'ambiente e non vengono mai registrati.

**Permessi:** lettura/scrittura del file system per i build, socket Docker (opzionale), rete per la pubblicazione nel registro e l'API di GitHub. Consultare [SECURITY.md](SECURITY.md) per la politica completa.

## Licenza

Licenza MIT -- vedere [LICENSE](LICENSE) per i dettagli.

## Contributi

I contributi sono benvenuti! Consultare [CONTRIBUTING.md](docs/CONTRIBUTING.md) per le linee guida.

---

Creato da <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
