# Changelog

All notable changes to BranchTree are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-09-13

### Fixed

- CLI error contract: `add` with a missing or non-UTF-8 `--file`, an unknown
  `--branch`, a corrupt or missing `tree.json`, or an invalid lock `--scope`
  now prints one clean error line and exits 1 instead of dumping a raw
  traceback (`FileNotFoundError`, `UnicodeDecodeError`, `ValueError`,
  pydantic `ValidationError`).
- `branchtree new` no longer silently destroys an existing story tree: it
  refuses with exit 1 and requires the new `--force` flag to overwrite.
  Names with path separators (e.g. `a/b`) or empty names are rejected —
  they previously created trees the CLI could never discover.
- `branchtree consistency` now exits 1 when violations are found (and 0
  when clean), so scripts can gate on the result. Previously it always
  exited 0.
- A cyclic parent chain in a hand-edited `tree.json` no longer hangs
  `branchtree view` forever: `StoryTree.branch_path` detects the cycle and
  raises a `ValueError` the CLI reports cleanly.

### Added

- `branchtree regenerate` is implemented: it rewrites a branch tip through
  an openai-compatible endpoint (`OPENAI_BASE_URL` / `OPENAI_API_KEY` /
  model via the adapter), renders the existing `prompts.py` contract, and
  post-checks the output against every applicable lock's pinned facts —
  an explicit contradiction refuses the write and leaves the tree
  untouched.
- `branchtree --version` prints the version.

### Changed

- Version surfaces (VERSION, pyproject.toml, `branchtree.__version__`,
  web/site.json `implementation_version`) are lockstepped at 0.2.0 and
  covered by a version-consistency test; CHANGELOG.md added.

## [0.1.0] - 2026-08-22

### Added

- The branchable story-tree primitive: `new` / `add` / `branch` / `merge`
  with parent-chained chapter nodes, named branches and JSON persistence.
- Fact locks (`lock add` / `lock list`) and the rule-based cross-chapter
  consistency checker (`consistency`) for explicit Chinese negation
  patterns.
- Static self-contained HTML tree view (`view`) with dark-mode support.
- Bilingual README (zh + en), 30-chapter demo-serial fixture, recorded
  demo run and capture.
