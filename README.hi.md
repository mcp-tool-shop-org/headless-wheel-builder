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

एक सार्वभौमिक, हेडलेस पायथन व्हील बिल्डर जिसमें एकीकृत गिटहब संचालन, रिलीज़ प्रबंधन और पूर्ण CI/CD पाइपलाइन स्वचालन शामिल है। व्हील बनाएं, अनुमोदन वर्कफ़्लो के साथ रिलीज़ प्रबंधित करें, निर्भरताओं का विश्लेषण करें और मल्टी-रिपॉजिटरी संचालन को व्यवस्थित करें - यह सब वेब यूआई को छुए बिना।

[MCP टूल शॉप](https://mcp-tool-shop.github.io/) का हिस्सा - व्यावहारिक डेवलपर उपकरण जो आपके रास्ते में नहीं आते।

## हेडलेस व्हील बिल्डर क्यों?

अधिकांश पायथन बिल्ड टूल `python -m build` पर रुक जाते हैं। हेडलेस व्हील बिल्डर आगे बढ़ता है: अनुमोदन वर्कफ़्लो के साथ ड्राफ्ट रिलीज़, लाइसेंस अनुपालन के साथ निर्भरता विश्लेषण, मल्टी-रिपो समन्वय और रजिस्ट्री प्रकाशन - यह सब एक ही CLI से। यदि आप पायथन पैकेजों के लिए CI/CD पाइपलाइन चलाते हैं, तो यह स्क्रिप्ट के एक संयोजन को एक उपकरण से बदल देता है।

## v0.3.0 में नया क्या है

- **रिलीज़ प्रबंधन**: मल्टी-स्टेज अनुमोदन वर्कफ़्लो के साथ ड्राफ्ट रिलीज़
- **निर्भरता विश्लेषण**: लाइसेंस अनुपालन जांच के साथ पूर्ण निर्भरता ग्राफ
- **CI/CD पाइपलाइन**: बिल्ड-टू-रिलीज़ पाइपलाइन ऑर्केस्ट्रेशन
- **मल्टी-रिपो संचालन**: रिपॉजिटरी में बिल्ड का समन्वय
- **अधिसूचनाएं**: स्लैक, डिस्कॉर्ड और वेबहुक एकीकरण
- **सुरक्षा स्कैनिंग**: SBOM (सॉफ्टवेयर बिल ऑफ मैटेरियल्स) पीढ़ी, लाइसेंस ऑडिट, भेद्यता जांच
- **मेट्रिक्स और एनालिटिक्स**: बिल्ड प्रदर्शन ट्रैकिंग और रिपोर्टिंग
- **आर्टिफैक्ट कैशिंग**: रजिस्ट्री एकीकरण के साथ LRU (लीस्ट रिसेंटली यूज्ड) कैश

## विशेषताएं

### कोर बिल्डिंग
- **कहीं से भी बनाएं**: स्थानीय पथ, गिट URL (शाखा/टैग के साथ), टारबॉल
- **बिल्ड अलगाव**: venv (uv-संचालित, 10-100 गुना तेज) या डॉकर (manylinux/musllinux)
- **मल्टी-प्लेटफॉर्म**: Python 3.10-3.14, Linux/macOS/Windows के लिए बिल्ड मैट्रिक्स
- **पब्लिशिंग**: PyPI विश्वसनीय प्रकाशक (OIDC), DevPi, आर्टिफैक्टरी, S3

### रिलीज़ प्रबंधन
- **ड्राफ्ट रिलीज़**: प्रकाशित करने से पहले रिलीज़ बनाएं, समीक्षा करें और अनुमोदित करें
- **अनुमोदन वर्कफ़्लो**: सरल, दो-स्टेज या एंटरप्राइज़ (QA → सुरक्षा → रिलीज़)
- **रोलबैक समर्थन**: प्रकाशित रिलीज़ को आसानी से वापस करें
- **चेंजलॉग पीढ़ी**: पारंपरिक कमिट से स्वचालित रूप से उत्पन्न करें

### डेवऑप्स और CI/CD
- **पाइपलाइन ऑर्केस्ट्रेशन**: बिल्ड → टेस्ट → रिलीज़ → पब्लिश श्रृंखला बनाएं
- **गिटहब एक्शन जेनरेटर**: अनुकूलित CI वर्कफ़्लो बनाएं
- **मल्टी-रिपो संचालन**: रिपॉजिटरी में रिलीज़ का समन्वय करें
- **आर्टिफैक्ट कैशिंग**: बुद्धिमान कैशिंग के साथ बिल्ड समय कम करें

### विश्लेषण और सुरक्षा
- **निर्भरता ग्राफ**: पैकेज निर्भरताओं को विज़ुअलाइज़ और विश्लेषण करें
- **लाइसेंस अनुपालन**: अनुमत परियोजनाओं में GPL का पता लगाएं, अज्ञात लाइसेंस
- **सुरक्षा स्कैनिंग**: भेद्यता का पता लगाना, SBOM पीढ़ी
- **मेट्रिक्स डैशबोर्ड**: बिल्ड समय, सफलता दर, कैश हिट को ट्रैक करें

### एकीकरण
- **अधिसूचनाएं**: स्लैक, डिस्कॉर्ड, माइक्रोसॉफ्ट टीम्स, कस्टम वेबहुक
- **हेडलेस गिटहब**: रिलीज़, PR (पुल रिक्वेस्ट), इश्यू, वर्कफ़्लो - पूरी तरह से स्क्रिप्ट करने योग्य
- **रजिस्ट्री समर्थन**: PyPI, TestPyPI, निजी रजिस्ट्री, S3

## स्थापना

```bash
# With pip
pip install headless-wheel-builder

# With uv (recommended - faster)
uv pip install headless-wheel-builder

# With all optional dependencies
pip install headless-wheel-builder[all]
```

## शुरुआत कैसे करें

### व्हील बनाएं

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

### रिलीज़ प्रबंधन

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

### निर्भरता विश्लेषण

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

### पाइपलाइन स्वचालन

```bash
# Run a complete build-to-release pipeline
hwb pipeline run my-pipeline.yml

# Execute specific stages
hwb pipeline run my-pipeline.yml --stage build --stage test

# Generate GitHub Actions workflow
hwb actions generate ./my-project --output .github/workflows/ci.yml
```

### अधिसूचनाएं

```bash
# Configure Slack notifications
hwb notify config slack --webhook-url https://hooks.slack.com/...

# Send a build notification
hwb notify send slack "Build completed successfully" --status success

# Test webhook integration
hwb notify test discord
```

### सुरक्षा स्कैनिंग

```bash
# Full security audit
hwb security audit ./my-project

# Generate SBOM
hwb security sbom ./my-project --format cyclonedx

# License compliance check
hwb security licenses ./my-project --policy permissive
```

### मल्टी-रिपो संचालन

```bash
# Build multiple repositories
hwb multirepo build repos.yml

# Sync versions across repos
hwb multirepo sync --version 2.0.0

# Coordinate releases
hwb multirepo release --tag v2.0.0
```

### मेट्रिक्स और एनालिटिक्स

```bash
# Show build metrics
hwb metrics show

# Export metrics for monitoring
hwb metrics export --format prometheus

# Analyze build trends
hwb metrics trends --period 30d
```

### कैश प्रबंधन

```bash
# Show cache statistics
hwb cache stats

# List cached packages
hwb cache list

# Prune old entries
hwb cache prune --max-size 1G
```

## हेडलेस गिटहब संचालन

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

## पायथन एपीआई

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

## कॉन्फ़िगरेशन

`pyproject.toml` में कॉन्फ़िगर करें:

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

## CLI कमांड

| कमांड | विवरण |
| --------- | ------------- |
| `hwb build` | स्रोत से व्हील बनाएं |
| `hwb publish` | PyPI/रजिस्ट्री पर प्रकाशित करें |
| `hwb inspect` | परियोजना कॉन्फ़िगरेशन का विश्लेषण करें |
| `hwb github` | GitHub संचालन (रिलीज़, पुल रिक्वेस्ट, मुद्दे) |
| `hwb release` | प्रारंभिक रिलीज़ प्रबंधन |
| `hwb pipeline` | सीआई/सीडी पाइपलाइन का समन्वय |
| `hwb deps` | निर्भरता ग्राफ विश्लेषण |
| `hwb actions` | GitHub एक्शन जेनरेटर |
| `hwb multirepo` | मल्टी-रिपॉजिटरी संचालन |
| `hwb notify` | अधिसूचना प्रबंधन |
| `hwb security` | सुरक्षा स्कैनिंग |
| `hwb metrics` | बिल्ड मेट्रिक्स और विश्लेषण |
| `hwb cache` | आर्टिफैक्ट कैश प्रबंधन |
| `hwb changelog` | चेंजलॉग जनरेशन |

## आवश्यकताएं

- पायथन 3.10+
- गिट (गिट स्रोत समर्थन के लिए)
- डॉकर (वैकल्पिक, manylinux बिल्ड के लिए)
- यूवी (वैकल्पिक, तेज़ बिल्ड के लिए)

## दस्तावेज़

विस्तृत दस्तावेज़ के लिए [docs/](docs/) निर्देशिका देखें:

- [ROADMAP.md](docs/ROADMAP.md) - विकास चरण और मील के पत्थर
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - सिस्टम डिज़ाइन और घटक
- [API.md](docs/API.md) - सीएलआई और पायथन एपीआई संदर्भ
- [SECURITY.md](docs/SECURITY.md) - सुरक्षा मॉडल और सर्वोत्तम अभ्यास
- [PUBLISHING.md](docs/PUBLISHING.md) - रजिस्ट्री प्रकाशन कार्यप्रवाह
- [ISOLATION.md](docs/ISOLATION.md) - बिल्ड आइसोलेशन रणनीतियाँ
- [VERSIONING.md](docs/VERSIONING.md) - सिमेंटिक वर्जनिंग और चेंजलॉग
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - विकास दिशानिर्देश

## लाइसेंस

एमआईटी लाइसेंस -- विवरण के लिए [LICENSE](LICENSE) देखें।

## योगदान

योगदान का स्वागत है! दिशानिर्देशों के लिए [CONTRIBUTING.md](docs/CONTRIBUTING.md) देखें।
