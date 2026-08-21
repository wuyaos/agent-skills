import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = [
    ROOT / "skills/moviepilot-v2-plugin-dev",
    ROOT / "skills/moviepilot-debug",
]


def frontmatter(text):
    assert text.startswith("---\n")
    raw, body = text[4:].split("\n---\n", 1)
    values = {}
    for line in raw.splitlines():
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values, body


def test_skill_frontmatter_and_progressive_disclosure():
    for directory in SKILLS:
        values, body = frontmatter((directory / "SKILL.md").read_text())
        assert set(values) == {"name", "description"}
        assert re.fullmatch(r"[a-z0-9-]{1,64}", values["name"])
        assert len(values["description"]) <= 1024
        assert values["description"].startswith("Use when")
        assert len(body.split()) < 500
        assert "## Overview" in body and "## Rules" in body and "## Workflow" in body


def test_skill_relative_links_exist():
    link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
    for directory in SKILLS:
        text = (directory / "SKILL.md").read_text()
        for target in link_pattern.findall(text):
            if "://" in target or target.startswith("#"):
                continue
            assert (directory / target).exists(), f"missing {directory.name}/{target}"


def test_all_moviepilot_scripts_have_working_help():
    scripts = [path for directory in SKILLS for path in (directory / "scripts").glob("*.py") if path.name != "common.py"]
    assert scripts
    for script in scripts:
        result = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
        assert result.returncode == 0, f"{script}: {result.stderr}"
        assert "usage:" in result.stdout.lower()


def test_minimal_template_contains_repository_contract_files():
    template = ROOT / "skills/moviepilot-v2-plugin-dev/templates/minimal_v2_plugin"
    assert (template / "AGENTS.md").is_file()
    metadata = json.loads((template / "package.v2.entry.json").read_text())["MyPlugin"]
    assert metadata["version"] == "1.0.0"
    assert list(metadata["history"])[0] == "v1.0.0"
    source = (template / "__init__.py").read_text()
    assert '"text": self._message' in source
