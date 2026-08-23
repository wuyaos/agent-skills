import importlib.util
import json
import sys
import threading
from argparse import Namespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
COMMON = load_module("mp_debug_common", ROOT / "scripts/common.py")
MERGE = load_module("mp_merge_config", ROOT / "scripts/merge_plugin_config.py")
DEPLOY = load_module("mp_deploy_plugin", ROOT / "scripts/deploy_plugin.py")
PROBE = load_module("mp_probe_plugin", ROOT / "scripts/probe_plugin.py")


def test_redact_removes_nested_secrets():
    value = {
        "enabled": True,
        "password": "secret",
        "nested": {"cookie": "session=value", "message": "ok"},
    }
    redacted = COMMON.redact(value)
    assert redacted["password"] == {"configured": True}
    assert redacted["nested"]["cookie"] == {"configured": True}
    assert redacted["nested"]["message"] == "ok"
    assert "abc" not in COMMON.redact_text("X-API-KEY: abcdefghijklmnop")


def test_merge_config_preserves_unspecified_fields(tmp_path):
    secret_file = tmp_path / "cookie"
    secret_file.write_text("__Host-session=value")
    model = {"enabled": True, "cron": "0 1 * * *", "cookie": "old", "onlyonce": False}
    merged, public = MERGE.build_plan(
        model,
        ["cron=\"0 2 * * *\""],
        [f"cookie={secret_file}"],
        allow_business_action=False,
    )
    assert merged == {"enabled": True, "cron": "0 2 * * *", "cookie": "__Host-session=value", "onlyonce": False}
    assert public["changed_keys"] == ["cookie", "cron"]
    assert public["secret_fields"]["cookie"] == {"before_configured": True, "after_configured": True}


def test_merge_config_blocks_secret_cli_and_business_action():
    model = {"password": "old", "onlyonce": False}
    with pytest.raises(ValueError, match="set-secret"):
        MERGE.build_plan(model, ["password=new"], [], False)
    with pytest.raises(ValueError, match="allow-business-action"):
        MERGE.build_plan(model, ["onlyonce=true"], [], False)
    with pytest.raises(ValueError, match="allow-business-action"):
        MERGE.build_plan({"enabled": True, "onlyonce": True}, ["enabled=false"], [], False)
    with pytest.raises(ValueError, match="masked secrets"):
        MERGE.build_plan({"enabled": True, "password": "********"}, ["enabled=false"], [], False)


def test_deploy_manifest_excludes_tests_and_caches(tmp_path):
    plugin = tmp_path / "demo"
    (plugin / "tests").mkdir(parents=True)
    (plugin / "__pycache__").mkdir()
    (plugin / ".omc/state").mkdir(parents=True)
    (plugin / "__init__.py").write_text("x=1")
    (plugin / "client.py").write_text("x=2")
    (plugin / "tests/test_client.py").write_text("assert True")
    (plugin / "__pycache__/x.pyc").write_bytes(b"x")
    (plugin / ".omc/state/session.json").write_text("{}")
    assert DEPLOY.source_manifest(plugin) == ["__init__.py", "client.py"]
    plan = DEPLOY.build_plan(["__init__.py", "client.py"], ["__init__.py", "old.py"])
    assert plan["add"] == ["client.py"]
    assert plan["overwrite"] == ["__init__.py"]
    assert plan["delete_stale"] == ["old.py"]


def test_remote_manifest_uses_source_exclusions(monkeypatch):
    remote_output = "\n".join([
        "__init__.py",
        "client.py",
        "old.py",
        "__pycache__/client.cpython-312.pyc",
        ".omc/state/session.json",
        "tests/test_client.py",
        ".hidden",
    ])

    def fake_run_ssh(_host, _command, timeout=40):
        return type("Result", (), {
            "returncode": 0,
            "stdout": remote_output,
            "stderr": "",
        })()

    monkeypatch.setattr(DEPLOY, "_run_ssh", fake_run_ssh)
    remote = DEPLOY.remote_manifest("qnap", "MP", "docker", "/app/app/plugins/demo")
    assert remote == ["__init__.py", "client.py", "old.py"]

    plan = DEPLOY.build_plan(["__init__.py", "client.py"], remote)
    assert plan["add"] == []
    assert plan["overwrite"] == ["__init__.py", "client.py"]
    assert plan["delete_stale"] == ["old.py"]


def test_deploy_rejects_unsafe_target():
    with pytest.raises(ValueError):
        DEPLOY._validate_target("../demo", "qnap", "MP", "docker", "/app/app/plugins")
    with pytest.raises(ValueError):
        DEPLOY._validate_target("demo", "qnap;rm", "MP", "docker", "/app/app/plugins")


def test_probe_summaries_do_not_expose_secret_values():
    form = {"model": {"enabled": True, "cron": "0 1 * * *", "password": "secret", "cookie": "value"}}
    summary = PROBE._summarize_form(form)
    assert summary["secret_fields"] == {"cookie": True, "password": True}
    assert "model" not in summary
    assert all(isinstance(value, bool) for value in summary["secret_fields"].values())
    page = {"page": [{"component": "VCard", "content": [{"component": "VCardTitle", "text": "Status"}]}]}
    page_summary = PROBE._summarize_page(page)
    assert page_summary["components"] == {"VCard": 1, "VCardTitle": 1}


def test_probe_and_config_apply_against_fake_api(tmp_path):
    state = {
        "config": {"enabled": True, "cron": "0 1 * * *", "password": "secret", "cookie": "cookie", "onlyonce": False},
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            pass

        def send_json(self, status, body):
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path.startswith("/api/v1/plugin/?"):
                return self.send_json(200, [{"id": "Demo", "installed": True, "state": True}])
            if self.path == "/api/v1/plugin/form/Demo":
                return self.send_json(200, {"render_mode": "vuetify", "model": state["config"]})
            if self.path == "/api/v1/plugin/page/Demo":
                return self.send_json(200, {"page": [{"component": "VCard", "text": "Demo"}]})
            if self.path == "/api/v1/dashboard/schedule":
                return self.send_json(200, [{"id": "Demo_Demo", "status": "等待"}])
            return self.send_json(404, {"message": "not found"})

        def do_PUT(self):
            length = int(self.headers.get("Content-Length", "0"))
            state["config"] = json.loads(self.rfile.read(length))
            return self.send_json(200, {"success": True, "data": {}})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    key_file = tmp_path / "api-key"
    key_file.write_text("test-api-key")
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        probe_args = Namespace(
            plugin="Demo", base_url=base_url, api_key_file=str(key_file),
            ssh_host=None, container="MP", docker_bin="docker", log_lines=20,
        )
        report = PROBE.probe(probe_args)
        assert report["ok"] is True
        form_summary = report["requests"][1]["summary"]
        assert form_summary["secret_fields"] == {"cookie": True, "password": True}

        merge_args = Namespace(
            plugin="Demo", base_url=base_url, api_key_file=str(key_file),
            sets=["cron=\"0 2 * * *\""], secret_sets=[], apply=True,
            allow_business_action=False,
        )
        result = MERGE.run(merge_args)
        assert result["applied"] is True
        assert state["config"]["cron"] == "0 2 * * *"
        assert state["config"]["password"] == "secret"
        assert state["config"]["cookie"] == "cookie"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
