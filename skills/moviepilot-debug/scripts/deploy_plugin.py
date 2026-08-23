#!/usr/bin/env python3
"""Plan and apply a constrained MoviePilot plugin deployment over SSH.

Dry-run by default. Production files only; tests and caches are excluded.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from common import api_request, extract_form_model, load_api_key, normalize_base_url, print_json, redact_text

SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
SAFE_COMMAND = re.compile(r"^(?:[A-Za-z0-9_.-]+|/[A-Za-z0-9_./-]+)$")
EXCLUDED_PARTS = {
    "tests", "__pycache__", ".git", ".pytest_cache", ".mypy_cache",
    ".omc", ".ralph", ".pi", ".agents", ".idea", ".vscode",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def _validate_target(plugin: str, host: str, container: str, docker_bin: str, remote_root: str):
    if not re.fullmatch(r"[a-z0-9_-]+", plugin):
        raise ValueError("plugin directory must be lowercase and path-safe")
    if not SAFE_NAME.fullmatch(host) or not SAFE_NAME.fullmatch(container):
        raise ValueError("unsafe ssh host or container name")
    if not SAFE_COMMAND.fullmatch(docker_bin):
        raise ValueError("unsafe docker command")
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", remote_root) or ".." in PurePosixPath(remote_root).parts:
        raise ValueError("unsafe remote root")


def _is_excluded_manifest_path(relative: PurePosixPath | Path) -> bool:
    """Use one exclusion policy for local source and remote runtime manifests."""
    return bool(
        EXCLUDED_PARTS.intersection(relative.parts)
        or any(part.startswith(".") for part in relative.parts)
        or relative.suffix in EXCLUDED_SUFFIXES
    )


def source_manifest(plugin_dir: Path) -> list[str]:
    files: list[str] = []
    for path in plugin_dir.rglob("*"):
        relative = path.relative_to(plugin_dir)
        if not path.is_file() or _is_excluded_manifest_path(relative):
            continue
        files.append(relative.as_posix())
    return sorted(files)


def _run_ssh(host: str, command: str, timeout: int = 40) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", host, command], capture_output=True, text=True, timeout=timeout)


def remote_manifest(host: str, container: str, docker_bin: str, target: str) -> list[str]:
    inner = f"if [ -d {shlex.quote(target)} ]; then cd {shlex.quote(target)} && find . -type f | sed 's#^./##' | sort; fi"
    command = f"{shlex.quote(docker_bin)} exec {shlex.quote(container)} sh -c {shlex.quote(inner)}"
    result = _run_ssh(host, command)
    if result.returncode != 0:
        raise RuntimeError(redact_text(result.stderr.strip() or "remote manifest failed"))
    files = []
    for line in result.stdout.splitlines():
        relative_text = line.strip()
        if not relative_text:
            continue
        relative = PurePosixPath(relative_text)
        if _is_excluded_manifest_path(relative):
            continue
        files.append(relative.as_posix())
    return sorted(files)


def build_plan(source: list[str], remote: list[str]) -> dict[str, Any]:
    source_set, remote_set = set(source), set(remote)
    return {
        "source_count": len(source),
        "remote_count": len(remote),
        "add": sorted(source_set - remote_set),
        "overwrite": sorted(source_set & remote_set),
        "delete_stale": sorted(remote_set - source_set),
    }


def _build_archive(plugin_dir: Path, manifest: list[str]) -> Path:
    handle = tempfile.NamedTemporaryFile(prefix=f"{plugin_dir.name}-", suffix=".tgz", delete=False)
    handle.close()
    archive = Path(handle.name)
    with tarfile.open(archive, "w:gz") as tar:
        for relative in manifest:
            tar.add(plugin_dir / relative, arcname=relative, recursive=False)
    return archive


def _assert_no_onlyonce(base_url: str | None, api_key_file: str | None, plugin_id: str) -> dict[str, Any]:
    if not base_url and not api_key_file and not os.environ.get("MP_API_KEY"):
        raise ValueError("deployment apply requires MoviePilot API credentials to guard onlyonce")
    base = normalize_base_url(base_url)
    key = load_api_key(api_key_file)
    path = f"/api/v1/plugin/form/{plugin_id}"
    status, body = api_request(base, path, key)
    if status == 404:
        return {"checked": False, "reason": "plugin form not registered yet"}
    if not 200 <= status < 300:
        raise RuntimeError(f"cannot inspect plugin config before reload: HTTP {status}")
    model = extract_form_model(body)
    if model.get("onlyonce") is True:
        raise RuntimeError("reload blocked: remote onlyonce=true may trigger a business action")
    return {"checked": True, "enabled": model.get("enabled"), "onlyonce": model.get("onlyonce")}


def apply_deployment(args, plugin_dir: Path, manifest: list[str], plan: dict[str, Any], target: str):
    if plan["delete_stale"] and not args.allow_delete_stale:
        raise RuntimeError("stale remote files require --allow-delete-stale")
    archive = _build_archive(plugin_dir, manifest)
    remote_archive = f"/tmp/{plugin_dir.name}-skill-deploy.tgz"
    container_archive = remote_archive
    try:
        upload = subprocess.run(["scp", str(archive), f"{args.ssh_host}:{remote_archive}"], capture_output=True, text=True, timeout=60)
        if upload.returncode != 0:
            raise RuntimeError(redact_text(upload.stderr.strip() or "scp failed"))
        commands = [
            f"{shlex.quote(args.docker_bin)} exec {shlex.quote(args.container)} mkdir -p {shlex.quote(target)}",
            f"{shlex.quote(args.docker_bin)} cp {shlex.quote(remote_archive)} {shlex.quote(args.container)}:{shlex.quote(container_archive)}",
            f"{shlex.quote(args.docker_bin)} exec {shlex.quote(args.container)} tar xzf {shlex.quote(container_archive)} -C {shlex.quote(target)}",
        ]
        if plan["delete_stale"]:
            stale_paths = [f"{target}/{relative}" for relative in plan["delete_stale"]]
            commands.append(
                f"{shlex.quote(args.docker_bin)} exec {shlex.quote(args.container)} rm -f "
                + " ".join(shlex.quote(path) for path in stale_paths)
            )
        commands.extend([
            f"{shlex.quote(args.docker_bin)} exec {shlex.quote(args.container)} rm -f {shlex.quote(container_archive)}",
            f"rm -f {shlex.quote(remote_archive)}",
        ])
        result = _run_ssh(args.ssh_host, " && ".join(commands), timeout=90)
        if result.returncode != 0:
            raise RuntimeError(redact_text(result.stderr.strip() or "remote deployment failed"))
    finally:
        archive.unlink(missing_ok=True)


def run(args) -> dict[str, Any]:
    repo = Path(args.repo).resolve()
    plugin_dir = repo / "plugins.v2" / args.plugin
    if not (plugin_dir / "__init__.py").is_file():
        raise FileNotFoundError(f"plugin entry not found: {plugin_dir / '__init__.py'}")
    _validate_target(args.plugin, args.ssh_host, args.container, args.docker_bin, args.remote_root)
    # Deterministic local syntax gate before any remote write.
    for path in plugin_dir.rglob("*.py"):
        if "tests" not in path.relative_to(plugin_dir).parts:
            compile(path.read_text(), str(path), "exec")
    validator = Path(__file__).resolve().parents[2] / "moviepilot-v2-plugin-dev/scripts/validate_plugin.py"
    validation = None
    if validator.is_file():
        checked = subprocess.run(
            [sys.executable, str(validator), "--repo", str(repo), "--plugin", args.plugin, "--class-name", args.class_name],
            capture_output=True, text=True,
        )
        try:
            validation = json.loads(checked.stdout)
        except Exception as error:
            raise RuntimeError(f"local validator returned invalid output: {error}") from error
        if checked.returncode != 0 or not validation.get("ok"):
            failed = [item.get("id") for item in validation.get("errors", [])]
            raise RuntimeError(f"local plugin validation failed: {', '.join(failed)}")

    source = source_manifest(plugin_dir)
    target = f"{args.remote_root.rstrip('/')}/{args.plugin}"
    remote = remote_manifest(args.ssh_host, args.container, args.docker_bin, target)
    plan = build_plan(source, remote)
    reload_guard = None
    if args.apply or args.reload:
        reload_guard = _assert_no_onlyonce(args.base_url, args.api_key_file, args.class_name)

    result = {
        "ok": True,
        "applied": False,
        "mode": "apply" if args.apply else "dry-run",
        "plugin": args.plugin,
        "class_name": args.class_name,
        "target": target,
        "plan": plan,
        "reload_requested": args.reload,
        "reload_guard": reload_guard,
        "local_validation": {
            "available": validation is not None,
            "ok": validation.get("ok") if validation else None,
        },
    }
    if not args.apply:
        return result

    apply_deployment(args, plugin_dir, source, plan, target)
    if args.reload:
        base = normalize_base_url(args.base_url)
        key = load_api_key(args.api_key_file)
        path = f"/api/v1/plugin/reload/{args.class_name}"
        status, body = api_request(base, path, key)
        if not 200 <= status < 300:
            raise RuntimeError(f"plugin reload failed: HTTP {status} {redact_text(str(body))}")
    verified = remote_manifest(args.ssh_host, args.container, args.docker_bin, target)
    if set(verified) != set(source):
        raise RuntimeError("remote manifest does not match source after deployment")
    result["applied"] = True
    result["verified_file_count"] = len(verified)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely deploy one MoviePilot plugin over SSH.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--plugin", required=True, help="Lowercase plugins.v2 directory")
    parser.add_argument("--class-name", required=True)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--container", default="MP")
    parser.add_argument("--docker-bin", default="docker")
    parser.add_argument("--remote-root", default="/app/app/plugins")
    parser.add_argument("--base-url")
    parser.add_argument("--api-key-file")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-delete-stale", action="store_true")
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    if (args.apply or args.reload) and not (args.base_url or os.environ.get("MP_BASE_URL")):
        parser.error("--apply/--reload requires --base-url or MP_BASE_URL")
    try:
        result = run(args)
        print_json(result, args.pretty)
        return 0
    except Exception as error:
        print_json({"ok": False, "error": redact_text(str(error))}, args.pretty)
        return 2


if __name__ == "__main__":
    sys.exit(main())
