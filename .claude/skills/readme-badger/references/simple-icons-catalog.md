# Simple Icons Catalog — shields.io Badge Reference

Reference for using Simple Icons with shields.io badges. All slugs, hex colors, and usage
patterns verified against Simple Icons v16.10.0 (released 2026-03-01).

SOURCE: [simple-icons/simple-icons](https://github.com/simple-icons/simple-icons) (accessed 2026-03-03)
SOURCE: [shields.io Logos documentation](https://shields.io/docs/logos) (accessed 2026-03-03)
SOURCE: simple-icons/simple-icons `data/simple-icons.json` via GitHub API (accessed 2026-03-03)
SOURCE: simple-icons/simple-icons `slugs.md` via GitHub API (accessed 2026-03-03)

---

## Overview

Simple Icons provides over 3,400 SVG brand icons under the CC0 license. The `logo=` parameter
on shields.io accepts Simple Icons slugs directly. The library is updated continuously; the
[slugs.md](https://github.com/simple-icons/simple-icons/blob/develop/slugs.md) file in the
repo is the authoritative slug reference.

**Stats (v16.10.0, 2026-03-01)**:

- 3,408 icons
- License: CC0-1.0 (public domain)
- GitHub stars: 24,575
- npm package: `simple-icons`

---

## Slug Naming Convention

SOURCE: [CONTRIBUTING.md — Name the Icon](https://github.com/simple-icons/simple-icons/blob/develop/CONTRIBUTING.md) (accessed 2026-03-03)

Slugs are derived from the brand title by applying these rules in order:

1. Convert to **lowercase**
2. Remove all **whitespace**
3. Replace **`+`** with `plus`
4. Replace **`.`** with `dot`
5. Replace **`&`** with `and`
6. Remove all remaining **non-latin, non-alphanumeric characters** (accents become their base letter)
7. When a collision exists, append `_modifier` to disambiguate (e.g., `hive_blockchain`)

Examples:

```text
"Python"        -> python
"C++"           -> cplusplus
"Vue.js"        -> vuedotjs
"Next.js"       -> nextdotjs
"GNU Bash"      -> gnubash
"Hugging Face"  -> huggingface
"GitHub Actions"-> githubactions
"OpenJDK"       -> openjdk
```

The `npm run get-filename -- "Brand name"` command in the repo computes the correct slug
for any brand name.

---

## shields.io Integration

### Basic badge with logo

```text
https://img.shields.io/badge/{label}-{message}-{color}?logo={slug}
```

### With logoColor

```text
https://img.shields.io/badge/{label}-{message}-{color}?logo={slug}&logoColor={color}
```

### Example — Python badge

```text
https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white
```

---

## logoColor Parameter

SOURCE: [shields.io Logos documentation](https://shields.io/docs/logos) (accessed 2026-03-03)

The `logoColor` parameter sets the color of the icon rendered inside the badge. Accepts hex,
rgb, rgba, hsl, hsla, and CSS named colors.

### When to use `logoColor=white`

Use `logoColor=white` when:

- The badge background is **dark** (black, dark gray, brand color) — default icons render in
  their brand color, which may be invisible against a dark background
- The icon's brand color is **black or near-black** (e.g., GitHub `#181717`, Vercel `#000000`,
  Next.js `#000000`, Express `#000000`) — the icon will be invisible on the default dark badge
- The icon's brand color is **very light or white** — invisible on light badge backgrounds

Use the **default** (no `logoColor`) when:

- The badge has a **colored background** that contrasts with the brand color
- The brand color is a **mid-range** color that reads well against both light and dark backgrounds
- You want the icon to display in its official brand color (e.g., Python `#3776AB` on gray)

### Decision guide

```text
Badge background color?
├── Dark / black background  -> logoColor=white
├── Light / white background -> use brand color (default)
└── Colored background       -> test contrast, often logoColor=white works best
```

### Common patterns

```text
# Black background, white icon (GitHub-style)
?logo=github&logoColor=white&color=181717

# Brand-colored background, white icon
?logo=python&logoColor=white&color=3776AB

# Default: icon in brand color on gray
?logo=python
```

---

## Custom SVG Logos

SOURCE: [shields.io Logos documentation](https://shields.io/docs/logos) (accessed 2026-03-03)

For icons not in Simple Icons, pass a base64-encoded SVG via the `logo=` parameter:

```text
logo=data:image/svg+xml;base64,{BASE64_ENCODED_SVG}
```

### Encoding an SVG

```bash
base64 -w 0 icon.svg
```

```python
import base64

with open("icon.svg", "rb") as f:
    encoded = base64.b64encode(f.read()).decode()
print(f"logo=data:image/svg+xml;base64,{encoded}")
```

### Constraints

- URL-encode the data URI if embedding in Markdown image syntax
- SVG must be a single valid XML document
- Large SVGs increase URL length; keep under 2048 characters total for compatibility
- shields.io renders the SVG at 14px height inside the badge

### Example

```text
https://img.shields.io/badge/custom-tool-blue?logo=data:image/svg%2bxml;base64,PHN2Zy...
```

---

## CDN Usage (without shields.io)

Simple Icons provides its own CDN for direct SVG embedding:

```html
<!-- Default brand color -->
<img src="https://cdn.simpleicons.org/{slug}" height="32" />

<!-- Custom color -->
<img src="https://cdn.simpleicons.org/{slug}/{hex}" height="32" />

<!-- Light/dark mode adaptive -->
<img src="https://cdn.simpleicons.org/{slug}/{light-hex}/{dark-hex}" height="32" />
```

---

## Icon Catalog by Category

The `logoColor` column indicates the recommended setting for dark badge backgrounds.

### Languages

All verified against `data/simple-icons.json` v16.10.0.

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| Python | `python` | `#3776AB` | white | `https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white` |
| JavaScript | `javascript` | `#F7DF1E` | black | `https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black` |
| TypeScript | `typescript` | `#3178C6` | white | `https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white` |
| Rust | `rust` | `#000000` | white | `https://img.shields.io/badge/Rust-000000?logo=rust&logoColor=white` |
| Go | `go` | `#00ADD8` | white | `https://img.shields.io/badge/Go-00ADD8?logo=go&logoColor=white` |
| Java (OpenJDK) | `openjdk` | `#000000` | white | `https://img.shields.io/badge/OpenJDK-000000?logo=openjdk&logoColor=white` |
| C | `c` | `#A8B9CC` | black | `https://img.shields.io/badge/C-A8B9CC?logo=c&logoColor=black` |
| C++ | `cplusplus` | `#00599C` | white | `https://img.shields.io/badge/C++-00599C?logo=cplusplus&logoColor=white` |
| Ruby | `ruby` | `#CC342D` | white | `https://img.shields.io/badge/Ruby-CC342D?logo=ruby&logoColor=white` |
| PHP | `php` | `#777BB4` | white | `https://img.shields.io/badge/PHP-777BB4?logo=php&logoColor=white` |
| Swift | `swift` | `#F05138` | white | `https://img.shields.io/badge/Swift-F05138?logo=swift&logoColor=white` |
| Kotlin | `kotlin` | `#7F52FF` | white | `https://img.shields.io/badge/Kotlin-7F52FF?logo=kotlin&logoColor=white` |
| Dart | `dart` | `#0175C2` | white | `https://img.shields.io/badge/Dart-0175C2?logo=dart&logoColor=white` |
| Lua | `lua` | `#000080` | white | `https://img.shields.io/badge/Lua-000080?logo=lua&logoColor=white` |
| Perl | `perl` | `#0073A1` | white | `https://img.shields.io/badge/Perl-0073A1?logo=perl&logoColor=white` |
| Bash | `gnubash` | `#4EAA25` | white | `https://img.shields.io/badge/Bash-4EAA25?logo=gnubash&logoColor=white` |
| PowerShell | — | — | — | **Not in Simple Icons** (Microsoft brand — excluded per project policy) |

Note: The slug for Bash is `gnubash` (GNU Bash), not `bash`. Java uses `openjdk`, not `java`
(Oracle/Java brand excluded per project policy).

### AI / ML

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| Anthropic | `anthropic` | `#191919` | white | `https://img.shields.io/badge/Anthropic-191919?logo=anthropic&logoColor=white` |
| OpenAI | — | — | — | **Not in Simple Icons** (no official entry; only `openaigym` exists) |
| Hugging Face | `huggingface` | `#FFD21E` | black | `https://img.shields.io/badge/HuggingFace-FFD21E?logo=huggingface&logoColor=black` |
| PyTorch | `pytorch` | `#EE4C2C` | white | `https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white` |
| TensorFlow | `tensorflow` | `#FF6F00` | white | `https://img.shields.io/badge/TensorFlow-FF6F00?logo=tensorflow&logoColor=white` |
| LangChain | `langchain` | `#1C3C3C` | white | `https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white` |
| Ollama | `ollama` | `#000000` | white | `https://img.shields.io/badge/Ollama-000000?logo=ollama&logoColor=white` |

Note: For OpenAI badges, use a custom SVG logo via the `logo=data:image/svg+xml;base64,...`
approach (see Custom SVG Logos section above).

### Package Managers

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| npm | `npm` | `#CB3837` | white | `https://img.shields.io/badge/npm-CB3837?logo=npm&logoColor=white` |
| PyPI | `pypi` | `#3775A9` | white | `https://img.shields.io/badge/PyPI-3775A9?logo=pypi&logoColor=white` |
| Cargo (Rust) | — | — | — | **Not in Simple Icons** — use `rust` slug as proxy |
| Homebrew | `homebrew` | `#FBB040` | black | `https://img.shields.io/badge/Homebrew-FBB040?logo=homebrew&logoColor=black` |
| Chocolatey | `chocolatey` | `#80B5E3` | black | `https://img.shields.io/badge/Chocolatey-80B5E3?logo=chocolatey&logoColor=black` |
| uv | — | — | — | **Not in Simple Icons** — use custom SVG or `python` slug |

Note: Cargo has no dedicated Simple Icons entry. For Cargo badges use `logo=rust` or a custom
SVG. The `uv` tool from Astral also has no entry yet.

### CI/CD

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| GitHub Actions | `githubactions` | `#2088FF` | white | `https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white` |
| GitLab CI | `gitlab` | `#FC6D26` | white | `https://img.shields.io/badge/GitLab_CI-FC6D26?logo=gitlab&logoColor=white` |
| CircleCI | `circleci` | `#343434` | white | `https://img.shields.io/badge/CircleCI-343434?logo=circleci&logoColor=white` |
| Jenkins | `jenkins` | `#D24939` | white | `https://img.shields.io/badge/Jenkins-D24939?logo=jenkins&logoColor=white` |
| Travis CI | `travisci` | `#3EAAAF` | white | `https://img.shields.io/badge/Travis_CI-3EAAAF?logo=travisci&logoColor=white` |

### Cloud Platforms

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| Amazon Web Services | — | — | — | **Not in Simple Icons** (Amazon brand — excluded per project policy) |
| Google Cloud | `googlecloud` | `#4285F4` | white | `https://img.shields.io/badge/Google_Cloud-4285F4?logo=googlecloud&logoColor=white` |
| Microsoft Azure | — | — | — | **Not in Simple Icons** (Microsoft brand — excluded per project policy) |
| DigitalOcean | `digitalocean` | `#0080FF` | white | `https://img.shields.io/badge/DigitalOcean-0080FF?logo=digitalocean&logoColor=white` |
| Vercel | `vercel` | `#000000` | white | `https://img.shields.io/badge/Vercel-000000?logo=vercel&logoColor=white` |
| Netlify | `netlify` | `#00C7B7` | white | `https://img.shields.io/badge/Netlify-00C7B7?logo=netlify&logoColor=white` |
| Cloudflare | `cloudflare` | `#F38020` | white | `https://img.shields.io/badge/Cloudflare-F38020?logo=cloudflare&logoColor=white` |
| Heroku | — | — | — | **Not in Simple Icons** (removed; no longer available) |

Note: Amazon/AWS, Microsoft Azure, Windows, and Visual Studio Code are excluded from Simple
Icons because those brands have restrictive trademark policies and have explicitly objected to
inclusion. See CONTRIBUTING.md Forbidden Brands list. Heroku was removed from the library.
For AWS/Azure/Heroku, use custom SVG logos or find community-sourced alternatives.

### Databases

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| PostgreSQL | `postgresql` | `#4169E1` | white | `https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white` |
| MySQL | `mysql` | `#4479A1` | white | `https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white` |
| MongoDB | `mongodb` | `#47A248` | white | `https://img.shields.io/badge/MongoDB-47A248?logo=mongodb&logoColor=white` |
| Redis | `redis` | `#FF4438` | white | `https://img.shields.io/badge/Redis-FF4438?logo=redis&logoColor=white` |
| SQLite | `sqlite` | `#003B57` | white | `https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white` |
| Elasticsearch | `elasticsearch` | `#005571` | white | `https://img.shields.io/badge/Elasticsearch-005571?logo=elasticsearch&logoColor=white` |

### Frameworks

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| React | `react` | `#61DAFB` | black | `https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black` |
| Vue.js | `vuedotjs` | `#4FC08D` | white | `https://img.shields.io/badge/Vue.js-4FC08D?logo=vuedotjs&logoColor=white` |
| Angular | `angular` | `#0F0F11` | white | `https://img.shields.io/badge/Angular-0F0F11?logo=angular&logoColor=white` |
| Next.js | `nextdotjs` | `#000000` | white | `https://img.shields.io/badge/Next.js-000000?logo=nextdotjs&logoColor=white` |
| FastAPI | `fastapi` | `#009688` | white | `https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white` |
| Flask | `flask` | `#3BABC3` | white | `https://img.shields.io/badge/Flask-3BABC3?logo=flask&logoColor=white` |
| Django | `django` | `#092E20` | white | `https://img.shields.io/badge/Django-092E20?logo=django&logoColor=white` |
| Express | `express` | `#000000` | white | `https://img.shields.io/badge/Express-000000?logo=express&logoColor=white` |
| NestJS | `nestjs` | `#E0234E` | white | `https://img.shields.io/badge/NestJS-E0234E?logo=nestjs&logoColor=white` |

Note: React's brand color (`#61DAFB`) is light cyan — use `logoColor=black` on light badges,
`logoColor=white` on dark backgrounds.

### Developer Tools

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| Docker | `docker` | `#2496ED` | white | `https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white` |
| Kubernetes | `kubernetes` | `#326CE5` | white | `https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white` |
| Git | `git` | `#F05032` | white | `https://img.shields.io/badge/Git-F05032?logo=git&logoColor=white` |
| GitHub | `github` | `#181717` | white | `https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white` |
| Linux | `linux` | `#FCC624` | black | `https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black` |
| Apple / macOS | `apple` | `#000000` | white | `https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white` |
| Windows | — | — | — | **Not in Simple Icons** (Microsoft brand — excluded per project policy) |
| Visual Studio Code | — | — | — | **Not in Simple Icons** (Microsoft brand — excluded per project policy) |
| Neovim | `neovim` | `#57A143` | white | `https://img.shields.io/badge/Neovim-57A143?logo=neovim&logoColor=white` |
| tmux | `tmux` | `#1BB91F` | white | `https://img.shields.io/badge/tmux-1BB91F?logo=tmux&logoColor=white` |

### Testing

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| pytest | `pytest` | `#0A9EDC` | white | `https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white` |
| Jest | `jest` | `#C21325` | white | `https://img.shields.io/badge/Jest-C21325?logo=jest&logoColor=white` |
| Selenium | `selenium` | `#43B02A` | white | `https://img.shields.io/badge/Selenium-43B02A?logo=selenium&logoColor=white` |
| Cypress | `cypress` | `#69D3A7` | black | `https://img.shields.io/badge/Cypress-69D3A7?logo=cypress&logoColor=black` |
| Playwright | — | — | — | **Not in Simple Icons** (Microsoft brand — excluded per project policy) |

Note: The slug for pytest is `pytest` (capitalized title "Pytest" in the data, slug is
`pytest`). Playwright is a Microsoft product and is explicitly excluded from Simple Icons.

### Linting / Code Quality

| Icon | Slug | Hex | logoColor | Sample Badge URL |
| :--- | :--- | :--- | :--- | :--- |
| ESLint | `eslint` | `#4B32C3` | white | `https://img.shields.io/badge/ESLint-4B32C3?logo=eslint&logoColor=white` |
| Prettier | `prettier` | `#F7B93E` | black | `https://img.shields.io/badge/Prettier-F7B93E?logo=prettier&logoColor=black` |
| SonarQube | — | — | — | Split into three slugs — see below |
| Codecov | `codecov` | `#F01F7A` | white | `https://img.shields.io/badge/Codecov-F01F7A?logo=codecov&logoColor=white` |

**SonarQube variants** (v16.10.0 rebranding):

| Variant | Slug | Hex | Sample Badge URL |
| :--- | :--- | :--- | :--- |
| SonarQube Cloud (SonarCloud) | `sonarqubecloud` | `#126ED3` | `https://img.shields.io/badge/SonarQube_Cloud-126ED3?logo=sonarqubecloud&logoColor=white` |
| SonarQube Server (self-hosted) | `sonarqubeserver` | `#126ED3` | `https://img.shields.io/badge/SonarQube_Server-126ED3?logo=sonarqubeserver&logoColor=white` |
| SonarQube for IDE | `sonarqubeforide` | `#126ED3` | `https://img.shields.io/badge/SonarQube_IDE-126ED3?logo=sonarqubeforide&logoColor=white` |

The generic `sonarqube` slug does not exist in v16.10.0. Use `sonarqubecloud` for the most
common cloud-hosted variant.

---

## Forbidden / Missing Brands

The following brands requested in the original spec are **not available** in Simple Icons,
with reasons sourced from CONTRIBUTING.md:

SOURCE: [CONTRIBUTING.md — Forbidden Brands](https://github.com/simple-icons/simple-icons/blob/develop/CONTRIBUTING.md#forbidden-brands) (accessed 2026-03-03)

| Brand | Reason |
| :--- | :--- |
| Amazon / AWS (`amazonaws`) | Amazon brand — explicitly forbidden per project policy |
| Microsoft Azure (`microsoftazure`) | Microsoft brand — explicitly forbidden per project policy |
| Windows (`windows`) | Microsoft brand — explicitly forbidden per project policy |
| Visual Studio Code (`visualstudiocode`) | Microsoft brand — explicitly forbidden per project policy |
| Playwright (`playwright`) | Microsoft brand — explicitly forbidden per project policy |
| PowerShell (`powershell`) | Microsoft brand — explicitly forbidden per project policy |
| OpenAI (`openai`) | Not present; only `openaigym` exists (OpenAI Gym, a different product) |
| Heroku (`heroku`) | Not present in v16.10.0; was removed from the library |
| Cargo (`cargo`) | Not present; use `rust` slug as functional equivalent |
| uv (`uv`) | Not present; package is too new for inclusion threshold |

For these brands, the alternatives are:

1. Use a related icon (e.g., `rust` for Cargo, `python` for uv)
2. Use a custom SVG via `logo=data:image/svg+xml;base64,...`
3. Use shields.io's built-in named logos if available (separate from Simple Icons)

---

## shields.io Update Lag

SOURCE: [shields.io GitHub discussion #5369](https://github.com/badges/shields/discussions/5369) (accessed 2026-03-03)

shields.io does not immediately pull new Simple Icons releases. There is a lag between when
an icon appears in Simple Icons and when it becomes available on `img.shields.io`. The
`slugs.md` file may list icons that shields.io does not yet support. If a badge shows a
missing icon, either wait for the next shields.io update cycle or use the CDN approach:

```html
<!-- Direct from Simple Icons CDN — always current -->
<img src="https://cdn.simpleicons.org/{slug}" height="14" />
```

---

## Freshness Tracking

- **Data version**: Simple Icons v16.10.0
- **Data date**: 2026-03-01 (release date)
- **Catalog created**: 2026-03-03
- **Next review**: 2026-06-03
- **Review trigger**: New Simple Icons major version, or new icons requested for badge skill

To refresh hex colors, re-query:

```bash
gh api "repos/simple-icons/simple-icons/contents/data/simple-icons.json" \
  --jq '.content' | base64 -d | python3 -c "
import json, sys
icons = json.load(sys.stdin)
for icon in icons:
    slug = icon.get('slug', icon['title'].lower().replace(' ', ''))
    print(f'{icon[\"title\"]}|{slug}|{icon[\"hex\"]}')
" | grep -i "TARGET_NAME"
```
