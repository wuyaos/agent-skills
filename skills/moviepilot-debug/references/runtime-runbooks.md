# MoviePilot Runtime Runbooks

## 常见排障场景路由表

| 症状 | 用哪个 CLI/API/日志定位 |
|---|---|
| 服务起不来 | `moviepilot doctor --json` → `moviepilot logs --stdio` → `moviepilot logs --frontend` → `moviepilot config get PORT/NGINX_PORT` |
| 后端启动但前端不可用 | `moviepilot status`；查 `<Config Dir>/logs/moviepilot.frontend.stdout.log`；确认前端代理 `/api` 到后端 |
| 插件未加载 | `moviepilot start --safe` 区分插件导致的启动问题；`GET /api/v1/plugin/?state=all&force=true`；`GET /api/v1/plugin/reload/{plugin_id}`；查 `moviepilot.log` |
| 插件 API 未注册 | `GET /api/v1/plugin/{plugin_id}` 确认安装配置；`GET /api/v1/plugin/reload/{plugin_id}`；查插件 import/init 日志 |
| 插件页面/表单空白 | `GET /api/v1/plugin/form/{plugin_id}` / `page/{plugin_id}`；查 `plugins/<plugin_id>.log` 与 `moviepilot.log` |
| 插件日志 404 | `GET /api/v1/system/logging?logfile=plugins/<plugin_id>.log&length=-1`；确认日志文件是否首次写入/预创建 |
| 定时任务不触发 | 先只读查询 `moviepilot scheduler list`、`GET /api/v1/dashboard/schedule`，旧实例再尝试 `schedule2`；仅在明确授权后运行 service |
| 识别失败 | `GET /api/v1/media/recognize` 或 `recognize_file` 最小复现；再查 `GET /api/v1/search/last/context` 与 `moviepilot.log` |
| 搜索无结果 | `GET /api/v1/search/title?keyword=...`；`GET /api/v1/site/test/{site_id}`；`GET /api/v1/site/rss`；查站点/下载器日志 |
| 订阅不刷新 | `GET /api/v1/subscribe/`；`GET /api/v1/subscribe/refresh`；`GET /api/v1/subscribe/history/{mtype}`；scheduler list/run |
| 下载器异常 | `GET /api/v1/download/clients`；`GET /api/v1/dashboard/downloader`；`moviepilot config list` 查下载器相关配置 |
| 整理/入库异常 | `GET /api/v1/transfer/queue`；`GET /api/v1/history/transfer`；`GET /api/v1/transfer/name?path=...`；查 transfer 相关日志 |
| 媒体库已存在判断异常 | `GET /api/v1/mediaserver/exists`；`GET /api/v1/mediaserver/library`；`GET /api/v1/mediaserver/latest` |
| 版本不更新 | `moviepilot stop && moviepilot update all && moviepilot start`；`moviepilot version`；`GET /api/v1/system/versions`；查 progress/logging |
| 配置怀疑错误 | `moviepilot config path/list/describe`；`GET /api/v1/system/env`；`GET /api/v1/system/setting/{key}` |

## Fast read-only commands

```bash
moviepilot doctor --json
moviepilot status
moviepilot logs --lines 200
moviepilot scheduler list
```

For plugin evidence, prefer `../scripts/probe_plugin.py`; it produces redacted structured output. `start --safe`, scheduler execution, reload, restart, install, reset, refresh, and update are state-changing operations and require explicit authorization.

## Notes

- Prefer CLI `doctor/status/logs/config` when the backend may be down; prefer API when the instance is up and structured runtime state is needed.
- Discover the active ports and routes from the current instance. Personal deployments may use custom ports, and V3 routes can differ from older V2 OpenAPI snapshots.
- Plugin-specific logs and persisted plugin status/history can be stronger evidence than the general MoviePilot log.
- Do not invent endpoints or flags. Probe the current CLI/OpenAPI or report `NOT_VERIFIED` with the missing evidence.
