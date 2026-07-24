---
name: moviepilot-v2-plugin-dev
description: "Build and maintain MoviePilot V2 plugins using the official V2 development contract. Load when the user mentions 插件开发/写插件/新建插件/迁移V2插件/插件表单/插件页面/插件API/插件调度/插件元数据/package.v2.json, or V2 plugin get_form/get_page/get_api/get_service/get_dashboard/get_actions/get_agent_tools wiring, version sync, registration/render issues. English: creating/upgrading V2 plugins, validating package.v2.json metadata, troubleshooting V2 registration/render. Do not use for runtime debugging a live instance — use moviepilot-debug."
---

# MoviePilot V2 Plugin Dev

## Purpose
Provide a repeatable workflow for developing and validating MoviePilot V2 plugins in this repository, aligned with the official V2 contract.

Primary reference:
- `references/V2_Plugin_Development.md`

## Use When
- User asks to create a new MoviePilot plugin for V2.
- User asks to migrate V1 plugin to V2.
- User asks why plugin is not visible / API not registered / service not loaded / page not rendered.
- User asks to standardize plugin metadata, versioning, or release checklist.
- User asks about dashboard, workflow actions, agent tools, message buttons, or system cache.
- User asks to wire get_form / get_page / get_api / get_service / get_dashboard / get_actions / get_agent_tools.

## Do Not Use When
- Request is unrelated to MoviePilot plugin development.
- Request is only generic Python refactor with no plugin contract surface.

## Workflow
1. Identify plugin mode and target:
- `vuetify` JSON mode (default) or `vue` federated mode.
- New plugin (`plugins.v2/<id>/`) or migration from `plugins/<id>/`.

2. Validate filesystem and metadata contract:
- Plugin path under `plugins.v2/<plugin_id_lower>/`.
  - **目录名必须全小写**（如 `sunnyptsignin`，而非 `SunnyPTSignin`）。
  - MoviePilot 安装时用 `pid.lower()` 拼 GitHub raw 路径（见 `PluginHelper.install` line `file_api += f"/{pid.lower()}"`），GitHub 内容 API 大小写敏感，目录名含大写会导致 **404 无法安装**。
  - 创建新插件后用 `ls plugins.v2/ | grep -v '^[a-z0-9_-]*$'` 检查是否有大写目录名。
- Class metadata fields exist and are internally consistent.
- `package.v2.json` has plugin entry with matching `version`, `name`, `level`.
- `plugin_version` equals metadata `version`.
- `_enabled = False` class attribute exists (防止 `get_state()` 在首次加载时 AttributeError).

3. Validate required _PluginBase methods:
- `init_plugin` — must handle `config=None` gracefully (`config = config or {}`)
- `get_state`
- `get_api` — auth: `bear` for frontend, `apikey` for external
- `get_form` — returns `(page_json, default_model)`
- `get_page` — wrap with try/except to prevent silent crash
- `stop_service`

4. Validate optional surfaces only when needed:
- `get_command` for slash commands + `@eventmanager.register(EventType.PluginAction)` handler.
- `get_service` for schedulers/services — `id` must be stable and unique.
- `get_dashboard` / `get_dashboard_meta` for dashboards.
- `get_render_mode` + `get_sidebar_nav` for Vue full page plugins.
- `get_module` for system module override (v2.4.4+).
- `get_actions` for workflow actions (v2.4.8+).
- `get_agent_tools` for AI agent tools (v2.8.0+).

5. Enforce V2 operational rules:
- Service `id` must be stable and unique.
- API auth (`bear` vs `apikey`) should match usage scenario.
- Avoid hardcoded plugin IDs — use `self.__class__.__name__` for clone/fork friendliness.
- Prefer `_PluginBase` helpers: `update_config/get_config/get_data_path/save_data/get_data/del_data/post_message`.
- `get_page()` API calls: use `events.click.api` pattern (v1.8.4+), page auto-refreshes.
- Message buttons: `callback_data` format `[PLUGIN]ClassName|action` (v2.5.7+).
- System cache: `@cached` decorator or `TTLCache`/`FileCache` classes (v2.7.4+).

6. Run minimum verification:
- `python3 -m py_compile plugins.v2/<id>/__init__.py`
- `python3 -m compileall plugins.v2/<id>`
- `git diff --check`

7. Publish checklist pass:
- Path, naming, metadata, version alignment, history updated, release flag (if required).

## Version Sync Procedure (版本同步规范)
When releasing a plugin update, **three places must be updated together** — missing any one causes MP to show stale version / no update prompt / history gap:

1. `plugins.v2/<id>/__init__.py` → class attribute `plugin_version = "x.y.z"` (source of truth at runtime).
2. `package.v2.json` → `<PluginClassName>.version` must equal `plugin_version`; add a `history.v<x.y.z>` entry describing the change (one line, user-facing).
3. Commit + push to `main` (MP pulls plugin metadata from the repo's `package.v2.json`).

Rules:
- `plugin_version` (code) and `package.v2.json` `version` (metadata) **must be identical** — never bump one without the other.
- `history` entries are reverse-chronological (newest first), keyed by `v<x.y.z>`, value is a concise Chinese/English changelog line.
- Bump rules: patch for bugfix/internal tweak; minor for new feature/behavior; major for breaking change. Pre-1.0 plugins may use 0.x.
- Never edit an already-released `history` entry; add a new version line instead.
- After editing, validate: `python3 -c "import json; d=json.load(open('package.v2.json')); p=d['<PluginClassName>']; assert p['version']=='x.y.z'; assert 'v<x.y.z>' in p['history']"`.

## Fast Commands
Use these from repo root:

```bash
# locate candidate plugin files
rg --files plugins.v2

# validate one plugin quickly
python3 -m py_compile plugins.v2/<plugin_id>/__init__.py
python3 -m compileall plugins.v2/<plugin_id>

# verify metadata entry exists
rg -n '"<PluginClassName>"\s*:\s*\{' package.v2.json
```

## Scaffolding Template
Minimal template files are provided in:
- `templates/minimal_v2_plugin/__init__.py`
- `templates/minimal_v2_plugin/requirements.txt`
- `templates/minimal_v2_plugin/package.v2.entry.json`

Copy and adapt them when creating a new plugin.

## Known Gotchas
- `plugin_version` 与 `package.v2.json` `version` 必须同步，漏一处会导致 MP 显示旧版本/无更新提示 → 见 ## Version Sync Procedure
- 插件图标 GitHub raw URL CDN 缓存约 5 分钟，MP 进程还会缓存图标；需重启 MP 或禁用再启用插件才刷新
- `init_plugin` 须预创建日志文件（`path.touch`），否则前端首次查看日志 404 → 见 ## Troubleshooting Router 的 page-not-rendering
- **插件目录名含大写** → 安装时 404 → 目录名必须全小写，见 ## Workflow Step 2

## Troubleshooting Router
When plugin behavior is inconsistent with this repo alone, inspect host/frontend integration points:

Note: `MoviePilot/app/...` paths vary by MP install mode (source/Docker); use the actual deployed path.

| 问题 | 文件 |
|------|------|
| 插件未加载 | `MoviePilot/app/core/plugin.py` |
| API 未注册 | `MoviePilot/app/api/endpoints/plugin.py` |
| _PluginBase 方法 | `MoviePilot/app/plugins/__init__.py` |
| Vue 联邦加载 | `MoviePilot-Frontend/src/utils/federationLoader.ts` |
| 模块联邦指南 | `MoviePilot-Frontend/docs/module-federation-guide.md` |

Common install-404 causes:
1. **插件目录名含大写** → MoviePilot 用 `pid.lower()` 请求 GitHub raw，大小写不匹配 → 404
   - 修复：`git mv plugins.v2/MyPlugin plugins.v2/myplugin_tmp && git mv plugins.v2/myplugin_tmp plugins.v2/myplugin`（两步 mv 规避大小写不敏感文件系统）
2. PLUGIN_MARKET 未配置自己的仓库地址 → 从 jxxghp 官方仓库找不到自定义插件 → 404

Common page-not-rendering causes:
1. Missing `_enabled = False` class attribute → `get_state()` AttributeError
2. `get_form()` / `get_page()` crashes silently (add try/except with VAlert fallback)
3. `self.siteoper` / `self.sites` is None when `init_plugin` failed → guard with `try/except`
4. Import error in `__init__.py` prevents class loading → check all top-level imports

## Local Debug
调试运行中的 MoviePilot 实例（CLI/API/日志/调度器）请用 `moviepilot-debug` skill，本 skill 只负责插件开发契约与发布规范。

## Notes
- Keep diffs minimal and reversible.
- Prefer compatibility-preserving migrations when IDs/routes are already in use.
- If changing externally visible IDs, add a transitional compatibility path.
- Event types reference: see `references/V2_Plugin_Development.md` section 10.
- Vuetify JSON component patterns: see `references/V2_Plugin_Development.md` section 11.
- CLI reference: see [MoviePilot-Wiki/cli.md](https://github.com/jxxghp/MoviePilot-Wiki/blob/main/cli.md)
