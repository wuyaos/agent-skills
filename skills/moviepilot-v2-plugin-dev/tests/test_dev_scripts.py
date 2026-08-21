import importlib.util
import json
from pathlib import Path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = load_module("mp_validate_plugin", ROOT / "scripts/validate_plugin.py")
METADATA = load_module("mp_update_metadata", ROOT / "scripts/update_metadata.py")


def make_repo(tmp_path, *, nested_model=False, version="1.0.0"):
    repo = tmp_path / "repo"
    plugin = repo / "plugins.v2" / "demo"
    plugin.mkdir(parents=True)
    model = "nested.value" if nested_model else "enabled"
    (plugin / "AGENTS.md").write_text("# Demo\n")
    (plugin / "__init__.py").write_text(
        "from app.plugins import _PluginBase\n"
        "class Demo(_PluginBase):\n"
        "    plugin_name = 'Demo'\n"
        f"    plugin_version = '{version}'\n"
        "    auth_level = 2\n"
        "    _enabled = False\n"
        "    def init_plugin(self, config=None): pass\n"
        "    def get_state(self): return self._enabled\n"
        "    def get_api(self): return [{'path': '/run'}]\n"
        f"    def get_form(self): return ([{{'component':'VSwitch','props':{{'model':'{model}'}}}}], {{}})\n"
        "    def get_page(self): return []\n"
        "    def stop_service(self): pass\n"
    )
    package = {
        "Demo": {
            "name": "Demo", "description": "Demo", "labels": "Demo",
            "version": version, "icon": "icon.png", "author": "tester", "level": 2,
            "history": {f"v{version}": "initial"},
        }
    }
    (repo / "package.v2.json").write_text(json.dumps(package, indent=4) + "\n")
    return repo


def check(report, check_id):
    return next(item for item in report.checks if item["id"] == check_id)


def test_validate_plugin_passes_minimal_contract(tmp_path):
    repo = make_repo(tmp_path)
    report = VALIDATOR.validate(repo, "demo", "Demo")
    assert report.ok
    assert check(report, "version-sync")["status"] == "pass"
    assert check(report, "api-relative-paths")["status"] == "pass"
    assert check(report, "flat-form-models")["status"] == "pass"


def test_validate_plugin_rejects_nested_model(tmp_path):
    repo = make_repo(tmp_path, nested_model=True)
    report = VALIDATOR.validate(repo, "demo", "Demo")
    assert not report.ok
    assert check(report, "flat-form-models")["evidence"] == ["nested.value"]


def test_update_metadata_dry_run_and_apply(tmp_path):
    repo = make_repo(tmp_path)
    plan = METADATA.build_update(repo, "demo", "Demo", "1.0.1", "bug fix")
    assert plan["changed"] is True
    assert "1.0.1" not in (repo / "plugins.v2/demo/__init__.py").read_text()
    METADATA.apply_update(plan)
    assert "plugin_version = '1.0.1'" in (repo / "plugins.v2/demo/__init__.py").read_text()
    package = json.loads((repo / "package.v2.json").read_text())["Demo"]
    assert package["version"] == "1.0.1"
    assert list(package["history"])[0] == "v1.0.1"


def test_update_metadata_refuses_history_overwrite(tmp_path):
    repo = make_repo(tmp_path)
    try:
        METADATA.build_update(repo, "demo", "Demo", "1.0.0", "different")
    except ValueError as error:
        assert "already exists" in str(error)
    else:
        raise AssertionError("expected history overwrite rejection")
