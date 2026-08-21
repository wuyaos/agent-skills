#!/usr/bin/env python3
"""Deterministic MoviePilot plugin contract validator.

Read-only. Emits a stable JSON report and exits 1 when any required check fails.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class Report:
    def __init__(self, plugin: str):
        self.plugin = plugin
        self.checks: list[dict[str, Any]] = []

    def add(self, check_id: str, status: str, evidence: Any = None):
        item = {"id": check_id, "status": status}
        if evidence not in (None, "", [], {}):
            item["evidence"] = evidence
        self.checks.append(item)

    @property
    def ok(self) -> bool:
        return not any(item["status"] == "fail" for item in self.checks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "plugin": self.plugin,
            "checks": self.checks,
            "errors": [item for item in self.checks if item["status"] == "fail"],
            "warnings": [item for item in self.checks if item["status"] == "warn"],
        }


def _literal_assignments(class_node: ast.ClassDef) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for node in class_node.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        for target in targets:
            if isinstance(target, ast.Name):
                try:
                    values[target.id] = ast.literal_eval(value_node)
                except (ValueError, TypeError):
                    pass
    return values


def _inherits_plugin_base(class_node: ast.ClassDef) -> bool:
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id == "_PluginBase":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "_PluginBase":
            return True
    return False


def _find_entry_class(tree: ast.Module, class_name: str | None) -> ast.ClassDef | None:
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if class_name:
        return next((node for node in classes if node.name == class_name), None)
    return next((node for node in classes if _inherits_plugin_base(node)), None)


def _dict_string_value(node: ast.Dict, key_name: str) -> list[str]:
    values = []
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and key.value == key_name and isinstance(value, ast.Constant) and isinstance(value.value, str):
            values.append(value.value)
    return values


def _model_and_prop_violations(tree: ast.AST) -> tuple[list[str], list[str]]:
    nested_models: list[str] = []
    camel_props: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for model in _dict_string_value(node, "model"):
            if "." in model or "[" in model or "]" in model:
                nested_models.append(model)
        for key, value in zip(node.keys, node.values):
            if not (isinstance(key, ast.Constant) and key.value == "props" and isinstance(value, ast.Dict)):
                continue
            for prop_key in value.keys:
                if isinstance(prop_key, ast.Constant) and isinstance(prop_key.value, str) and re.search(r"[A-Z]", prop_key.value):
                    camel_props.append(prop_key.value)
    return sorted(set(nested_models)), sorted(set(camel_props))


def _api_paths(tree: ast.Module, class_node: ast.ClassDef) -> list[str]:
    method = next((node for node in class_node.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "get_api"), None)
    if not method:
        return []
    return sorted({node.value for node in ast.walk(method) if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/")})


def _secret_literal_hits(plugin_dir: Path) -> list[str]:
    patterns = [
        re.compile(r"X-API-KEY\s*[:=]\s*[A-Za-z0-9_-]{16,}", re.I),
        re.compile(r"__Host-[A-Za-z0-9_-]+=[A-Za-z0-9._~+/%-]{16,}"),
        re.compile(r"Authorization\s*[:=]\s*Bearer\s+[A-Za-z0-9._~-]{20,}", re.I),
    ]
    hits: list[str] = []
    for path in plugin_dir.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".md", ".json", ".yaml", ".yml"} or "tests" in path.parts:
            continue
        text = path.read_text(errors="ignore")
        if any(pattern.search(text) for pattern in patterns):
            hits.append(str(path.relative_to(plugin_dir)))
    return sorted(hits)


def validate(repo: Path, plugin: str, class_name: str | None = None, run_pyflakes: bool = False) -> Report:
    report = Report(plugin)
    repo = repo.resolve()
    plugin_dir = repo / "plugins.v2" / plugin
    init_path = plugin_dir / "__init__.py"
    package_path = repo / "package.v2.json"

    report.add("plugin-directory", "pass" if plugin_dir.is_dir() else "fail", str(plugin_dir))
    report.add("lowercase-directory", "pass" if re.fullmatch(r"[a-z0-9_-]+", plugin) else "fail", plugin)
    report.add("entry-file", "pass" if init_path.is_file() else "fail", str(init_path))
    report.add("agents-file", "pass" if (plugin_dir / "AGENTS.md").is_file() else "fail", str(plugin_dir / "AGENTS.md"))
    report.add("package-file", "pass" if package_path.is_file() else "fail", str(package_path))
    if not init_path.is_file() or not package_path.is_file():
        return report

    syntax_errors: list[str] = []
    trees: dict[Path, ast.Module] = {}
    for path in sorted(plugin_dir.rglob("*.py")):
        try:
            trees[path] = ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as error:
            syntax_errors.append(f"{path.relative_to(repo)}:{error.lineno}:{error.msg}")
    report.add("python-ast", "pass" if not syntax_errors else "fail", syntax_errors or f"{len(trees)} files")
    if init_path not in trees:
        return report

    tree = trees[init_path]
    entry_class = _find_entry_class(tree, class_name)
    report.add("entry-class", "pass" if entry_class else "fail", class_name or "auto-detect _PluginBase")
    if not entry_class:
        return report
    class_name = entry_class.name
    metadata = _literal_assignments(entry_class)
    methods = {node.name for node in entry_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    required_methods = {"init_plugin", "get_state", "get_api", "get_form", "get_page", "stop_service"}
    missing_methods = sorted(required_methods - methods)
    report.add("plugin-methods", "pass" if not missing_methods else "fail", {"missing": missing_methods} if missing_methods else sorted(required_methods))
    report.add("enabled-default", "pass" if metadata.get("_enabled") is False else "warn", metadata.get("_enabled", "not-literal"))

    try:
        package = json.loads(package_path.read_text())
    except (json.JSONDecodeError, OSError) as error:
        report.add("package-json", "fail", str(error))
        return report
    report.add("package-json", "pass")
    package_entry = package.get(class_name)
    if package_entry is None and not class_name:
        package_entry = next((value for key, value in package.items() if key.lower() == plugin.lower()), None)
    report.add("package-entry", "pass" if isinstance(package_entry, dict) else "fail", class_name)
    if isinstance(package_entry, dict):
        code_version = metadata.get("plugin_version")
        package_version = package_entry.get("version")
        report.add("version-sync", "pass" if code_version and code_version == package_version else "fail", {"code": code_version, "package": package_version})
        history = package_entry.get("history") or {}
        history_keys = list(history) if isinstance(history, dict) else []
        expected_history = f"v{package_version}" if package_version else ""
        report.add("history-latest", "pass" if history_keys and history_keys[0] == expected_history else "fail", {"expected": expected_history, "first": history_keys[0] if history_keys else None})
        required_package = {"name", "description", "labels", "version", "icon", "author", "level", "history"}
        missing_package = sorted(required_package - set(package_entry))
        report.add("package-fields", "pass" if not missing_package else "fail", {"missing": missing_package} if missing_package else sorted(required_package))

    nested_models: list[str] = []
    camel_props: list[str] = []
    for parsed_tree in trees.values():
        nested, camel = _model_and_prop_violations(parsed_tree)
        nested_models.extend(nested)
        camel_props.extend(camel)
    report.add("flat-form-models", "pass" if not nested_models else "fail", sorted(set(nested_models)))
    report.add("kebab-case-props", "pass" if not camel_props else "warn", sorted(set(camel_props)))

    paths = _api_paths(tree, entry_class)
    duplicate_prefix = [path for path in paths if path == f"/{class_name}" or path.startswith(f"/{class_name}/")]
    report.add("api-relative-paths", "pass" if not duplicate_prefix else "fail", duplicate_prefix or paths)

    secret_hits = _secret_literal_hits(plugin_dir)
    report.add("secret-literals", "pass" if not secret_hits else "fail", secret_hits)

    git = shutil.which("git")
    if git and (repo / ".git").exists():
        command = [git, "-C", str(repo), "diff", "--check", "--", str(plugin_dir.relative_to(repo)), "package.v2.json"]
        result = subprocess.run(command, capture_output=True, text=True)
        report.add("git-diff-check", "pass" if result.returncode == 0 else "fail", result.stdout.strip() or result.stderr.strip())
    else:
        report.add("git-diff-check", "skip", "git repository unavailable")

    if run_pyflakes:
        pyflakes = shutil.which("pyflakes")
        if not pyflakes:
            report.add("pyflakes", "skip", "pyflakes unavailable")
        else:
            files = [str(path) for path in sorted(plugin_dir.rglob("*.py"))]
            result = subprocess.run([pyflakes, *files], capture_output=True, text=True)
            report.add("pyflakes", "pass" if result.returncode == 0 else "fail", (result.stdout + result.stderr).strip())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one MoviePilot plugin deterministically.")
    parser.add_argument("--repo", default=".", help="MoviePilot-Plugins repository root")
    parser.add_argument("--plugin", required=True, help="Lowercase plugins.v2 directory name")
    parser.add_argument("--class-name", help="Plugin class/package key; auto-detected by default")
    parser.add_argument("--pyflakes", action="store_true", help="Run pyflakes when installed")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    report = validate(Path(args.repo), args.plugin, args.class_name, args.pyflakes)
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
