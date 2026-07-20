---
name: moviepilot-debug
description: "Debug and analyze a running MoviePilot V2 instance with local CLI and API probes. Load when the user mentions MoviePilot/MP runtime issues: 插件未加载/插件bug/插件不工作, 定时不触发/定时任务没执行/调度器, 插件页面空白/表单异常/日志404, 识别搜索失败, 版本不更新/服务起不来/状态异常, MP调试/MP排障/查日志/查插件状态. English: plugin not loaded, API not registered, scheduler not firing, recognition/search failures, log inspection, version/update issues, startup failures, runtime state discovery. Do not use for plugin code/contract changes — use moviepilot-v2-plugin-dev."
---

# MoviePilot Debug

## Purpose
Provide a compact, evidence-first runbook for debugging a **running MoviePilot V2 instance** via the local `moviepilot` CLI and backend API. This complements `moviepilot-v2-plugin-dev`: use that skill for plugin contract/code changes, use this skill for runtime 排障、状态探查、日志/API/调度器定位。

Primary local references used to build this skill:
- CLI reference: `/tmp/mp_cli.md`
- OpenAPI spec: `/tmp/mp_openapi.json`

Note: these are build-time source materials only; this skill does not depend on those files at runtime. To regenerate them, collect CLI `--help` output and `/docs` OpenAPI from a running MP instance.

## Use When
- MoviePilot 服务起不来、前端/后端端口不通、状态异常。
- 插件未加载、插件 API 未注册、插件页面/表单/仪表板异常、插件日志 404。
- 定时任务不触发、scheduler/service job 需要手动触发。
- 媒体识别、搜索、刮削、站点资源查询失败。
- 订阅、下载、整理/transfer、媒体库存在性需要只读探查。
- 版本不更新、升级后前后端不一致、需要查 versions/progress/logging。
- 需要用 CLI/API 快速采集 MoviePilot runtime 证据。

## Do Not Use When
- 只是在编写/迁移 V2 插件代码、校验 `get_api/get_service/get_form` 契约：优先用 `moviepilot-v2-plugin-dev`。
- 与 MoviePilot 运行时、CLI、API、日志无关。
- 需要联网查未知文档；本 skill 基于本地资料，不做外部搜索。

## CLI 调试手册

### Help / discovery

```bash
moviepilot --help
moviepilot help
moviepilot commands
moviepilot help install
moviepilot help init
moviepilot help setup
moviepilot help uninstall
moviepilot help update
moviepilot help agent
moviepilot help config
moviepilot help config set
moviepilot help tool
moviepilot help scheduler
```

配置项与动态工具发现：

```bash
moviepilot config keys
moviepilot config keys API
moviepilot config describe API_TOKEN
moviepilot tool list
moviepilot tool show <tool_name>
```

### Install / setup / init

后端依赖：

```bash
moviepilot install deps
moviepilot install deps --python python3.11
moviepilot install deps --venv /path/to/venv
moviepilot install deps --recreate
moviepilot install deps --config-dir /path/to/moviepilot-config
```

前端 release：

```bash
moviepilot install frontend
moviepilot install frontend --version latest
moviepilot install frontend --version v2.9.31
moviepilot install frontend --node-version 20.12.1
moviepilot install frontend --config-dir /path/to/moviepilot-config
```

资源文件：

```bash
moviepilot install resources
moviepilot install resources --resources-repo /path/to/MoviePilot-Resources
moviepilot install resources --resource-dir /path/to/resources.v2
moviepilot install resources --config-dir /path/to/moviepilot-config
```

初始化本地配置：

```bash
moviepilot init
moviepilot init --wizard
moviepilot init --skip-resources
moviepilot init --force-token
moviepilot init --superuser admin --superuser-password 'ChangeMe123!'
moviepilot init --config-dir /path/to/moviepilot-config
```

一体化安装：

```bash
moviepilot setup
moviepilot setup --wizard
moviepilot setup --frontend-version latest
moviepilot setup --node-version 20.12.1
moviepilot setup --skip-resources
moviepilot setup --recreate
moviepilot setup --superuser admin --superuser-password 'ChangeMe123!'
moviepilot setup --config-dir /path/to/moviepilot-config
```

`setup` 串行执行：安装后端依赖、安装前端 release、同步资源、初始化配置。`--wizard` 可配置 API_TOKEN、超级管理员、数据库、下载目录/媒体库、AI Agent、用户站点认证、开机自启、下载器、媒体服务器、消息通知。

### Service management / startup / doctor

```bash
moviepilot start
moviepilot start --timeout 60
moviepilot start --safe
moviepilot stop
moviepilot stop --timeout 30 --force
moviepilot restart
moviepilot restart --start-timeout 60 --stop-timeout 30
moviepilot status
moviepilot version
```

Key runtime facts:
- `start` 先启动后端，再启动前端。
- `start --safe` 安全模式启动后端，本次启动跳过插件、调度器、监控、命令和工作流等后台扩展能力，不修改用户配置。
- `MOVIEPILOT_AUTO_UPDATE=release|true|dev` 时，`start/restart` 启动前尽力执行本地自动更新；失败只告警。
- 前端默认 `NGINX_PORT=3000`，后端默认 `PORT=3001`。
- 前端 `service.js` 代理 `/api` 与 `/cookiecloud` 到后端。

开机自启：

```bash
moviepilot startup status
moviepilot startup enable
moviepilot startup disable
moviepilot startup enable --venv /path/to/venv
moviepilot startup enable --config-dir /path/to/moviepilot-config
```

离线诊断：

```bash
moviepilot doctor
moviepilot doctor --json
moviepilot doctor --fix
moviepilot doctor --deep
```

`doctor` 不依赖后端已启动，会读取配置目录、运行时文件、日志、进程、端口、依赖、数据库和前端资源；`--json` 输出稳定 JSON；`--fix` 仅白名单安全修复；`--deep` 执行较慢探测。

Docker 场景：

```bash
docker exec <container> moviepilot doctor
# 容器已退出时，资料给出的方式：用镜像挂载同一配置目录运行 python -m app.cli doctor
```

### Logs

```bash
moviepilot logs
moviepilot logs --lines 100
moviepilot logs --stdio
moviepilot logs --frontend
moviepilot logs --follow
moviepilot logs --frontend --follow
moviepilot logs --stdio --follow
```

日志路径（本地源码模式）：
- 后端应用日志：`<Config Dir>/logs/moviepilot.log`
- 后端启动日志：`<Config Dir>/logs/moviepilot.stdout.log`
- 前端启动日志：`<Config Dir>/logs/moviepilot.frontend.stdout.log`

### Config

```bash
moviepilot config path
moviepilot config list
moviepilot config list --show-secrets
moviepilot config get PORT
moviepilot config set PORT 3001
moviepilot config set NGINX_PORT 3000
moviepilot config set API_TOKEN your-token-here
moviepilot config keys
moviepilot config keys DB_
moviepilot config keys --show-current
moviepilot config keys --show-current --show-secrets
moviepilot config describe PORT
moviepilot config describe API_TOKEN --show-secrets
```

默认配置目录：
- macOS: `~/Library/Application Support/MoviePilot`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/moviepilot`

### Update / uninstall

```bash
moviepilot update backend
moviepilot update backend --ref latest
moviepilot update backend --ref v2
moviepilot update backend --ref v2.9.31
moviepilot update frontend
moviepilot update frontend --frontend-version latest
moviepilot update frontend --frontend-version v2.9.31
moviepilot update all
moviepilot update all --ref latest --frontend-version latest
moviepilot update all --skip-resources
```

更新前先执行：

```bash
moviepilot stop
```

卸载：

```bash
moviepilot uninstall
moviepilot uninstall --venv /path/to/venv
moviepilot uninstall --config-dir /path/to/moviepilot-config
```

### Agent / Tool / Scheduler

```bash
moviepilot agent 帮我分析最近一次搜索失败的原因
moviepilot agent --user-id admin 帮我检查当前下载器配置
moviepilot agent --session cli-debug-1 帮我看看为什么没有自动整理
moviepilot agent --new-session 帮我总结当前系统配置有什么明显问题
```

使用前需要正确配置 LLM 参数并打开 `AI_AGENT_ENABLE`。

```bash
moviepilot tool list
moviepilot tool show query_schedulers
moviepilot tool show search_torrents
moviepilot tool run query_schedulers
moviepilot tool run search_torrents media_type=movie tmdb_id=12345
```

`tool run` 参数格式固定为 `key=value`。

```bash
moviepilot scheduler list
moviepilot scheduler run subscribe_refresh
```

## API 调试手册

Base URL in local CLI mode is commonly the frontend proxy, e.g. `http://127.0.0.1:3000/api/v1/...`; backend default port from CLI docs is `3001`. OpenAPI auth schemes include OAuth2 password bearer, `apikey` query, `X-API-KEY` header, `token` query, `MoviePilot` cookie, and HTTP bearer.

Auth notation used below:
- `bearer/apikey/token` = OpenAPI lists OAuth2PasswordBearer, `apikey` query, `X-API-KEY`, or `token` query.
- `token` = API_TOKEN query only (`?token=...`).
- `cookie` = `MoviePilot` resource token cookie.
- `none/token-param` = no declared security, but path has `token` query parameter.

### 获取 Token

```bash
TOKEN=$(curl -s -X POST "http://127.0.0.1:3000/api/v1/login/access-token" \
  -d "username=admin&password=<PASSWORD>" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
```

### 插件管理 Plugin

| Method | Path | Auth | 关键参数 | 用途 |
|---|---|---|---|---|
| GET | `/api/v1/plugin/` | bearer/apikey/token | `state=all`, `force=false` | 所有插件，排查市场/安装态/状态刷新 |
| GET | `/api/v1/plugin/installed` | bearer/apikey/token | - | 已安装插件 |
| GET | `/api/v1/plugin/reload/{plugin_id}` | bearer/apikey/token | `plugin_id` | 重新加载插件，排查未加载/API 未注册 |
| GET | `/api/v1/plugin/install/{plugin_id}` | bearer/apikey/token | `plugin_id`, `repo_url=`, `force=false` | 安装/强制重装插件 |
| DELETE | `/api/v1/plugin/{plugin_id}` | bearer/apikey/token | `plugin_id` | 卸载插件 |
| GET | `/api/v1/plugin/reset/{plugin_id}` | bearer/apikey/token | `plugin_id` | 重置插件配置及数据 |
| GET | `/api/v1/plugin/{plugin_id}` | bearer/apikey/token | `plugin_id` | 获取插件配置 |
| PUT | `/api/v1/plugin/{plugin_id}` | bearer/apikey/token | `plugin_id`, JSON body | 更新插件配置 |
| GET | `/api/v1/plugin/form/{plugin_id}` | bearer/apikey/token | `plugin_id` | 获取插件表单页面，排查 form 渲染 |
| GET | `/api/v1/plugin/page/{plugin_id}` | bearer/apikey/token | `plugin_id` | 获取插件数据页面，排查 page 渲染 |
| GET | `/api/v1/plugin/dashboard/meta` | bearer/apikey/token | - | 获取所有插件仪表板元信息 |
| GET | `/api/v1/plugin/dashboard/{plugin_id}` | bearer/apikey/token | `plugin_id`, `user-agent` header | 获取插件仪表板配置 |
| GET | `/api/v1/plugin/sidebar_nav` | bearer/apikey/token | - | 获取插件侧栏导航项，排查 Vue/导航注册 |

查看已安装插件：

```bash
curl -s "http://127.0.0.1:3000/api/v1/plugin/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

强制重装插件：

```bash
curl -s "http://127.0.0.1:3000/api/v1/plugin/install/<PluginClassName>?repo_url=<REPO_URL>&force=true" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### 系统 System / logging / progress

| Method | Path | Auth | 关键参数 | 用途 |
|---|---|---|---|---|
| GET | `/api/v1/system/logging` | cookie | `length=50`, `logfile=moviepilot.log` | 实时日志；`length=-1` 返回全文 |
| GET | `/api/v1/system/env` | bearer/apikey/token | - | 查询系统配置 |
| GET | `/api/v1/system/setting/{key}` | bearer/apikey/token | `key` | 查询系统设置 |
| GET | `/api/v1/system/global` | none/token-param | `token` | 查询非敏感系统设置 |
| GET | `/api/v1/system/global/user` | bearer/apikey/token | - | 查询用户相关系统设置 |
| GET | `/api/v1/system/restart` | bearer/apikey/token | - | 重启系统 |
| GET | `/api/v1/system/versions` | bearer/apikey/token | - | 查询 Github 所有 Release 版本 |
| GET | `/api/v1/system/progress/{process_type}` | cookie | `process_type` | 实时进度 |
| GET | `/api/v1/system/modulelist` | bearer/apikey/token | - | 查询已加载模块 ID 列表 |
| GET | `/api/v1/system/moduletest/{moduleid}` | bearer/apikey/token | `moduleid` | 模块可用性测试 |
| GET | `/api/v1/system/nettest` | bearer/apikey/token | `target_id`, `url`, `include` | 测试网络连通性 |
| GET | `/api/v1/system/ruletest` | bearer/apikey/token | `title`, `rulegroup_name`, `subtitle` | 过滤规则测试 |

查看后端应用日志全文：

```bash
curl -s "http://127.0.0.1:3000/api/v1/system/logging?logfile=moviepilot.log&length=-1" \
  -H "Authorization: Bearer $TOKEN"
```

查看插件日志：

```bash
curl -s "http://127.0.0.1:3000/api/v1/system/logging?logfile=plugins/<plugin_id>.log&length=-1" \
  -H "Authorization: Bearer $TOKEN"
```

插件日志注意事项（适用于调试场景）：
- MoviePilot logger 按插件目录名写日志文件：`{LOG_PATH}/plugins/{plugin_id}.log`。
- `/api/v1/system/logging` 文件不存在时直接返回 **404**，不会自动创建。
- `RotatingFileHandler` 在首次写日志时才懒创建文件。
- 前端“查看日志”按钮拼接路径：`plugins/${plugin.id.toLowerCase()}.log`；`plugin.id` 取自 `package.v2.json` 的 key，再 `.toLowerCase()`。
- Best practice：插件 `init_plugin()` 中预创建日志文件，避免首次请求 404。

### 调度器 Scheduler / services

| Method | Path | Auth | 关键参数 | 用途 |
|---|---|---|---|---|
| GET | `/api/v1/dashboard/schedule2` | token | - | 后台服务（API_TOKEN），用于只读查看 scheduler/service 状态 |
| GET | `/api/v1/system/runscheduler` | bearer/apikey/token | `jobid` | 运行服务 |
| GET | `/api/v1/system/runscheduler2` | token | `jobid` | 运行服务（API_TOKEN） |

CLI 通常更直接：

```bash
moviepilot scheduler list
moviepilot scheduler run <service_id>
```

### 媒体 / 搜索 / 识别 Media & Search

| Method | Path | Auth | 关键参数 | 用途 |
|---|---|---|---|---|
| GET | `/api/v1/media/recognize` | bearer/apikey/token | `title`, `subtitle` | 识别媒体信息（种子） |
| GET | `/api/v1/media/recognize2` | token | `title`, `subtitle` | 识别种子媒体信息（API_TOKEN） |
| GET | `/api/v1/media/recognize_file` | bearer/apikey/token | `path` | 识别媒体信息（文件） |
| GET | `/api/v1/media/recognize_file2` | token | `path` | 识别文件媒体信息（API_TOKEN） |
| GET | `/api/v1/media/search` | bearer/apikey/token | `title`, `type=media`, `page=1`, `count=8` | 搜索媒体/人物信息 |
| GET | `/api/v1/media/{mediaid}` | bearer/apikey/token | `mediaid`, `type_name`, `title`, `year` | 查询媒体详情 |
| GET | `/api/v1/search/last` | bearer/apikey/token | - | 查询搜索结果 |
| GET | `/api/v1/search/last/context` | bearer/apikey/token | - | 查询上次搜索上下文 |
| GET | `/api/v1/search/title` | bearer/apikey/token | `keyword`, `page=0`, `sites` | 模糊搜索资源 |
| GET | `/api/v1/search/media/{mediaid}` | bearer/apikey/token | `mediaid`, `mtype`, `area=title`, `title`, `year`, `season`, `sites` | 精确搜索资源 |

识别问题最小复现：

```bash
curl -s "http://127.0.0.1:3000/api/v1/media/recognize?title=<TITLE>&subtitle=<SUBTITLE>" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### 站点 Site

| Method | Path | Auth | 关键参数 | 用途 |
|---|---|---|---|---|
| GET | `/api/v1/site/` | bearer/apikey/token | - | 所有站点 |
| GET | `/api/v1/site/test/{site_id}` | bearer/apikey/token | `site_id` | 连接测试 |
| GET | `/api/v1/site/userdata/{site_id}` | bearer/apikey/token | `site_id`, `workdate` | 查询某站点用户数据 |
| GET | `/api/v1/site/userdata/latest` | bearer/apikey/token | - | 查询所有站点最新用户数据 |
| GET | `/api/v1/site/statistic` | bearer/apikey/token | - | 所有站点统计信息 |
| GET | `/api/v1/site/rss` | bearer/apikey/token | - | 所有订阅站点 |
| GET | `/api/v1/site/mapping` | bearer/apikey/token | - | 获取站点域名到名称映射 |

### 订阅 Subscribe

| Method | Path | Auth | 关键参数 | 用途 |
|---|---|---|---|---|
| GET | `/api/v1/subscribe/` | bearer/apikey/token | - | 查询所有订阅 |
| GET | `/api/v1/subscribe/list` | token | - | 查询所有订阅（API_TOKEN） |
| GET | `/api/v1/subscribe/refresh` | bearer/apikey/token | - | 刷新订阅 |
| GET | `/api/v1/subscribe/search` | bearer/apikey/token | - | 搜索所有订阅 |
| GET | `/api/v1/subscribe/search/{subscribe_id}` | bearer/apikey/token | `subscribe_id` | 搜索指定订阅 |
| GET | `/api/v1/subscribe/history/{mtype}` | bearer/apikey/token | `mtype`, `page=1`, `count=30` | 查询订阅历史 |
| GET | `/api/v1/subscribe/files/{subscribe_id}` | bearer/apikey/token | `subscribe_id` | 订阅相关文件信息 |

### 下载 / 整理 / 媒体库 Download & Transfer & MediaServer

| Method | Path | Auth | 关键参数 | 用途 |
|---|---|---|---|---|
| GET | `/api/v1/download/` | bearer/apikey/token | `name` | 正在下载 |
| GET | `/api/v1/download/clients` | bearer/apikey/token | - | 查询可用下载器 |
| GET | `/api/v1/download/paths` | bearer/apikey/token | - | 查询可用下载路径 |
| GET | `/api/v1/dashboard/downloader` | bearer/apikey/token | `name` | 下载器信息 |
| GET | `/api/v1/dashboard/downloader2` | token | - | 下载器信息（API_TOKEN） |
| GET | `/api/v1/transfer/name` | bearer/apikey/token | `path`, `filetype` | 查询整理后的名称 |
| GET | `/api/v1/transfer/queue` | bearer/apikey/token | - | 查询整理队列 |
| GET | `/api/v1/transfer/now` | token | - | 立即执行下载器文件整理 |
| GET | `/api/v1/history/transfer` | bearer/apikey/token | `title`, `page=1`, `count=30`, `status` | 查询整理记录 |
| GET | `/api/v1/history/download` | bearer/apikey/token | `page=1`, `count=30` | 查询下载历史记录 |
| GET | `/api/v1/mediaserver/exists` | bearer/apikey/token | `title`, `year`, `mtype`, `tmdbid`, `season` | 查询本地是否存在（数据库） |
| GET | `/api/v1/mediaserver/latest` | bearer/apikey/token | `server`, `count=20` | 最新入库条目 |
| GET | `/api/v1/mediaserver/library` | bearer/apikey/token | `server`, `hidden=false` | 媒体库列表 |

## 常见排障场景路由表

| 症状 | 用哪个 CLI/API/日志定位 |
|---|---|
| 服务起不来 | `moviepilot doctor --json` → `moviepilot logs --stdio` → `moviepilot logs --frontend` → `moviepilot config get PORT/NGINX_PORT` |
| 后端启动但前端不可用 | `moviepilot status`；查 `<Config Dir>/logs/moviepilot.frontend.stdout.log`；确认前端代理 `/api` 到后端 |
| 插件未加载 | `moviepilot start --safe` 区分插件导致的启动问题；`GET /api/v1/plugin/?state=all&force=true`；`GET /api/v1/plugin/reload/{plugin_id}`；查 `moviepilot.log` |
| 插件 API 未注册 | `GET /api/v1/plugin/{plugin_id}` 确认安装配置；`GET /api/v1/plugin/reload/{plugin_id}`；查插件 import/init 日志 |
| 插件页面/表单空白 | `GET /api/v1/plugin/form/{plugin_id}` / `page/{plugin_id}`；查 `plugins/<plugin_id>.log` 与 `moviepilot.log` |
| 插件日志 404 | `GET /api/v1/system/logging?logfile=plugins/<plugin_id>.log&length=-1`；确认日志文件是否首次写入/预创建 |
| 定时任务不触发 | `moviepilot scheduler list`；`moviepilot scheduler run <service_id>`；API `GET /api/v1/dashboard/schedule2?token=<API_TOKEN>`；`runscheduler`/`runscheduler2` |
| 识别失败 | `GET /api/v1/media/recognize` 或 `recognize_file` 最小复现；再查 `GET /api/v1/search/last/context` 与 `moviepilot.log` |
| 搜索无结果 | `GET /api/v1/search/title?keyword=...`；`GET /api/v1/site/test/{site_id}`；`GET /api/v1/site/rss`；查站点/下载器日志 |
| 订阅不刷新 | `GET /api/v1/subscribe/`；`GET /api/v1/subscribe/refresh`；`GET /api/v1/subscribe/history/{mtype}`；scheduler list/run |
| 下载器异常 | `GET /api/v1/download/clients`；`GET /api/v1/dashboard/downloader`；`moviepilot config list` 查下载器相关配置 |
| 整理/入库异常 | `GET /api/v1/transfer/queue`；`GET /api/v1/history/transfer`；`GET /api/v1/transfer/name?path=...`；查 transfer 相关日志 |
| 媒体库已存在判断异常 | `GET /api/v1/mediaserver/exists`；`GET /api/v1/mediaserver/library`；`GET /api/v1/mediaserver/latest` |
| 版本不更新 | `moviepilot stop && moviepilot update all && moviepilot start`；`moviepilot version`；`GET /api/v1/system/versions`；查 progress/logging |
| 配置怀疑错误 | `moviepilot config path/list/describe`；`GET /api/v1/system/env`；`GET /api/v1/system/setting/{key}` |

## Fast Commands

Most other commands are listed in the CLI/API manuals above.

```bash
# 1) 离线采集启动问题证据
moviepilot doctor --json

# 2) 安全模式启动：跳过插件、调度器、监控、命令、工作流等后台扩展能力
moviepilot start --safe

# 3) 查看近期日志
moviepilot logs --lines 200

# 4) 获取 bearer token
TOKEN=$(curl -s -X POST "http://127.0.0.1:3000/api/v1/login/access-token" \
  -d "username=admin&password=<PASSWORD>" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# 5) 查看/触发调度器
moviepilot scheduler list
moviepilot scheduler run <service_id>
```

## Notes
- Keep probes read-only unless the scenario explicitly requires reload/restart/install/reset/run scheduler.
- Prefer CLI `doctor/status/logs/config` when the backend may be down; prefer API when the instance is up and you need structured runtime state.
- `moviepilot start --safe` is the fastest way to separate core service startup from plugin/scheduler/monitor/workflow side effects.
- API auth is endpoint-specific; if bearer fails on logging/progress, check whether the route is declared as `MoviePilot` cookie in OpenAPI.
- Do not invent endpoints or flags. If a needed runtime fact is absent from `/tmp/mp_cli.md` and `/tmp/mp_openapi.json`, mark it as “资料未提供”.
