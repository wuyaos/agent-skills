#!/usr/bin/env python3
"""Safely merge MoviePilot plugin config using the complete form model.

Dry-run by default. Secret values must come from files, never command arguments.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

from common import api_request, extract_form_model, load_api_key, normalize_base_url, parse_assignment, print_json, redact_text, require_json

SECRET_KEY_RE = re.compile(r"(?:password|passwd|secret|cookie|token|api[_-]?key|authorization)", re.I)


def _parse_secret_assignment(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise ValueError("secret assignment must be KEY=FILE")
    key, file_name = value.split("=", 1)
    key = key.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
        raise ValueError(f"invalid config key: {key}")
    if not SECRET_KEY_RE.search(key):
        raise ValueError(f"--set-secret is only for secret-like keys: {key}")
    secret = Path(file_name).expanduser().read_text().strip()
    if not secret:
        raise ValueError(f"secret file is empty for key: {key}")
    return key, secret


def build_plan(model: dict[str, Any], sets: list[str], secret_sets: list[str], allow_business_action: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    merged = dict(model)
    changes: dict[str, Any] = {}
    for item in sets:
        key, value = parse_assignment(item)
        if SECRET_KEY_RE.search(key):
            raise ValueError(f"secret key must use --set-secret: {key}")
        if key not in model:
            raise KeyError(f"unknown config key: {key}")
        changes[key] = value
    for item in secret_sets:
        key, value = _parse_secret_assignment(item)
        if key not in model:
            raise KeyError(f"unknown config key: {key}")
        changes[key] = value
    merged.update(changes)
    if merged.get("onlyonce") is True and not allow_business_action:
        raise ValueError("effective onlyonce=true requires --allow-business-action")
    changed_keys = sorted(key for key, value in changes.items() if model.get(key) != value)
    public = {
        "changed_keys": changed_keys,
        "preserved_key_count": len(model) - len(changed_keys),
        "secret_fields": {
            key: {"before_configured": bool(model.get(key)), "after_configured": bool(merged.get(key))}
            for key in sorted(model)
            if SECRET_KEY_RE.search(key)
        },
        "business_action_requested": merged.get("onlyonce") is True,
    }
    return merged, public


def run(args) -> dict[str, Any]:
    base_url = normalize_base_url(args.base_url)
    api_key = load_api_key(args.api_key_file)
    form_path = f"/api/v1/plugin/form/{args.plugin}"
    status, body = api_request(base_url, form_path, api_key)
    model = extract_form_model(require_json(status, body, form_path))
    merged, public = build_plan(model, args.sets, args.secret_sets, args.allow_business_action)
    result = {
        "ok": True,
        "applied": False,
        "mode": "apply" if args.apply else "dry-run",
        "plugin": args.plugin,
        **public,
    }
    if not args.apply or not public["changed_keys"]:
        return result

    put_path = f"/api/v1/plugin/{args.plugin}"
    put_status, put_body = api_request(base_url, put_path, api_key, method="PUT", payload=merged, timeout=30)
    require_json(put_status, put_body, put_path)
    mismatches = list(public["changed_keys"])
    for attempt in range(5):
        verify_status, verify_body = api_request(base_url, form_path, api_key)
        verified = extract_form_model(require_json(verify_status, verify_body, form_path))
        mismatches = [key for key in public["changed_keys"] if verified.get(key) != merged.get(key)]
        if not mismatches:
            break
        if attempt < 4:
            time.sleep(1)
    if mismatches:
        raise RuntimeError(f"config verification failed for keys: {', '.join(mismatches)}")
    result["applied"] = True
    result["verified_keys"] = public["changed_keys"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge a complete MoviePilot plugin config safely.")
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--base-url", help="Defaults to MP_BASE_URL or http://127.0.0.1:3000")
    parser.add_argument("--api-key-file", help="Read API key from file; otherwise MP_API_KEY")
    parser.add_argument("--set", dest="sets", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--set-secret", dest="secret_sets", action="append", default=[], metavar="KEY=FILE")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-business-action", action="store_true", help="Required for onlyonce=true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    if not args.sets and not args.secret_sets:
        parser.error("at least one --set or --set-secret is required")
    try:
        result = run(args)
        print_json(result, args.pretty)
        return 0
    except Exception as error:
        print_json({"ok": False, "error": redact_text(str(error))}, args.pretty)
        return 2


if __name__ == "__main__":
    sys.exit(main())
