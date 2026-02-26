<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="assets/logo.png" alt="Headless Wheel Builder" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/headless-wheel-builder/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/headless-wheel-builder/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/headless-wheel-builder/"><img src="https://img.shields.io/pypi/v/headless-wheel-builder" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/headless-wheel-builder/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Un constructor de paquetes (wheels) de Python universal y sin interfaz gráfica, con operaciones integradas de GitHub, gestión de versiones y automatización completa de la canalización de CI/CD. Cree paquetes, gestione las versiones con flujos de trabajo de aprobación, analice las dependencias y coordine operaciones en múltiples repositorios, todo ello sin necesidad de interactuar con la interfaz web.

Parte de [MCP Tool Shop](https://mcp-tool-shop.github.io/) – herramientas prácticas para desarrolladores que no se interponen en su camino.

## ¿Por qué un constructor de paquetes sin interfaz gráfica?

La mayoría de las herramientas de construcción de Python se detienen en `python -m build`. El constructor de paquetes sin interfaz gráfica va más allá: crea versiones preliminares con flujos de trabajo de aprobación, análisis de dependencias con verificación de cumplimiento de licencias, coordinación entre múltiples repositorios y publicación en registros, todo ello desde una única línea de comandos. Si utiliza canalizaciones de CI/CD para paquetes de Python, esta herramienta reemplaza una serie de scripts con una única herramienta.

## Novedades en la versión 0.3.0

- **Gestión de versiones**: Creación de versiones preliminares con flujos de trabajo de aprobación de múltiples etapas.
- **Análisis de dependencias**: Gráfico completo de dependencias con verificación de cumplimiento de licencias.
- **Canalizaciones de CI/CD**: Orquestación de la canalización de construcción a versión.
- **Operaciones en múltiples repositorios**: Coordinación de compilaciones en diferentes repositorios.
- **Notificaciones**: Integraciones con Slack, Discord y webhooks.
- **Análisis de seguridad**: Generación de SBOM (Software Bill of Materials), auditorías de licencias y verificación de vulnerabilidades.
- **Métricas y análisis**: Seguimiento y generación de informes sobre el rendimiento de las compilaciones.
- **Almacenamiento en caché de artefactos**: Caché LRU (Least Recently Used) con integración con el registro.

## Características

### Construcción básica
- **Construcción desde cualquier lugar**: Rutas locales, URL de Git (con rama/etiqueta), archivos tar.
- **Aislamiento de la construcción**: Entorno virtual (venv, potenciado por uv, hasta 100 veces más rápido) o Docker (manylinux/musllinux).
- **Multiplataforma**: Matriz de compilación para Python 3.10-3.14, Linux/macOS/Windows.
- **Publicación**: Publicadores de confianza de PyPI (OIDC), DevPi, Artifactory, S3.

### Gestión de versiones
- **Creación de versiones preliminares**: Cree, revise y apruebe las versiones antes de publicarlas.
- **Flujos de trabajo de aprobación**: Sencillos, de dos etapas o empresariales (QA → Seguridad → Versión).
- **Soporte para reversión**: Revierte fácilmente las versiones publicadas.
- **Generación de changelog**: Generación automática a partir de commits convencionales.

### DevOps y CI/CD
- **Orquestación de canalizaciones**: Encadena la construcción, las pruebas, la versión y la publicación.
- **Generador de acciones de GitHub**: Crea flujos de trabajo de CI optimizados.
- **Operaciones en múltiples repositorios**: Coordina las versiones en diferentes repositorios.
- **Almacenamiento en caché de artefactos**: Reduce los tiempos de compilación con un almacenamiento en caché inteligente.

### Análisis y seguridad
- **Gráficos de dependencias**: Visualice y analice las dependencias de los paquetes.
- **Cumplimiento de licencias**: Detecte licencias GPL en proyectos permisivos y licencias desconocidas.
- **Análisis de seguridad**: Detección de vulnerabilidades, generación de SBOM.
- **Panel de métricas**: Realice un seguimiento de los tiempos de compilación, las tasas de éxito y los aciertos en la caché.

### Integraciones
- **Notificaciones**: Slack, Discord, Microsoft Teams, webhooks personalizados.
- **GitHub sin interfaz gráfica**: Versiones, solicitudes de extracción (PR), problemas, flujos de trabajo: todo se puede controlar mediante scripts.
- **Soporte para registros**: PyPI, TestPyPI, registros privados, S3.

## Instalación

```bash
# With pip
pip install headless-wheel-builder

# With uv (recommended - faster)
uv pip install headless-wheel-builder

# With all optional dependencies
pip install headless-wheel-builder[all]
```

## Guía de inicio rápido

### Construcción de paquetes

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

### Gestión de versiones

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

### Análisis de dependencias

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

### Automatización de canalizaciones

```bash
# Run a complete build-to-release pipeline
hwb pipeline run my-pipeline.yml

# Execute specific stages
hwb pipeline run my-pipeline.yml --stage build --stage test

# Generate GitHub Actions workflow
hwb actions generate ./my-project --output .github/workflows/ci.yml
```

### Notificaciones

```bash
# Configure Slack notifications
hwb notify config slack --webhook-url https://hooks.slack.com/...

# Send a build notification
hwb notify send slack "Build completed successfully" --status success

# Test webhook integration
hwb notify test discord
```

### Análisis de seguridad

```bash
# Full security audit
hwb security audit ./my-project

# Generate SBOM
hwb security sbom ./my-project --format cyclonedx

# License compliance check
hwb security licenses ./my-project --policy permissive
```

### Operaciones en múltiples repositorios

```bash
# Build multiple repositories
hwb multirepo build repos.yml

# Sync versions across repos
hwb multirepo sync --version 2.0.0

# Coordinate releases
hwb multirepo release --tag v2.0.0
```

### Métricas y análisis

```bash
# Show build metrics
hwb metrics show

# Export metrics for monitoring
hwb metrics export --format prometheus

# Analyze build trends
hwb metrics trends --period 30d
```

### Gestión de caché

```bash
# Show cache statistics
hwb cache stats

# List cached packages
hwb cache list

# Prune old entries
hwb cache prune --max-size 1G
```

## Operaciones de GitHub sin interfaz gráfica

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

## API de Python

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

## Configuración

Configure en `pyproject.toml`:

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

## Comandos de la línea de comandos

| Comando | Descripción |
| --------- | ------------- |
| `hwb build` | Construye paquetes a partir del código fuente. |
| `hwb publish` | Publica en PyPI/registros. |
| `hwb inspect` | Analiza la configuración del proyecto. |
| `hwb github` | Operaciones de GitHub (lanzamientos, solicitudes de extracción, incidencias) |
| `hwb release` | Gestión de lanzamientos (borrador) |
| `hwb pipeline` | Orquestación de la canalización CI/CD |
| `hwb deps` | Análisis del grafo de dependencias |
| `hwb actions` | Generador de GitHub Actions |
| `hwb multirepo` | Operaciones con múltiples repositorios |
| `hwb notify` | Gestión de notificaciones |
| `hwb security` | Análisis de seguridad |
| `hwb metrics` | Métricas y análisis de compilación |
| `hwb cache` | Gestión de la caché de artefactos |
| `hwb changelog` | Generación de registros de cambios |

## Requisitos

- Python 3.10+
- Git (para soporte de código fuente Git)
- Docker (opcional, para compilaciones manylinux)
- uv (opcional, para compilaciones más rápidas)

## Documentación

Consulte el directorio [docs/](docs/) para obtener documentación completa:

- [ROADMAP.md](docs/ROADMAP.md) - Fases y hitos de desarrollo
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Diseño y componentes del sistema
- [API.md](docs/API.md) - Referencia de la API de la línea de comandos y de Python
- [SECURITY.md](docs/SECURITY.md) - Modelo de seguridad y mejores prácticas
- [PUBLISHING.md](docs/PUBLISHING.md) - Flujos de trabajo de publicación en el registro
- [ISOLATION.md](docs/ISOLATION.md) - Estrategias de aislamiento de la compilación
- [VERSIONING.md](docs/VERSIONING.md) - Versionado semántico y registro de cambios
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - Directrices de desarrollo

## Licencia

Licencia MIT. Consulte [LICENSE](LICENSE) para obtener más detalles.

## Contribuciones

¡Las contribuciones son bienvenidas! Consulte [CONTRIBUTING.md](docs/CONTRIBUTING.md) para obtener las directrices.
