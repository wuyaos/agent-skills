# MoviePilot CLI Runtime Reference

> 本文保留完整CLI索引。命令中的密码和Token均为占位示例；实际凭据必须从安全文件或环境变量读取，不得写入日志、Prompt或提交。start/stop/restart/update/uninstall/scheduler run 等命令属于写操作，执行前必须取得授权。

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
