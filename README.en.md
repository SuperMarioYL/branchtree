<div align="right"><sub><b>English</b> | <a href="./README.md">简体中文</a></sub></div>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/hero-light.svg">
  <img src="./assets/hero-light.svg" width="880" alt="BranchTree — treat your story as a tree, not a sheet">
</picture>

<p align="center"><sub>BranchTree is the branchable story-tree agent that locks cross-chapter consistency for serialized fiction writers. Runs locally.</sub></p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
  <a href="https://github.com/SuperMarioYL/branchtree/releases"><img src="https://img.shields.io/github/v/release/SuperMarioYL/branchtree" alt="Release"></a>
  <a href="https://github.com/SuperMarioYL/branchtree/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/SuperMarioYL/branchtree/ci.yml?branch=main&label=CI" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python">
</p>

**At chapter 200 your character's eye color contradicts chapter 12? Treat the story as a tree — branch an alternate take, lock character facts, and consistency holds across the whole serial.**

<h2><img src="https://api.iconify.design/tabler:topology-star-3.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Architecture</h2>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/atlas-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/atlas-light.svg">
  <img src="./assets/atlas-light.svg" width="880" alt="Architecture: CLI → Core → LLM Adapter / HTML Renderer">
</picture>

A single-process CLI — no microservices, no running server. CLI (typer) calls Core (pydantic, pure logic), which owns the story tree, state, and consistency checker. The LLM adapter talks openai-compat endpoints (DeepSeek/Doubao/Kimi), and the renderer produces static HTML via jinja2.

## Table of Contents

- [Why BranchTree](#why-branchtree)
- [Install & Quickstart](#install--quickstart)
- [Usage](#usage)
- [Demo](#demo)
- [Configuration](#configuration)
- [Roadmap](#roadmap)
- [Pricing](#pricing)
- [License](#license)

## Why BranchTree

At 200,000 words a serialized author hits consistency collapse: a character's eye color in chapter 12 contradicts chapter 180; a foreshadow from chapter 30 is forgotten by chapter 200; readers cite "setting collapse" as their drop reason. Generic LLM chat has no persistent narrative state — every chapter means re-pasting context, and writing an alternate take overwrites the old version. BranchTree persists narrative state as a branchable project file: when you regenerate, locks enforce immutable facts, and consistency holds across a million words.

<h2><img src="https://api.iconify.design/tabler:rocket.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Install & Quickstart</h2>

```bash
git clone https://github.com/SuperMarioYL/branchtree.git && cd branchtree
uv tool install -e .
cd examples/demo-serial && branchtree view   # opens a 30-chapter tree view in your browser
```

<details>
<summary>Sample output</summary>

```
Rendered tree view → demo-serial.tree/tree.html
Open in browser: file:///.../demo-serial.tree/tree.html
```

The browser shows 30 main-line chapters + a 3-chapter alt-take branch, plus character locks (Lin Wan: left-hand scar, hates her brother).

</details>

<h2><img src="https://api.iconify.design/tabler:terminal-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Usage</h2>

**Create a story tree and add chapters:**

```bash
branchtree new myserial
branchtree add --text "Chapter 1 Lin Wan opened her eyes; the old scar on her left hand ached."
branchtree add --file ch02.txt
```

**Lock character facts (immutable across regeneration):**

```bash
branchtree lock add character:林晚 --facts "left-hand scar;hates her brother"
branchtree lock list
```

**Branch an alternate take and merge the best version:**

```bash
branchtree branch --from ch12 --name alt-take
branchtree add --text "Lin Wan strikes first." --branch alt-take
branchtree view                    # main line and alt-take shown side by side
branchtree merge --branch alt-take --into main
```

**Cross-chapter consistency check:**

```bash
branchtree consistency   # detects setting collapse, reports violation points
```

<h2><img src="https://api.iconify.design/tabler:photo.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Demo</h2>

![demo](assets/demo.gif)

Running branch + merge + view on the 30-chapter demo serial — branch structure and lock status visualized in static HTML.

<h2><img src="https://api.iconify.design/tabler:adjustments.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Configuration</h2>

LLM features (regenerate / deep state extraction, m2 milestone) are configured via environment variables:

| Variable | Description | Default |
|---|---|---|
| `OPENAI_BASE_URL` | openai-compat endpoint (DeepSeek/Doubao/Kimi) | none |
| `OPENAI_API_KEY` | API key | none |
| `BRANCHTREE_MODEL` | Model name | `deepseek-chat` |

m1 does not require an LLM — story-tree persistence, branching, merging, and the static HTML view all run locally.

<h2><img src="https://api.iconify.design/tabler:map-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Roadmap</h2>

- [x] **m1 Story-tree primitive** — branchable story tree on disk + static HTML view (no LLM)
- [ ] **m2 In-loop control** — regenerate-this-branch + lock-character consistency check, demoable on the 30-chapter serial
- [ ] **m3 Install-and-go** — uv/pipx 10-minute install + bilingual README + demo GIF, reproducible by a stranger

Future: hosted cloud sync (cross-device editing + million-word consistency graph), studio co-writing with shared branches/locks.

<h2><img src="https://api.iconify.design/tabler:credit-card.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Pricing</h2>

v0.1 is entirely free, local, and open-source (MIT) — no paywall. Future hosted tiers:

| Plan | Price | Features |
|---|---|---|
| Personal hosted | ¥19/mo | Cloud-synced story tree + cross-device editing + million-word consistency graph |
| Studio | ¥99/mo/seat | Shared branch/lock co-writing, 5 seats minimum |

Paid features launch after m3 ships and the 30-day kill-gate passes. The local OSS version stays free forever.

## License

[MIT](./LICENSE) © 2026 SuperMarioYL. Feel free to open bug reports or feature requests in [GitHub Issues](https://github.com/SuperMarioYL/branchtree/issues).

<p align="center"><sub><a href="./LICENSE">MIT</a> © 2026 SuperMarioYL</sub></p>
