#!/usr/bin/env python3
"""Safely synchronize MoviePilot plugin version and package history.

Dry-run by default. Use --apply for an atomic best-effort two-file update.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

VERSION_RE = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")
PLUGIN_VERSION_RE = re.compile(r"(?m)^(?P<indent>\s*)plugin_version\s*=\s*(?P<quote>['\"])(?P<version>[^'\"]+)(?P=quote)\s*$")


def _atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def build_update(repo: Path, plugin: str, class_name: str, version: str, history_text: str) -> dict[str, Any]:
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"invalid semantic version: {version}")
    if not history_text.strip():
        raise ValueError("history text must not be empty")
    repo = repo.resolve()
    init_path = repo / "plugins.v2" / plugin / "__init__.py"
    package_path = repo / "package.v2.json"
    if not init_path.is_file() or not package_path.is_file():
        raise FileNotFoundError("plugin __init__.py or package.v2.json not found")

    init_before = init_path.read_text()
    matches = list(PLUGIN_VERSION_RE.finditer(init_before))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one plugin_version assignment, found {len(matches)}")
    current_code_version = matches[0].group("version")
    init_after = PLUGIN_VERSION_RE.sub(
        lambda match: f"{match.group('indent')}plugin_version = {match.group('quote')}{version}{match.group('quote')}",
        init_before,
        count=1,
    )

    package = json.loads(package_path.read_text())
    entry = package.get(class_name)
    if not isinstance(entry, dict):
        raise KeyError(f"package entry not found: {class_name}")
    current_package_version = entry.get("version")
    history = entry.get("history")
    if not isinstance(history, dict):
        raise ValueError("package history must be an object")
    history_key = f"v{version}"
    if history_key in history and history[history_key] != history_text:
        raise ValueError(f"history entry already exists with different text: {history_key}")

    entry["version"] = version
    entry["history"] = {history_key: history_text.strip(), **{key: value for key, value in history.items() if key != history_key}}
    package_after = json.dumps(package, ensure_ascii=False, indent=4) + "\n"

    # Validate generated artifacts before exposing them to the caller.
    compile(init_after, str(init_path), "exec")
    generated = json.loads(package_after)
    generated_entry = generated[class_name]
    if generated_entry["version"] != version or next(iter(generated_entry["history"]), None) != history_key:
        raise ValueError("generated metadata failed validation")

    return {
        "repo": repo,
        "plugin": plugin,
        "class_name": class_name,
        "version": version,
        "current_code_version": current_code_version,
        "current_package_version": current_package_version,
        "history_key": history_key,
        "changed": init_after != init_before or package_after != package_path.read_text(),
        "init_path": init_path,
        "package_path": package_path,
        "init_before": init_before,
        "init_after": init_after,
        "package_before": package_path.read_text(),
        "package_after": package_after,
    }


def apply_update(plan: dict[str, Any]):
    init_path: Path = plan["init_path"]
    package_path: Path = plan["package_path"]
    init_before = plan["init_before"]
    package_before = plan["package_before"]
    try:
        _atomic_write(init_path, plan["init_after"])
        _atomic_write(package_path, plan["package_after"])
        compile(init_path.read_text(), str(init_path), "exec")
        package = json.loads(package_path.read_text())
        entry = package[plan["class_name"]]
        assert entry["version"] == plan["version"]
        assert next(iter(entry["history"])) == plan["history_key"]
    except Exception:
        _atomic_write(init_path, init_before)
        _atomic_write(package_path, package_before)
        raise


def public_plan(plan: dict[str, Any], applied: bool) -> dict[str, Any]:
    return {
        "ok": True,
        "applied": applied,
        "changed": plan["changed"],
        "plugin": plan["plugin"],
        "class_name": plan["class_name"],
        "current": {
            "code_version": plan["current_code_version"],
            "package_version": plan["current_package_version"],
        },
        "target": {
            "version": plan["version"],
            "history_key": plan["history_key"],
        },
        "files": [
            str(plan["init_path"].relative_to(plan["repo"])),
            str(plan["package_path"].relative_to(plan["repo"])),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize plugin_version and package.v2.json safely.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--plugin", required=True, help="Lowercase plugins.v2 directory")
    parser.add_argument("--class-name", required=True, help="package.v2.json key / plugin class")
    parser.add_argument("--version", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--apply", action="store_true", help="Write changes; default is dry-run")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        plan = build_update(Path(args.repo), args.plugin, args.class_name, args.version, args.history)
        if args.apply and plan["changed"]:
            apply_update(plan)
        print(json.dumps(public_plan(plan, args.apply), ensure_ascii=False, indent=2 if args.pretty else None))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
