#!/usr/bin/env python3
"""Read-only MoviePilot plugin runtime probe with redacted output."""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from collections import Counter
from typing import Any

from common import api_request, extract_form_model, extract_payload, load_api_key, normalize_base_url, print_json, redact, redact_text

SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
SAFE_COMMAND = re.compile(r"^(?:[A-Za-z0-9_.-]+|/[A-Za-z0-9_./-]+)$")


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _plugin_entries(body: Any, plugin_id: str) -> list[dict[str, Any]]:
    payload = extract_payload(body)
    if isinstance(payload, dict):
        payload = payload.get("data") or payload.get("items") or payload.get("plugins") or []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict) and str(item.get("id") or item.get("plugin_id") or "") == plugin_id]


def _schedule_entries(body: Any, plugin_id: str) -> list[dict[str, Any]]:
    payload = extract_payload(body)
    if isinstance(payload, dict):
        payload = payload.get("data") or payload.get("items") or []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict) and plugin_id.lower() in str(item.get("id") or item.get("name") or "").lower()]


def _summarize_form(body: Any) -> dict[str, Any]:
    model = extract_form_model(body)
    secret_keys = [key for key in model if re.search(r"password|secret|cookie|token|api[_-]?key", key, re.I)]
    return {
        "model_keys": sorted(model),
        "enabled": model.get("enabled"),
        "cron": model.get("cron"),
        "onlyonce": model.get("onlyonce"),
        "secret_fields": {key: bool(model.get(key)) for key in sorted(secret_keys)},
    }


def _summarize_page(body: Any) -> dict[str, Any]:
    payload = extract_payload(body)
    page = payload.get("page") if isinstance(payload, dict) else None
    if page is None and isinstance(body, dict):
        page = body.get("page")
    nodes = list(_walk(page or []))
    components = Counter(str(node.get("component")) for node in nodes if node.get("component"))
    texts = [str(node.get("text")) for node in nodes if isinstance(node.get("text"), (str, int, float))]
    return {
        "node_count": len(nodes),
        "components": dict(components.most_common(20)),
        "section_texts": [text for text in texts if len(text) <= 40][:30],
    }


def _request_summary(base_url: str, api_key: str, path: str, summarizer=None) -> dict[str, Any]:
    status, body = api_request(base_url, path, api_key)
    result: dict[str, Any] = {"path": path, "status": status, "ok": 200 <= status < 300}
    if result["ok"] and summarizer:
        try:
            result["summary"] = summarizer(body)
        except Exception as error:
            result["ok"] = False
            result["error"] = str(error)
    elif not result["ok"]:
        result["error"] = redact(body)
    return result


def _remote_probe(host: str, container: str, docker_bin: str, plugin_id: str, log_lines: int) -> dict[str, Any]:
    if not SAFE_NAME.fullmatch(host) or not SAFE_NAME.fullmatch(container):
        raise ValueError("unsafe ssh host or container name")
    if not SAFE_COMMAND.fullmatch(docker_bin):
        raise ValueError("unsafe docker command")
    plugin_lower = plugin_id.lower()
    if not SAFE_NAME.fullmatch(plugin_lower):
        raise ValueError("unsafe plugin id")
    log_path = f"/config/logs/plugins/{plugin_lower}.log"
    source_path = f"/app/app/plugins/{plugin_lower}/__init__.py"
    tail_command = f"tail -{log_lines} {log_path} 2>/dev/null || true"
    version_command = f"grep -m1 'plugin_version *=' {source_path} 2>/dev/null || true"
    script = (
        f"D={shlex.quote(docker_bin)}; "
        f"$D exec {shlex.quote(container)} date '+%Y-%m-%d %H:%M:%S %Z'; "
        f"$D exec {shlex.quote(container)} sh -c {shlex.quote(tail_command)}; "
        f"$D exec {shlex.quote(container)} sh -c {shlex.quote(version_command)}"
    )
    result = subprocess.run(["ssh", host, script], capture_output=True, text=True, timeout=30)
    lines = [redact_text(line) for line in result.stdout.splitlines()]
    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "lines": lines,
        "stderr": redact_text(result.stderr.strip()),
    }


def probe(args) -> dict[str, Any]:
    base_url = normalize_base_url(args.base_url)
    api_key = load_api_key(args.api_key_file)
    plugin_id = args.plugin
    requests_report = []

    requests_report.append(_request_summary(
        base_url, api_key, "/api/v1/plugin/?state=all",
        lambda body: redact(_plugin_entries(body, plugin_id)),
    ))
    requests_report.append(_request_summary(
        base_url, api_key, f"/api/v1/plugin/form/{plugin_id}", _summarize_form,
    ))
    page_result = _request_summary(
        base_url, api_key, f"/api/v1/plugin/page/{plugin_id}", _summarize_page,
    )
    if page_result["status"] == 404:
        page_result.update({"ok": True, "summary": {"available": False}})
        page_result.pop("error", None)
    requests_report.append(page_result)

    schedule_result = _request_summary(
        base_url, api_key, "/api/v1/dashboard/schedule",
        lambda body: redact(_schedule_entries(body, plugin_id)),
    )
    if schedule_result["status"] == 404:
        schedule_result = _request_summary(
            base_url, api_key, "/api/v1/dashboard/schedule2",
            lambda body: redact(_schedule_entries(body, plugin_id)),
        )
    requests_report.append(schedule_result)

    status_path = f"/api/v1/plugin/{plugin_id}/status"
    status_result = _request_summary(base_url, api_key, status_path, lambda body: redact(extract_payload(body)))
    if status_result["status"] != 404:
        requests_report.append(status_result)

    remote = None
    if args.ssh_host:
        remote = _remote_probe(args.ssh_host, args.container, args.docker_bin, plugin_id, args.log_lines)

    required = [requests_report[0], requests_report[1], requests_report[3]]
    return {
        "ok": all(item["ok"] for item in required),
        "mode": "read-only",
        "base_url": base_url,
        "plugin": plugin_id,
        "requests": requests_report,
        "remote": remote,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect redacted, read-only MoviePilot plugin evidence.")
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--base-url", help="Defaults to MP_BASE_URL or http://127.0.0.1:3000")
    parser.add_argument("--api-key-file", help="Read API key from file; otherwise MP_API_KEY")
    parser.add_argument("--ssh-host")
    parser.add_argument("--container", default="MP")
    parser.add_argument("--docker-bin", default="/usr/bin/docker")
    parser.add_argument("--log-lines", type=int, default=20)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.log_lines <= 200:
        parser.error("--log-lines must be 1..200")
    try:
        result = probe(args)
        print_json(result, args.pretty)
        return 0 if result["ok"] else 1
    except Exception as error:
        print_json({"ok": False, "error": redact_text(str(error))}, args.pretty)
        return 2


if __name__ == "__main__":
    sys.exit(main())
