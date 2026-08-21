"""Shared safe primitives for MoviePilot debug scripts."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SECRET_KEY_RE = re.compile(r"(?:password|passwd|secret|cookie|token|api[_-]?key|authorization)", re.I)
SENSITIVE_TEXT_PATTERNS = [
    re.compile(r"(?i)(X-API-KEY\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(Authorization\s*[:=]\s*Bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(__Host-[A-Za-z0-9_-]+=)[^\s,;]+"),
    re.compile(r"(?i)((?:password|cookie|token|api[_-]?key)\s*[:=]\s*)[^\s,;]+"),
]


class ApiError(RuntimeError):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"HTTP {status} {path}: {message}".rstrip())
        self.status = status
        self.path = path
        self.message = message


def load_api_key(api_key_file: str | None = None) -> str:
    if api_key_file:
        path = Path(api_key_file).expanduser()
        value = path.read_text().strip()
    else:
        value = os.environ.get("MP_API_KEY", "").strip()
    if not value:
        raise ValueError("MoviePilot API key is required via MP_API_KEY or --api-key-file")
    return value


def normalize_base_url(value: str | None) -> str:
    base = (value or os.environ.get("MP_BASE_URL") or "http://127.0.0.1:3000").strip().rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("invalid MP base URL")
    return base


def api_request(
    base_url: str,
    path: str,
    api_key: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int, Any]:
    if not path.startswith("/api/v1/"):
        raise ValueError("API path must start with /api/v1/")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            "X-API-KEY": api_key,
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, _decode_body(raw, response.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as error:
        raw = error.read()
        decoded = _decode_body(raw, error.headers.get("Content-Type", ""))
        return error.code, decoded


def require_json(status: int, body: Any, path: str) -> Any:
    if not 200 <= status < 300:
        message = ""
        if isinstance(body, dict):
            message = str(body.get("message") or body.get("detail") or body.get("error") or "")
        raise ApiError(status, path, redact_text(message))
    return body


def _decode_body(raw: bytes, content_type: str) -> Any:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    if "json" in content_type.lower() or text.lstrip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return text[:4000]


def redact(value: Any, key: str = "") -> Any:
    if SECRET_KEY_RE.search(key):
        if value in (None, "", False, [], {}):
            return {"configured": False}
        return {"configured": True}
    if isinstance(value, dict):
        return {str(item_key): redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(text: str) -> str:
    result = str(text or "")
    for pattern in SENSITIVE_TEXT_PATTERNS:
        result = pattern.sub(r"\1***REDACTED***", result)
    return result


def parse_assignment(value: str) -> tuple[str, Any]:
    if "=" not in value:
        raise ValueError(f"assignment must be KEY=VALUE: {value}")
    key, raw = value.split("=", 1)
    key = key.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
        raise ValueError(f"invalid config key: {key}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return key, parsed


def extract_payload(response: Any) -> Any:
    if isinstance(response, dict) and "data" in response and set(response).intersection({"success", "message", "message_i18n"}):
        return response.get("data")
    return response


def extract_form_model(response: Any) -> dict[str, Any]:
    payload = extract_payload(response)
    if isinstance(payload, dict) and isinstance(payload.get("model"), dict):
        return payload["model"]
    if isinstance(response, dict) and isinstance(response.get("model"), dict):
        return response["model"]
    raise ValueError("form response does not contain model")


def print_json(value: Any, pretty: bool = False):
    print(json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, sort_keys=False))
