"""Version lockstep test — every live version surface must agree.

Frozen recorded artifacts (docs/demo-results.json, assets/demo.gif) keep
their recorded 0.1.0 content and are allow-listed, as are the README /
site.json run-record history lines that cite the recorded v0.1.0 demo.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from branchtree import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED = "0.2.0"


def _console_script() -> str | None:
    """The branchtree console script for THIS interpreter, if installed."""
    local = Path(sys.executable).parent / "branchtree"
    if local.is_file():
        return str(local)
    return shutil.which("branchtree")

# Tracked text files allowed to mention the previous version: changelog
# history, frozen/recorded references to the v0.1.0 demo run, and the
# tests that deliberately pin that history (docstrings + changelog assertion).
ALLOWED_010_FILES = {
    "CHANGELOG.md",
    "docs/demo-results.json",
    "web/site.json",
    "README.md",
    "README.en.md",
    "tests/test_cli.py",
    "tests/test_version_consistency.py",
}


def _pyproject_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    assert match is not None
    return match.group(1)


def _site_json_version() -> str:
    data = json.loads((REPO_ROOT / "web" / "site.json").read_text(encoding="utf-8"))
    return data["meta"]["implementation_version"]


class TestVersionLockstep:
    def test_version_file(self):
        assert (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() == EXPECTED

    def test_pyproject_version(self):
        assert _pyproject_version() == EXPECTED

    def test_dunder_version(self):
        assert __version__ == EXPECTED

    def test_site_json_implementation_version(self):
        assert _site_json_version() == EXPECTED

    def test_changelog_has_both_sections(self):
        text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## [0.1.0] - 2026-08-22" in text
        assert f"## [{EXPECTED}] - " in text

    @pytest.mark.skipif(
        _console_script() is None,
        reason="branchtree console script not installed",
    )
    def test_cli_version_flag(self):
        result = subprocess.run(
            [_console_script(), "--version"], capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        assert EXPECTED in result.stdout

    def test_no_other_tracked_file_mentions_previous_version(self):
        tracked = subprocess.run(
            ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert tracked.returncode == 0, tracked.stderr
        offenders = []
        for rel_path in tracked.stdout.splitlines():
            path = REPO_ROOT / rel_path
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, ValueError):
                continue  # binary asset (e.g. the demo gif)
            if "0.1.0" in text and rel_path not in ALLOWED_010_FILES:
                offenders.append(rel_path)
        assert offenders == [], f"stale 0.1.0 references outside the allow-list: {offenders}"
