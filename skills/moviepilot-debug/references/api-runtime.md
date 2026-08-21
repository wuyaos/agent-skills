# MoviePilot API Runtime Reference

> 路由可能随 MoviePilot V2/V3 变化；执行前优先通过当前实例 OpenAPI、CLI 或只读探测确认。本文是查询索引，不代表调用授权；reload/install/reset/restart/refresh/run 等 GET 路由仍属于写操作。敏感凭据从环境变量或文件读取，不要直接放进命令行。

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
